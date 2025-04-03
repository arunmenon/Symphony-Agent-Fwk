"""Example demonstrating Symphony's agent reflection capabilities."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentBase, AgentConfig, ReactiveAgent
from symphony.agents.planning import PlannerAgent
from symphony.agents.reflection import ReflectionPhase, ReflectiveAgentMixin
from symphony.llm.base import LLMClient, MockLLMClient
from symphony.prompts.registry import PromptRegistry
from symphony.utils.types import Message


class ReflectiveReactiveAgent(ReactiveAgent, ReflectiveAgentMixin):
    """A reactive agent with reflection capabilities."""
    
    async def decide_action(
        self, 
        messages: List[Message], 
        mcp_context: Optional[Any] = None
    ) -> Message:
        """Decide what action to take, with reflection."""
        # First, get the initial response from the LLM
        initial_response = await self.llm_client.chat(messages)
        
        # Reflect on the response
        improved_content = await self.reflect(
            initial_response.content,
            {"task": messages[-1].content if messages else ""}
        )
        
        # Return the potentially improved response
        return Message(
            role="assistant",
            content=improved_content
        )


class ReflectivePlannerAgent(PlannerAgent, ReflectiveAgentMixin):
    """A planning agent with reflection capabilities."""
    
    async def _parse_plan(self, plan_text: str) -> Any:
        """Parse a plan from text, with reflection beforehand."""
        # Reflect on the plan before parsing it
        improved_plan = await self.reflection_phase.reflect_on_plan(
            agent=self,
            plan=plan_text,
            task="creating a structured plan"
        )
        
        # Parse the potentially improved plan
        return await super()._parse_plan(improved_plan)


async def main():
    """Run the example."""
    print("=== Agent Reflection System Example ===\n")
    
    # Create a prompt registry
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content="You are a helpful assistant that provides well-reasoned responses.",
        agent_type="reactive"
    )
    
    # Example of flawed and improved reasoning
    flawed_reasoning = """
To solve this problem, I'll calculate how many apples each person gets.
We have 10 apples and 3 people. Each person should get an equal number of apples.
10 divided by 3 equals 3, so each person gets 3 apples.
That means a total of 9 apples are distributed, and we have 1 apple left over.
"""

    reflection_on_flawed = """
REFLECTION:
The reasoning contains a mathematical error. The calculation of 10 divided by 3 is incorrect. 10 divided by 3 is not exactly 3, but approximately 3.33. In the context of distributing whole apples, we need to consider that we can only give whole apples to each person.

Also, the reasoning correctly identifies that if each person gets 3 apples, then 9 apples are distributed in total with 1 left over. However, it doesn't address what to do with the remaining apple.

IMPROVED REASONING:
To solve this problem, I'll calculate how many apples each person gets.
We have 10 apples and 3 people. Each person should get an equal number of apples.
10 divided by 3 equals 3 with a remainder of 1, which means each person gets 3 whole apples.
That means a total of 9 apples are distributed (3 apples × 3 people = 9 apples), and we have 1 apple left over.
We can either leave this apple undistributed, or we could cut it into 3 equal parts so each person gets an additional 1/3 of an apple, depending on the requirements of the problem.

CONFIDENCE: 0.95
"""

    # Create a mock LLM client with reflection responses
    llm_client = MockLLMClient(responses={
        # Initial responses (with reasoning flaws)
        "How many apples does each person get if we have 10 apples and 3 people?": flawed_reasoning,
        
        # Reflection responses
        "Please reflect on the following reasoning": reflection_on_flawed,
        
        # Plan creation and reflection
        "Create a plan for organizing a small birthday party": """
1. Buy decorations
2. Bake cake
3. Invite friends
4. Set up decorations
5. Have party
""",

        "Please reflect on the following reasoning": """
REFLECTION:
The plan for organizing a birthday party is very basic and lacks important details and considerations. It doesn't include timing elements (when to do each task), budget considerations, or specifics about what needs to be done within each step. Several critical elements are also missing, such as food/drinks beyond the cake, music/entertainment, and cleanup.

IMPROVED REASONING:
Plan for organizing a small birthday party:

1. Planning (1-2 weeks before):
   - Decide on date, time, guest list, and budget
   - Choose a theme and location
   - Send invitations with RSVP details

2. Shopping (3-5 days before):
   - Purchase decorations (balloons, banners, themed items)
   - Buy ingredients for cake and other food
   - Get beverages (considering preferences of guests)
   - Purchase party favors if desired

3. Food preparation (1 day before):
   - Bake cake or order from bakery
   - Prepare any food that can be made ahead of time
   - Confirm dietary restrictions of guests

4. Setup (day of party):
   - Arrange furniture as needed
   - Set up decorations
   - Prepare remaining food and drinks
   - Set up music/entertainment

5. During party:
   - Welcome guests
   - Serve food and drinks
   - Facilitate activities or games
   - Cake ceremony (singing, candles, etc.)

6. After party:
   - Thank guests as they leave
   - Clean up venue
   - Send thank-you messages next day

CONFIDENCE: 0.9
"""
    })
    
    # Create agent configurations
    reactive_config = AgentConfig(
        name="ReflectiveAssistant",
        agent_type="reactive",
        description="An assistant that reflects on its reasoning"
    )
    
    planner_config = AgentConfig(
        name="ReflectivePlanner",
        agent_type="planner",
        description="A planner that reflects on and improves its plans"
    )
    
    # Create reflective agents
    reactive_agent = ReflectiveReactiveAgent(
        config=reactive_config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    planner_agent = ReflectivePlannerAgent(
        config=planner_config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    # Test the reflective reactive agent
    print("Testing Reflective Reactive Agent\n")
    print("Question: How many apples does each person get if we have 10 apples and 3 people?")
    response = await reactive_agent.run("How many apples does each person get if we have 10 apples and 3 people?")
    print(f"Response (after reflection):\n{response}\n")
    
    # Test the reflective planner agent
    print("Testing Reflective Planner Agent\n")
    print("Task: Create a plan for organizing a small birthday party")
    response = await planner_agent.run("Create a plan for organizing a small birthday party")
    print(f"Response (after plan reflection):\n{response}\n")


if __name__ == "__main__":
    asyncio.run(main())