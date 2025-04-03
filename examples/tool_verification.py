"""Example demonstrating Symphony's tool verification system."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig
from symphony.agents.tool_enhanced import ToolVerifiedReactiveAgent
from symphony.core.events import Event, EventBus, default_event_bus
from symphony.llm.base import MockLLMClient
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import tool
from symphony.tools.verification import (
    LLMToolRecoveryStrategy,
    ToolExecutionStatus,
)


# Define a tool with strict type requirements
@tool(name="format_name", description="Format a person's name with proper capitalization")
def format_name(first_name: str, last_name: str) -> str:
    """Format a person's name with proper capitalization."""
    if not first_name or not isinstance(first_name, str):
        raise ValueError("First name must be a non-empty string")
    if not last_name or not isinstance(last_name, str):
        raise ValueError("Last name must be a non-empty string")
    
    return f"{first_name.strip().title()} {last_name.strip().title()}"


# Define a calculation tool that can fail
@tool(name="divide", description="Divide two numbers")
def divide(numerator: float, denominator: float) -> float:
    """Divide two numbers."""
    if denominator == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return numerator / denominator


# Define a tool with sensitive blocklisted operations
@tool(name="file_operation", description="Perform operations on files")
def file_operation(operation: str, filename: str) -> str:
    """Perform operations on files (simulation)."""
    return f"Simulated {operation} on {filename}"


# Event listener for the demonstration
def log_tool_event(event: Event) -> None:
    """Log tool-related events."""
    if event.type.startswith("tool:"):
        print(f"EVENT: {event.type} - {event.source}")
        if "tool_name" in event.data:
            print(f"  Tool: {event.data['tool_name']}")
        if "args" in event.data:
            print(f"  Args: {event.data['args']}")
        if "error" in event.data:
            print(f"  Error: {event.data['error']}")
        if "result" in event.data:
            print(f"  Result: {event.data['result']}")
        print()


async def main():
    """Run the example."""
    print("=== Tool Verification System Example ===\n")
    
    # Set up event bus
    event_bus = EventBus()
    event_bus.subscribe(log_tool_event)
    
    # Create prompt registry
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content="You are a helpful agent that calls tools with proper parameters.",
        agent_type="reactive"
    )
    
    # Create LLM client with recovery capability
    llm_client = MockLLMClient(responses={
        "Fix tool arguments that failed": """
```json
{
    "first_name": "john",
    "last_name": "doe"
}
```
I've fixed the arguments by providing both a first_name and last_name as strings.
""",
        "Fix division by zero": """
```json
{
    "numerator": 10,
    "denominator": 0.5
}
```
I've fixed the arguments by changing the denominator to a non-zero value.
"""
    })
    
    # Create agent configuration
    agent_config = AgentConfig(
        name="ToolUser",
        agent_type="reactive",
        description="An agent that uses tools with verification",
        tools=["format_name", "divide", "file_operation"]
    )
    
    # Create the tool-verified agent
    agent = ToolVerifiedReactiveAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=registry,
        event_bus=event_bus
    )
    
    # Scenario 1: Successful tool call
    print("Scenario 1: Successful Tool Call")
    try:
        result = await agent.call_tool("format_name", first_name="john", last_name="doe")
        print(f"Result: {result}\n")
    except Exception as e:
        print(f"Error: {str(e)}\n")
    
    # Scenario 2: Missing parameter (should be recovered)
    print("Scenario 2: Missing Parameter (with recovery)")
    try:
        # The LLM should provide the missing last_name
        recovery = LLMToolRecoveryStrategy(llm_client)
        # This call is expected to use recovery to fix the missing last_name
        result = await agent.call_tool("format_name", first_name="jane")
        print(f"Result: {result}\n")
    except Exception as e:
        print(f"Error: {str(e)}\n")
    
    # Scenario 3: Invalid parameter type
    print("Scenario 3: Invalid Parameter Type")
    try:
        result = await agent.call_tool("format_name", first_name=123, last_name="smith")
        print(f"Result: {result}\n")
    except Exception as e:
        print(f"Error: {str(e)}\n")
    
    # Scenario 4: Tool execution error with recovery
    print("Scenario 4: Tool Execution Error with Recovery")
    try:
        # Division by zero should be fixed through recovery
        result = await agent.call_tool("divide", numerator=10, denominator=0)
        print(f"Result: {result}\n")
    except Exception as e:
        print(f"Error: {str(e)}\n")
    
    # Scenario 5: Safety blocklist detection
    print("Scenario 5: Safety Blocklist Detection")
    try:
        result = await agent.call_tool("file_operation", operation="rm -rf", filename="/tmp/test")
        print(f"Result: {result}\n")
    except Exception as e:
        print(f"Error: {str(e)}\n")


if __name__ == "__main__":
    asyncio.run(main())