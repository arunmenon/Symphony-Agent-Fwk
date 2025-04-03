"""Example demonstrating Symphony's goal management system."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.agents.goals import Goal, GoalConditionedAgentMixin, GoalManager, GoalStatus
from symphony.agents.planning import PlannerAgent
from symphony.llm.base import MockLLMClient
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import tool


class GoalConditionedReactiveAgent(ReactiveAgent, GoalConditionedAgentMixin):
    """A reactive agent with goal conditioning."""
    
    async def run(self, input_message: str) -> str:
        """Run the agent with goal context incorporated."""
        # Include goal information in the system prompt
        original_system_prompt = self.system_prompt
        
        # Append goal information if available
        goal_info = self.format_goal_for_prompt()
        if goal_info and "No active goal" not in goal_info:
            self.system_prompt = f"{original_system_prompt}\n\n{goal_info}"
        
        # Run the agent
        result = await super().run(input_message)
        
        # Restore original system prompt
        self.system_prompt = original_system_prompt
        
        return result


# Define research tool for the example
@tool(name="research", description="Search for information on a topic")
def research(topic: str) -> str:
    """Simulate researching a topic."""
    research_data = {
        "climate change": "Climate change is the long-term alteration of temperature and typical weather patterns. It is primarily caused by human activities, especially the burning of fossil fuels, which increases heat-trapping greenhouse gas levels in Earth's atmosphere.",
        "renewable energy": "Renewable energy comes from sources that are naturally replenishing but flow-limited, such as sunlight, wind, rain, tides, waves, and geothermal heat. It typically has a lower environmental impact than fossil fuels.",
        "sustainable agriculture": "Sustainable agriculture is farming in sustainable ways, which means meeting society's present food and textile needs, without compromising the ability for current or future generations to meet their needs. It can be based on an understanding of ecosystem services."
    }
    
    return research_data.get(topic.lower(), f"No specific information found for: {topic}")


# Define note-taking tool
@tool(name="take_notes", description="Save notes about research findings")
def take_notes(title: str, content: str) -> str:
    """Simulate saving research notes."""
    print(f"\n--- Note Saved ---\nTitle: {title}\nContent: {content}\n-----------------")
    return f"Notes saved: {title}"


async def main():
    """Run the example."""
    print("=== Goal Management System Example ===\n")
    
    # Create a prompt registry
    registry = PromptRegistry()
    
    # Register system prompts
    registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a research assistant focused on achieving your assigned goals. "
            "Use the available tools to complete your research tasks efficiently."
        ),
        agent_type="reactive"
    )
    
    # Create a mock LLM for decomposing goals
    llm_client = MockLLMClient(responses={
        # Goal decomposition response
        "Task: Decompose the following goal into": """
```json
[
  {
    "description": "Research the causes of climate change",
    "success_criteria": [
      "Identify at least 3 major causes of climate change",
      "Understand the mechanisms behind greenhouse gas effects",
      "Determine which human activities contribute most significantly"
    ]
  },
  {
    "description": "Research the impacts of climate change",
    "success_criteria": [
      "Identify environmental impacts like rising sea levels and extreme weather",
      "Understand economic impacts on agriculture and infrastructure",
      "Explore social impacts like migration and health issues"
    ]
  },
  {
    "description": "Research potential solutions to climate change",
    "success_criteria": [
      "Identify renewable energy alternatives to fossil fuels",
      "Explore sustainable agriculture practices",
      "Understand policy approaches like carbon taxes and regulations"
    ]
  }
]
```
""",

        # Agent responses for various inputs
        "Tell me about climate change": "Based on my research: Climate change is the long-term alteration of temperature and typical weather patterns. It is primarily caused by human activities, especially the burning of fossil fuels, which increases heat-trapping greenhouse gas levels in Earth's atmosphere.",
        
        "Research renewable energy solutions": "I've researched renewable energy solutions. Renewable energy comes from sources that are naturally replenishing but flow-limited, such as sunlight, wind, rain, tides, waves, and geothermal heat. It typically has a lower environmental impact than fossil fuels.",
        
        "What have you learned about sustainable agriculture?": "From my research on sustainable agriculture: Sustainable agriculture is farming in sustainable ways, which means meeting society's present food and textile needs, without compromising the ability for current or future generations to meet their needs. It can be based on an understanding of ecosystem services."
    })
    
    # Create agent configuration
    agent_config = AgentConfig(
        name="ResearchAssistant",
        agent_type="reactive",
        description="A research assistant focused on climate change",
        tools=["research", "take_notes"]
    )
    
    # Create a goal-conditioned agent
    agent = GoalConditionedReactiveAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    # Scenario 1: Set a main research goal
    print("Scenario 1: Setting a Main Research Goal")
    main_goal = agent.set_goal(
        description="Conduct comprehensive research on climate change causes, impacts, and solutions",
        success_criteria=[
            "Gather detailed information on the major causes of climate change",
            "Identify key environmental, economic, and social impacts",
            "Research potential solutions including renewable energy and policy approaches"
        ]
    )
    print(f"Main goal set: {main_goal.description}")
    print(f"Success criteria: {[c.description for c in main_goal.success_criteria]}\n")
    
    # Scenario 2: Decompose the goal
    print("Scenario 2: Decomposing the Goal into Subgoals")
    subgoals = await agent.decompose_active_goal()
    print(f"Created {len(subgoals)} subgoals:")
    for i, subgoal in enumerate(subgoals):
        print(f"{i+1}. {subgoal.description}")
        print(f"   Criteria: {[c.description for c in subgoal.success_criteria]}")
    print()
    
    # Scenario 3: Include goal context in agent interactions
    print("Scenario 3: Agent Interaction with Goal Context")
    print("User: Tell me about climate change")
    response = await agent.run("Tell me about climate change")
    print(f"Agent: {response}\n")
    
    # Scenario 4: Mark criteria as complete
    print("Scenario 4: Tracking Goal Progress")
    
    # Mark first subgoal's first criterion as complete
    first_subgoal = subgoals[0]
    agent.goal_manager.mark_criterion_met(
        goal_id=first_subgoal.id,
        criterion_index=0,
        evidence="Identified fossil fuel burning as a major cause"
    )
    print(f"Marked criterion complete for subgoal: {first_subgoal.description}")
    
    # Show updated goal context
    goal_context = agent.get_active_goal_context()
    print("\nUpdated Goal Context:")
    print(json.dumps(goal_context, indent=2))
    
    # Scenario 5: Complete a subgoal
    print("\nScenario 5: Completing a Subgoal")
    
    # Mark all criteria of the first subgoal as complete
    for i in range(len(first_subgoal.success_criteria)):
        agent.goal_manager.mark_criterion_met(
            goal_id=first_subgoal.id,
            criterion_index=i,
            evidence=f"Completed criterion {i+1}"
        )
    
    # Update subgoal status
    agent.goal_manager.update_goal_status(first_subgoal.id, GoalStatus.COMPLETED)
    print(f"Completed subgoal: {first_subgoal.description}")
    
    # Show formatted goal for prompt
    print("\nGoal formatting for prompts:")
    print(agent.format_goal_for_prompt())
    
    # Scenario 6: Research with goal context
    print("\nScenario 6: Agent Using Goal Context for Research")
    print("User: Research renewable energy solutions")
    response = await agent.run("Research renewable energy solutions")
    print(f"Agent: {response}")
    
    # Show goal tree
    print("\nFinal Goal Tree:")
    goal_tree = agent.goal_manager.get_goal_tree()
    print(json.dumps(goal_tree, indent=2))


if __name__ == "__main__":
    asyncio.run(main())