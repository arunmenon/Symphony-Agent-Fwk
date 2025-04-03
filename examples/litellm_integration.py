"""Example of using Symphony with LiteLLM for multi-provider model support."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.litellm_client import LiteLLMClient, LiteLLMConfig
from symphony.mcp.base import MCPManager, MCPConfig
from symphony.prompts.registry import PromptRegistry
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
    # Create a prompt registry with system prompts
    registry = PromptRegistry()
    
    # Register a system prompt for multiple model providers
    registry.register_prompt(
        prompt_type="system",
        content="""You are a helpful AI assistant that excels at calculations.
When asked to calculate something, use the calculator tool.
Always show your work so the user can follow your reasoning.
""",
        agent_type="CalculatorAgent"
    )
    
    # Create LiteLLM configurations for different providers
    openai_config = LiteLLMConfig(
        model="openai/gpt-3.5-turbo",  # Note: replace with your model of choice
        max_tokens=500,
        temperature=0.7,
        # Add your API key here or use environment variables
        # api_key=os.environ.get("OPENAI_API_KEY")
    )
    
    anthropic_config = LiteLLMConfig(
        model="anthropic/claude-3-haiku",  # Note: replace with your model of choice
        max_tokens=500,
        temperature=0.7,
        # Add your API key here or use environment variables
        # api_key=os.environ.get("ANTHROPIC_API_KEY")
    )
    
    # For demo purposes, use just one config (switch between them as needed)
    active_config = openai_config
    
    # Create LiteLLM client
    llm_client = LiteLLMClient(config=active_config)
    
    # Initialize MCP Manager 
    mcp_manager = MCPManager()
    
    # Create agent config with calculator tool
    agent_config = AgentConfig(
        name="CalculatorAgent",
        agent_type="CalculatorAgent",
        description="An agent that can perform calculations",
        tools=["calculator"],
        mcp_enabled=True
    )
    
    # Create reactive agent
    agent = ReactiveAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=registry,
        mcp_manager=mcp_manager
    )
    
    # Set of calculation tasks to run
    calculation_tasks = [
        "What is 125 + 37?",
        "Calculate 85 * 12.",
        "If I have 250 and spend 75, how much do I have left?",
        "What is 1000 divided by 8?"
    ]
    
    # Run the tasks sequentially
    print(f"Running calculations with {active_config.model}...\n")
    
    for task in calculation_tasks:
        print(f"Question: {task}")
        try:
            response = await agent.run(task)
            print(f"Response: {response}\n")
        except Exception as e:
            print(f"Error: {str(e)}\n")
            # If you have API keys set up correctly, remove this comment to actually run with real LLMs
            print("Note: This example requires valid API keys to run with real LLMs.")
            print("To use real LLMs, uncomment the api_key lines in the LiteLLMConfig setups.")
            break


if __name__ == "__main__":
    asyncio.run(main())