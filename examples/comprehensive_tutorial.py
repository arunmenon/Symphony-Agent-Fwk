"""
Comprehensive Symphony Example: Research Assistant

This example demonstrates a full-featured Symphony application that:
1. Creates a multi-agent research assistant system
2. Implements custom tools for web search and summarization
3. Uses MCP for context management
4. Employs the event system for logging
5. Demonstrates memory usage for conversation history
6. Shows both reactive and planning agent patterns
7. Uses factory pattern for component creation
8. Implements a plugin for enhanced functionality

The research assistant can:
- Search for information on topics
- Summarize findings
- Take notes
- Answer questions based on research
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

# Import Symphony components
from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.agents.planning import PlannerAgent
from symphony.core import (
    ConfigLoader,
    Event,
    EventType,
    LLMClientFactory,
    MCPManagerFactory,
    MemoryFactory,
    Plugin,
    PluginType,
    SymphonyConfig,
    Symphony,
)
from symphony.llm.litellm_client import LiteLLMConfig
from symphony.mcp.base import MCPConfig
from symphony.mcp.base import Context as MCPContext
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import tool
from symphony.utils.types import Message


# ----------------------
# Custom Plugin Creation
# ----------------------

class ResearchLoggerPlugin(Plugin):
    """Plugin for logging research activities."""
    
    @property
    def name(self) -> str:
        return "research_logger"
    
    @property
    def description(self) -> str:
        return "Logs research activities and findings"
    
    @property
    def plugin_type(self) -> PluginType:
        return PluginType.OTHER
    
    def initialize(self, container, event_bus):
        """Initialize the plugin."""
        self.findings = []
        self.log_file = Path("research_log.txt")
        
        # Subscribe to events
        event_bus.subscribe(self.log_research, event_type="research:finding")
        event_bus.subscribe(self.log_message, event_type=EventType.MESSAGE_SENT)
        
        print(f"Research Logger plugin initialized. Log file: {self.log_file}")
    
    def log_research(self, event: Event):
        """Log a research finding."""
        finding = event.data.get("finding", "")
        source = event.data.get("source", "unknown")
        
        self.findings.append((finding, source))
        
        with open(self.log_file, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] FINDING from {source}:\n")
            f.write(f"{finding}\n\n")
    
    def log_message(self, event: Event):
        """Log a message."""
        if "research" in event.data.get("content", "").lower():
            with open(self.log_file, "a") as f:
                f.write(f"[{datetime.now().isoformat()}] MESSAGE from {event.source}:\n")
                f.write(f"{event.data.get('content', '')}\n\n")
    
    def get_findings(self) -> List[tuple]:
        """Get all research findings."""
        return self.findings


# ------------------
# Custom Tool Creation
# ------------------

@tool(name="web_search", description="Search the web for information on a topic")
def web_search(query: str) -> str:
    """Simulate a web search with mock results.
    
    In a real implementation, this would call a search API or web scraper.
    For this example, we'll return mock data based on the query keywords.
    """
    mock_results = {
        "machine learning": (
            "Machine learning is a branch of artificial intelligence that focuses on developing "
            "systems that can learn from and make decisions based on data. It employs algorithms "
            "that can receive input data and use statistical analysis to predict an output while "
            "updating outputs as new data becomes available."
        ),
        "neural networks": (
            "Neural networks are computing systems inspired by the biological neural networks "
            "in animal brains. They consist of artificial neurons that can learn to perform "
            "tasks by considering examples, without being explicitly programmed with task-specific rules. "
            "They are used in applications like computer vision, speech recognition, and natural "
            "language processing."
        ),
        "data science": (
            "Data science is an interdisciplinary field that uses scientific methods, processes, "
            "algorithms and systems to extract knowledge and insights from structured and unstructured "
            "data. It employs techniques from many fields, including statistics, computer science, "
            "and domain knowledge."
        )
    }
    
    # Search in our mock database
    for keyword, result in mock_results.items():
        if keyword.lower() in query.lower():
            return result
    
    # Default response if no keywords match
    return (
        "No specific information found for this query. Try searching for "
        "'machine learning', 'neural networks', or 'data science'."
    )


@tool(name="summarize", description="Summarize a piece of text")
def summarize(text: str, max_length: int = 100) -> str:
    """Summarize text to a specified maximum length.
    
    In a real implementation, this would use an LLM or extractive summarization.
    For this example, we'll just truncate the text.
    """
    if len(text) <= max_length:
        return text
    
    # Simple truncation-based summary
    return text[:max_length] + "..."


@tool(name="take_notes", description="Save research notes to a file")
def take_notes(title: str, content: str) -> str:
    """Save notes to a file.
    
    Args:
        title: The title of the note
        content: The content of the note
    
    Returns:
        A confirmation message
    """
    filename = f"notes_{title.replace(' ', '_').lower()}.txt"
    
    with open(filename, "w") as f:
        f.write(f"# {title}\n\n")
        f.write(f"{content}\n")
    
    return f"Notes saved to {filename}"


# -----------------------------
# MCP Resource Implementation
# -----------------------------

def setup_mcp_resources(mcp_manager):
    """Set up custom MCP resources."""
    
    @mcp_manager.mcp.resource("research://topics")
    def get_research_topics(ctx: MCPContext) -> List[str]:
        """Return a list of available research topics."""
        return ["machine learning", "neural networks", "data science"]
    
    @mcp_manager.mcp.resource("research://findings/{topic}")
    def get_research_findings(topic: str, ctx: MCPContext) -> str:
        """Return research findings for a specific topic."""
        findings = ctx.state.get("findings", {})
        return findings.get(topic, f"No findings available for {topic}")


# -------------------------
# Event Publishing Helpers
# -------------------------

def publish_research_finding(event_bus, finding, source):
    """Publish a research finding event."""
    event_bus.publish(Event.create(
        type="research:finding",
        source=source,
        finding=finding,
        timestamp=datetime.now().isoformat()
    ))


# --------------------------
# Main Application Function
# --------------------------

async def main():
    """Main application function."""
    
    # -----------------------------------
    # 1. Setup: Configuration & Symphony
    # -----------------------------------
    print("\n=== Setting up Symphony ===\n")
    
    # Create configuration
    config = SymphonyConfig(
        application_name="Research Assistant",
        debug=True,
        log_level="INFO",
        llm_provider="mock",  # Use mock for demo (no API keys needed)
        default_agent_type="reactive"
    )
    
    # Initialize Symphony
    symphony = Symphony(config)
    container = symphony.get_container()
    event_bus = symphony.get_event_bus()
    plugin_manager = symphony.get_plugin_manager()
    
    # Register the research logger plugin
    plugin_manager.register_plugin(ResearchLoggerPlugin())
    
    # -----------------------------------
    # 2. Component Creation with Factories
    # -----------------------------------
    print("Creating components...")
    
    # Create prompt registry
    prompt_registry = PromptRegistry()
    container.register("prompt_registry", prompt_registry)
    
    # Register prompts for different agent types
    prompt_registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a Research Agent. Your role is to find information on topics "
            "using the web_search tool. Be thorough in your searches."
        ),
        agent_type="ResearcherAgent"
    )
    
    prompt_registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a Planning Agent. Your role is to create and follow plans "
            "for research tasks. Break complex tasks into manageable steps."
        ),
        agent_type="PlannerAgent"
    )
    
    # Create mock LLM client with simulated responses
    mock_responses = {
        # Researcher responses
        "Research the topic of machine learning": 
            "I'll search for information on machine learning.\n\n"
            "From my search: Machine learning is a branch of artificial intelligence that focuses on "
            "developing systems that can learn from and make decisions based on data.",
        
        # Planner responses
        "I need to research neural networks and summarize the findings": 
            "I'll help you research neural networks and summarize the findings. Let me create a plan:\n\n"
            "1. Search for information about neural networks\n"
            "2. Summarize the key findings\n"
            "3. Save the information as notes",
    }
    llm_client = LLMClientFactory.create_mock(responses=mock_responses)
    container.register("llm_client", llm_client)
    
    # Create memory with factory
    memory = MemoryFactory.create("conversation")
    container.register("memory", memory)
    
    # Create MCP manager with factory
    mcp_config = MCPConfig(app_name="Research Assistant")
    mcp_manager = MCPManagerFactory.create(config=mcp_config)
    setup_mcp_resources(mcp_manager)
    container.register("mcp_manager", mcp_manager)
    
    # -----------------------------------
    # 3. Agent Creation
    # -----------------------------------
    print("Creating agents...")
    
    # Create researcher agent configuration
    researcher_config = AgentConfig(
        name="Researcher",
        agent_type="ResearcherAgent",
        description="An agent that searches for information",
        tools=["web_search", "take_notes"],
        mcp_enabled=True
    )
    
    # Create planner agent configuration
    planner_config = AgentConfig(
        name="ResearchPlanner",
        agent_type="PlannerAgent",
        description="An agent that plans and executes research tasks",
        tools=["web_search", "summarize", "take_notes"],
        mcp_enabled=True
    )
    
    # Create the agents
    researcher_agent = ReactiveAgent(
        config=researcher_config,
        llm_client=llm_client,
        prompt_registry=prompt_registry,
        memory=memory,
        mcp_manager=mcp_manager
    )
    
    planner_agent = PlannerAgent(
        config=planner_config,
        llm_client=llm_client,
        prompt_registry=prompt_registry,
        memory=memory,
        mcp_manager=mcp_manager
    )
    
    # -----------------------------------
    # 4. Using the Researcher Agent
    # -----------------------------------
    print("\n=== Using the Researcher Agent ===\n")
    
    # Publish event that we're starting research
    event_bus.publish(Event.create(
        type=EventType.AGENT_STARTED,
        source="main",
        agent_name=researcher_agent.config.name
    ))
    
    # Run the researcher agent
    research_task = "Research the topic of machine learning"
    print(f"Task: {research_task}")
    
    research_result = await researcher_agent.run(research_task)
    print(f"Result: {research_result}")
    
    # Extract and log the finding
    publish_research_finding(
        event_bus, 
        finding=research_result,
        source=researcher_agent.config.name
    )
    
    # -----------------------------------
    # 5. Using the Planner Agent
    # -----------------------------------
    print("\n=== Using the Planner Agent ===\n")
    
    # Publish event that we're starting planning
    event_bus.publish(Event.create(
        type=EventType.AGENT_STARTED,
        source="main",
        agent_name=planner_agent.config.name
    ))
    
    # Run the planner agent
    planning_task = "I need to research neural networks and summarize the findings"
    print(f"Task: {planning_task}")
    
    planning_result = await planner_agent.run(planning_task)
    print(f"Result: {planning_result}")
    
    # Extract and log the finding
    publish_research_finding(
        event_bus, 
        finding=planning_result,
        source=planner_agent.config.name
    )
    
    # -----------------------------------
    # 6. Summary and Cleanup
    # -----------------------------------
    print("\n=== Research Summary ===\n")
    
    # Get findings from the research logger plugin
    research_logger = plugin_manager.get_plugin("research_logger")
    findings = research_logger.get_findings()
    
    print(f"Collected {len(findings)} research findings:")
    for i, (finding, source) in enumerate(findings, 1):
        print(f"{i}. From {source}: {finding[:50]}...")
    
    # Cleanup
    symphony.cleanup()
    print("\nApplication completed successfully.")


# -----------------------------------
# Application Entry Point
# -----------------------------------

if __name__ == "__main__":
    asyncio.run(main())