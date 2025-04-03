"""Example of a planning agent using the Symphony framework."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig
from symphony.agents.planning import PlannerAgent
from symphony.llm.base import MockLLMClient
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import tool
from symphony.utils.types import Message


# Define a web search tool
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


# Define a note-taking tool
@tool(name="take_notes", description="Save notes to a notebook")
def take_notes(title: str, content: str) -> str:
    """Simulate saving notes to a notebook."""
    print(f"\n--- Note Saved ---\nTitle: {title}\nContent: {content}\n-----------------")
    return f"Note saved: {title}"


# Define a summarization tool
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
    # Create a prompt registry
    registry = PromptRegistry()
    
    # Register a system prompt for the planner agent
    registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a Planning Agent that creates and follows step-by-step plans "
            "to complete tasks. You have access to the following tools:\n"
            "- web_search: Search the web for information\n"
            "- take_notes: Save notes to a notebook\n"
            "- summarize: Summarize text\n\n"
            "For each task, create a plan of 2-4 steps, then execute each step in sequence."
        ),
        agent_type="PlannerAgent"
    )
    
    # Create a mock LLM client with predefined responses
    llm_client = MockLLMClient(responses={
        # Planning responses
        "Based on the above context, create a step-by-step plan to complete the task. Format your response as a JSON array of steps, where each step has a 'description' field. For example: [{'description': 'Search for information about X'}, {'description': 'Summarize findings'}]": 
            '[{"description": "Search for information about the capitals of countries"}, {"description": "Summarize the information found"}, {"description": "Save the summary as notes"}]',
        
        # Step execution responses
        "Current step to execute: Search for information about the capitals of countries\n\nComplete this step and provide your results.":
            "I'll search for information about capitals of countries.\n\nResults from web_search: The capital of France is Paris. The capital of Japan is Tokyo.",
        
        "Current step to execute: Summarize the information found\n\nComplete this step and provide your results.":
            "I'll summarize the information found.\n\nSummary: Paris is the capital of France, and Tokyo is the capital of Japan.",
        
        "Current step to execute: Save the summary as notes\n\nComplete this step and provide your results.":
            "I'll save these findings as notes.\n\nSaved note with title 'Country Capitals' containing: 'Paris is the capital of France, and Tokyo is the capital of Japan.'"
    })
    
    # Create an agent config with the tools
    agent_config = AgentConfig(
        name="ResearchPlanner",
        agent_type="PlannerAgent",
        description="An agent that plans and executes research tasks",
        tools=["web_search", "take_notes", "summarize"]
    )
    
    # Create a planner agent
    agent = PlannerAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    # Run the agent with a research task
    task = "Find information about the capitals of countries and save it to my notes."
    print(f"\nTask: {task}")
    response = await agent.run(task)
    print(f"\nFinal Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())