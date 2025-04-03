"""Example demonstrating Symphony's modular architecture with design patterns."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.core import (
    ConfigLoader,
    Container,
    Event,
    EventType,
    LLMClientFactory,
    MCPManagerFactory,
    MemoryFactory,
    Plugin,
    PluginManager,
    SymphonyConfig,
    Symphony,
)
from symphony.llm.litellm_client import LiteLLMConfig
from symphony.mcp.base import MCPConfig
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import tool


# Define a custom plugin
class LoggingPlugin(Plugin):
    """Plugin that logs events in the system."""
    
    @property
    def name(self) -> str:
        return "logging_plugin"
    
    @property
    def description(self) -> str:
        return "Logs events in the Symphony framework"
    
    def initialize(self, container, event_bus):
        """Initialize the plugin."""
        # Subscribe to all events
        event_bus.subscribe(self.log_event)
        print(f"Logging plugin initialized and listening for events")
    
    def log_event(self, event: Event):
        """Log an event."""
        print(f"EVENT: {event.type} from {event.source} at {event.timestamp}")
        if event.data:
            print(f"  Data: {event.data}")
        print()


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
    # Create a configuration
    config = SymphonyConfig(
        application_name="Symphony Demo",
        debug=True,
        log_level="DEBUG",
        llm_provider="mock",  # Use mock for demo
        default_agent_type="reactive"
    )
    
    # Create Symphony instance
    symphony = Symphony(config)
    
    # Get references to container and event bus
    container = symphony.get_container()
    event_bus = symphony.get_event_bus()
    plugin_manager = symphony.get_plugin_manager()
    
    # Register our logging plugin
    plugin_manager.register_plugin(LoggingPlugin())
    
    # Create prompt registry
    prompt_registry = PromptRegistry()
    container.register("prompt_registry", prompt_registry)
    
    # Register a system prompt
    prompt_registry.register_prompt(
        prompt_type="system",
        content="You are a helpful assistant that can perform calculations.",
        agent_type="reactive"
    )
    
    # Use factories to create components
    
    # 1. Create LLM client using factory
    mock_responses = {
        "What is 2 + 2?": "To calculate 2 + 2, I need to add the numbers: 2 + 2 = 4. So the answer is 4.",
        "Calculate 5 * 3": "To calculate 5 * 3, I need to multiply: 5 * 3 = 15. So the answer is 15."
    }
    llm_client = LLMClientFactory.create_mock(responses=mock_responses)
    container.register("llm_client", llm_client)
    
    # 2. Create memory using factory
    memory = MemoryFactory.create("conversation")
    container.register("memory", memory)
    
    # 3. Create MCP manager using factory
    mcp_config = MCPConfig(app_name="Symphony Demo")
    mcp_manager = MCPManagerFactory.create(config=mcp_config)
    container.register("mcp_manager", mcp_manager)
    
    # Create agent configuration
    agent_config = AgentConfig(
        name="Calculator",
        agent_type="reactive",
        description="An agent that can perform calculations",
        tools=["calculator"],
        mcp_enabled=True
    )
    
    # Create a reactive agent
    agent = ReactiveAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=prompt_registry,
        memory=memory,
        mcp_manager=mcp_manager
    )
    
    # Publish an event
    event_bus.publish(
        Event.create(
            type=EventType.AGENT_CREATED,
            source="modular_architecture.py",
            agent_name=agent.config.name,
            agent_type=agent.config.agent_type
        )
    )
    
    # Run the agent with questions
    for question in ["What is 2 + 2?", "Calculate 5 * 3"]:
        # Publish message received event
        event_bus.publish(
            Event.create(
                type=EventType.MESSAGE_RECEIVED,
                source="user",
                message=question
            )
        )
        
        print(f"\nQuestion: {question}")
        
        # Publish agent started event
        event_bus.publish(
            Event.create(
                type=EventType.AGENT_STARTED,
                source=agent.config.name,
                input_message=question
            )
        )
        
        # Run the agent
        response = await agent.run(question)
        
        print(f"Response: {response}")
        
        # Publish agent finished event
        event_bus.publish(
            Event.create(
                type=EventType.AGENT_FINISHED,
                source=agent.config.name,
                input_message=question,
                output_message=response
            )
        )
    
    # Clean up
    symphony.cleanup()


if __name__ == "__main__":
    asyncio.run(main())