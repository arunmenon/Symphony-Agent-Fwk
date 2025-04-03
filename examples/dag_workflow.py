"""Example of a DAG-based workflow using the Symphony framework."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.base import MockLLMClient
from symphony.orchestration.base import OrchestratorConfig
from symphony.orchestration.dag import DAG, DAGOrchestrator, Edge, Node, NodeType
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
    
    # Register system prompts for different agent types
    registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a Researcher Agent. Your job is to find accurate information "
            "using the web_search tool. Be thorough and precise in your searches."
        ),
        agent_type="ResearcherAgent"
    )
    
    registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a Writer Agent. Your job is to take information and create "
            "well-written, concise summaries. Use the summarize tool when appropriate."
        ),
        agent_type="WriterAgent"
    )
    
    registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a Decision Agent. Your job is to look at information and make "
            "recommendations based on it. Be clear and decisive in your recommendations."
        ),
        agent_type="DecisionAgent"
    )
    
    # Create a mock LLM client with predefined responses
    llm_client = MockLLMClient(responses={
        # Researcher agent responses
        "Find information about the weather today": 
            "Based on my search: The weather is sunny with a high of 75°F.",
        
        # Writer agent responses (depends on the output of the Researcher)
        "The weather is sunny with a high of 75°F.": 
            "Today's weather report: Sunny conditions with temperatures reaching up to 75°F.",
        
        # Decision agent responses (depends on the output of the Writer)
        "Today's weather report: Sunny conditions with temperatures reaching up to 75°F.": 
            "Given the sunny weather with a comfortable temperature of 75°F, I recommend outdoor activities today. "
            "It's perfect for hiking, picnics, or any outdoor sports.",
            
        # Condition outcomes (used for both branches)
        "Looking at your query about the weather today, I'll help you find the relevant information.":
            "I'll check the current weather conditions for you."
    })
    
    # Create agent configs
    researcher_config = AgentConfig(
        name="Researcher",
        agent_type="ResearcherAgent",
        tools=["web_search"]
    )
    
    writer_config = AgentConfig(
        name="Writer",
        agent_type="WriterAgent",
        tools=["summarize"]
    )
    
    decision_config = AgentConfig(
        name="Advisor",
        agent_type="DecisionAgent",
        tools=[]
    )
    
    # Create orchestrator config with all agents
    orchestrator_config = OrchestratorConfig(
        agent_configs=[researcher_config, writer_config, decision_config],
        max_steps=10
    )
    
    # Create a DAG orchestrator
    orchestrator = DAGOrchestrator(
        config=orchestrator_config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    # Initialize agents (needed for DAG orchestrator)
    orchestrator.agents = {
        "Researcher": ReactiveAgent(config=researcher_config, llm_client=llm_client, prompt_registry=registry),
        "Writer": ReactiveAgent(config=writer_config, llm_client=llm_client, prompt_registry=registry),
        "Advisor": ReactiveAgent(config=decision_config, llm_client=llm_client, prompt_registry=registry)
    }
    
    # Create a workflow DAG
    dag = DAG()
    
    # Add nodes
    dag.add_node(Node(id="start", type=NodeType.START))
    dag.add_node(Node(id="condition", type=NodeType.CONDITION, config={"condition": "weather"}))
    dag.add_node(Node(id="researcher", type=NodeType.AGENT, config={"agent_name": "Researcher"}))
    dag.add_node(Node(id="writer", type=NodeType.AGENT, config={"agent_name": "Writer"}))
    dag.add_node(Node(id="advisor", type=NodeType.AGENT, config={"agent_name": "Advisor"}))
    dag.add_node(Node(id="end", type=NodeType.END))
    
    # Add edges
    dag.add_edge(Edge(source="start", target="condition"))
    dag.add_edge(Edge(source="condition", target="researcher"))  # Weather-related path
    dag.add_edge(Edge(source="researcher", target="writer"))
    dag.add_edge(Edge(source="writer", target="advisor"))
    dag.add_edge(Edge(source="advisor", target="end"))
    
    # Set the DAG in the orchestrator
    orchestrator.set_dag(dag)
    
    # Run the workflow
    query = "What's the weather today and what should I do?"
    print(f"\nQuery: {query}")
    result = await orchestrator.run(query)
    print(f"\nFinal Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())