"""Example of a multi-agent system using the Symphony framework."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.agents.planning import PlannerAgent
from symphony.environment.base import InMemoryEnvironment
from symphony.llm.base import MockLLMClient
from symphony.orchestration.base import MultiAgentOrchestrator, OrchestratorConfig, TurnType
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import tool
from symphony.utils.types import Message


# Define a simple web search tool
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


# Define a simple summarization tool
@tool(name="summarize", description="Summarize a piece of text")
def summarize(text: str) -> str:
    """Simulate text summarization."""
    words = text.split()
    if len(words) <= 10:
        return text  # Text already short enough
    
    # Very simple summarization: take first sentence or first few words
    if "." in text:
        return text.split(".")[0] + "."
    else:
        return " ".join(words[:10]) + "..."


async def main():
    # Create a prompt registry with system prompts for different agent types
    registry = PromptRegistry()
    
    # Researcher agent prompt
    registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a Research Agent. Your role is to find information "
            "using the web_search tool. Be thorough and precise in your searches."
        ),
        agent_type="ResearcherAgent"
    )
    
    # Writer agent prompt
    registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a Writer Agent. Your role is to take information provided "
            "by the Researcher and create well-written, concise summaries. "
            "Use the summarize tool when appropriate. Focus on clarity and brevity."
        ),
        agent_type="WriterAgent"
    )
    
    # Create a mock LLM client with predefined responses
    llm_client = MockLLMClient(responses={
        # Research agent responses
        "what is the weather today": "Let me search for the current weather.\n\n"
                                     "Based on my search: The weather is sunny with a high of 75°F.",
        "what is the capital of France": "Let me search for information about France's capital.\n\n"
                                        "According to my search: The capital of France is Paris.",
        
        # Writer agent responses
        "The weather is sunny with a high of 75°F.": "Based on research, today will be sunny with a high of 75°F - "
                                                    "perfect weather for outdoor activities.",
        "According to my search: The capital of France is Paris.": "Paris is the capital city of France, known for "
                                                                  "its art, culture, and historic landmarks."
    })
    
    # Create agent configs
    researcher_config = AgentConfig(
        name="Researcher",
        agent_type="ResearcherAgent",
        description="An agent that searches for information",
        tools=["web_search"]
    )
    
    writer_config = AgentConfig(
        name="Writer",
        agent_type="WriterAgent",
        description="An agent that writes summaries",
        tools=["summarize"]
    )
    
    # Create an orchestrator config
    orchestrator_config = OrchestratorConfig(
        agent_configs=[researcher_config, writer_config],
        max_steps=5
    )
    
    # Create the environment
    environment = InMemoryEnvironment()
    
    # Create a multi-agent orchestrator
    orchestrator = MultiAgentOrchestrator(
        config=orchestrator_config,
        llm_client=llm_client,
        prompt_registry=registry,
        agent_classes={
            "ResearcherAgent": ReactiveAgent,
            "WriterAgent": ReactiveAgent
        },
        environment=environment,
        turn_type=TurnType.SEQUENTIAL  # First Researcher, then Writer
    )
    
    # Run the multi-agent system with a few test questions
    for question in [
        "what is the weather today",
        "what is the capital of France"
    ]:
        print(f"\nQuestion: {question}")
        response = await orchestrator.run(question)
        print(f"Final Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())