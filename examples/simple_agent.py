"""Example of a simple reactive agent using the Symphony framework."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.base import MockLLMClient
from symphony.prompts.registry import PromptRegistry, PromptTemplate
from symphony.tools.base import tool
from symphony.utils.types import Message


# Define a simple calculator tool
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
    # Create a prompt registry with a simple system prompt
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a helpful assistant that can perform calculations. "
            "When asked to calculate something, use the calculator tool."
        ),
        agent_type="ReactiveAgent"
    )
    
    # Create a mock LLM client with predefined responses
    llm_client = MockLLMClient(responses={
        "What is 2 + 2?": "To calculate 2 + 2, I'll use the calculator tool.\n"
                         "The result is 4.",
        "What is 10 - 5?": "Let me calculate 10 - 5 for you.\n"
                          "Using the calculator tool: subtract(10, 5) = 5",
        "What is 7 * 8?": "To find 7 * 8, I'll use my calculator tool.\n"
                         "7 * 8 = 56"
    })
    
    # Create an agent config with the calculator tool
    agent_config = AgentConfig(
        name="CalculatorAgent",
        agent_type="ReactiveAgent",
        description="An agent that can perform calculations",
        tools=["calculator"]
    )
    
    # Create a reactive agent
    agent = ReactiveAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    # Run the agent with a few test questions
    for question in [
        "What is 2 + 2?",
        "What is 10 - 5?",
        "What is 7 * 8?"
    ]:
        print(f"\nQuestion: {question}")
        response = await agent.run(question)
        print(f"Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())