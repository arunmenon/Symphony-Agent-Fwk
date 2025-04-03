"""Example demonstrating Symphony's enhanced prompt system."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig
from symphony.agents.prompt_integration import PromptEnhancedReactiveAgent, create_prompt_enhanced_agent
from symphony.agents.planning import PlannerAgent
from symphony.llm.base import MockLLMClient
from symphony.prompts.enhanced_registry import EnhancedPromptRegistry
from symphony.tools.base import tool


# Define a calculator tool
@tool(name="calculator", description="Perform basic arithmetic calculations")
def calculator(operation: str, a: float, b: float) -> float:
    """Perform a basic arithmetic calculation."""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")


async def main():
    """Run the example."""
    print("=== Enhanced Prompt System Example ===\n")
    
    # Create an enhanced prompt registry
    registry = EnhancedPromptRegistry()
    
    # Register a custom prompt (optional)
    registry.register_prompt(
        prompt_type="system",
        content="You are a custom ${agent_type} named ${agent_name} with these capabilities: ${tool_names}.\nToday is ${current_date}.",
        agent_type="custom"
    )
    
    # Register custom variables
    registry.register_variable("favorite_color", "blue")
    registry.register_variable("expertise_level", "expert", agent_type="researcher")
    
    # Create a mock LLM client
    llm_client = MockLLMClient(responses={
        "Tell me about yourself": "I am a reactive agent with calculator capabilities. Today's date is 2025-04-04."
    })
    
    # Demonstrate different prompt scenarios
    
    # Scenario 1: Using default template prompt
    print("Scenario 1: Default Template Prompt")
    reactive_config = AgentConfig(
        name="ReactiveCalculator",
        agent_type="reactive",
        description="A calculator assistant",
        tools=["calculator"]
    )
    
    reactive_agent = PromptEnhancedReactiveAgent(
        config=reactive_config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    print(f"System Prompt:\n{reactive_agent.system_prompt}\n")
    
    # Scenario 2: Using custom registered prompt
    print("Scenario 2: Custom Registered Prompt")
    custom_config = AgentConfig(
        name="CustomAgent",
        agent_type="custom",
        description="A custom agent",
        tools=["calculator"]
    )
    
    custom_agent = PromptEnhancedReactiveAgent(
        config=custom_config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    print(f"System Prompt:\n{custom_agent.system_prompt}\n")
    
    # Scenario 3: Using factory to enhance a different agent type
    print("Scenario 3: Factory-Enhanced Agent")
    planner_config = AgentConfig(
        name="TaskPlanner",
        agent_type="planner",
        description="A planning agent",
        tools=["calculator"]
    )
    
    enhanced_planner = create_prompt_enhanced_agent(
        agent_cls=PlannerAgent,
        config=planner_config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    print(f"System Prompt:\n{enhanced_planner.system_prompt}\n")
    
    # Demonstrate agent execution with prompted template
    print("Running agent with enhanced prompt...")
    response = await reactive_agent.run("Tell me about yourself")
    print(f"Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())