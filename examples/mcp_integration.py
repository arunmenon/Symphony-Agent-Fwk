"""Example of using Symphony with Model Context Protocol (MCP) integration."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.base import MockLLMClient
from symphony.mcp.base import MCPManager, MCPConfig
from mcp.server.fastmcp import Context  # Import Context from MCP
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import tool
from symphony.utils.types import Message


# Define a web search tool that will be exposed via MCP
@tool(name="web_search", description="Search the web for information")
def web_search(query: str) -> str:
    """Simulate a web search with mock results."""
    if "weather" in query.lower():
        return "The weather is sunny with a high of 75°F."
    elif "population" in query.lower():
        return "The world population is approximately 7.9 billion people."
    elif "capital" in query.lower():
        return "The capital of France is Paris. The capital of Japan is Tokyo."
    else:
        return f"No specific information found for: {query}"


# Define a custom MCP resource to provide additional context
def setup_custom_mcp_resources(mcp_manager: MCPManager) -> None:
    """Set up custom MCP resources."""
    
    @mcp_manager.mcp.resource("symphony://knowledge-base/{topic}")
    def get_knowledge(topic: str, ctx: Context) -> str:
        """Example knowledge base resource."""
        knowledge = {
            "weather": "Weather is the state of the atmosphere, including temperature, cloudiness, humidity, etc.",
            "population": "Population refers to the number of people living in a particular area.",
            "capitals": "A capital city is the municipality where a country's government is located."
        }
        return knowledge.get(topic, f"No information available about {topic}")


async def main():
    # Create a prompt registry
    registry = PromptRegistry()
    
    # Register a system prompt
    registry.register_prompt(
        prompt_type="system",
        content=(
            "You are an MCP-enabled assistant. You can use the MCP protocol to access "
            "external resources and tools. When asked about topics like weather, populations, "
            "or capitals, use the appropriate tools or resources."
        ),
        agent_type="MCPAgent"
    )
    
    # Create a mock LLM client
    llm_client = MockLLMClient(responses={
        "What is the weather today?": "Based on my search: The weather is sunny with a high of 75°F.",
        "Tell me about world population": "According to available data: The world population is approximately 7.9 billion people.",
        "What is the capital of France?": "The capital of France is Paris. It's one of the world's major cultural centers."
    })
    
    # Initialize MCP Manager with custom configuration
    mcp_config = MCPConfig(
        app_name="Symphony MCP Example",
        resource_prefix="symphony"
    )
    mcp_manager = MCPManager(config=mcp_config)
    
    # Set up custom MCP resources
    setup_custom_mcp_resources(mcp_manager)
    
    # Create agent config with MCP enabled
    agent_config = AgentConfig(
        name="MCPAgent",
        agent_type="MCPAgent",
        description="An agent that uses MCP for context and tools",
        tools=["web_search"],
        mcp_enabled=True  # Explicitly enable MCP integration
    )
    
    # Create agent with MCP manager
    agent = ReactiveAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=registry,
        mcp_manager=mcp_manager
    )
    
    # Run the agent with test questions
    for question in [
        "What is the weather today?",
        "Tell me about world population",
        "What is the capital of France?"
    ]:
        print(f"\nQuestion: {question}")
        response = await agent.run(question)
        print(f"Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())