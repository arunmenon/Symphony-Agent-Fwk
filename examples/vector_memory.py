"""Example demonstrating Symphony's vector memory capabilities.

This example showcases Symphony's vector-based memory system for long-term
semantic storage and retrieval, which enables agents to find relevant information
based on meaning rather than exact keyword matching.

Key concepts demonstrated:
1. Vector memory creation and configuration
2. Embedding generation for semantic similarity
3. Conversation memory with vector storage
4. Semantic search capabilities
5. Agent integration with advanced memory retrieval
6. Memory persistence across sessions

Vector memory provides the foundation for long-term memory in agents, enabling them
to store and retrieve information based on semantic meaning and relevance rather than
exact matches, significantly enhancing their ability to maintain context.

IMPORTANT: For production use, utilize high-quality embedding models to ensure
optimal semantic search results and retrieval performance.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.base import MockLLMClient
from symphony.memory.vector_memory import ConversationVectorMemory, SimpleEmbedder, VectorMemory
from symphony.prompts.registry import PromptRegistry
from symphony.utils.types import Message


class MemoryEnhancedAgent(ReactiveAgent):
    """Agent with enhanced vector memory capabilities."""
    
    async def run(self, input_message: str) -> str:
        """Run the agent with vector memory retrieval."""
        # Check if the message is a search query
        if input_message.startswith("search:"):
            query = input_message[7:].strip()
            return await self._search_memory(query)
            
        # Otherwise, process normally and save to memory
        return await super().run(input_message)
    
    async def _search_memory(self, query: str) -> str:
        """Search memory for relevant messages."""
        if isinstance(self.memory, VectorMemory):
            results = self.memory.search(query, limit=5, include_metadata=True)
            
            # Format results
            if not results:
                return "I couldn't find any relevant information in my memory."
                
            formatted_results = ["Here's what I found in my memory:"]
            for i, (content, metadata) in enumerate(results, 1):
                timestamp = metadata.get("timestamp", "unknown time")
                if isinstance(timestamp, (int, float)):
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
                
                formatted_results.append(f"\n{i}. {content}")
                if "source" in metadata:
                    formatted_results.append(f"   Source: {metadata['source']}")
                if timestamp != "unknown time":
                    formatted_results.append(f"   Time: {timestamp}")
            
            return "\n".join(formatted_results)
        else:
            return "Vector memory search is not available."


async def main():
    """Run the example."""
    print("=== Vector Memory Example ===\n")
    
    # Set up a simple embedder
    embedder = SimpleEmbedder(dimension=50)
    
    # Scenario 1: Basic Vector Memory
    print("Scenario 1: Basic Vector Memory")
    
    # Create a vector memory
    memory = VectorMemory(embedder=embedder)
    
    # Store some knowledge
    print("Storing knowledge in vector memory...")
    memory.store(
        key="python", 
        value="Python is a high-level, interpreted programming language known for its readability and versatility."
    )
    
    memory.store(
        key="javascript",
        value="JavaScript is a programming language used primarily for web development, allowing interactive elements on websites."
    )
    
    memory.store(
        key="machine_learning",
        value="Machine learning is a field of AI that enables systems to learn from data and improve without explicit programming."
    )
    
    memory.store(
        key="data_science",
        value="Data science combines statistics, data analysis, and machine learning to interpret complex data."
    )
    
    memory.store(
        key="computer_vision",
        value="Computer vision is an AI field that enables computers to derive information from images and videos."
    )
    
    # Demonstrate semantic search
    queries = [
        "programming languages",
        "artificial intelligence",
        "data analysis and statistics"
    ]
    
    for query in queries:
        print(f"\nSearching for: '{query}'")
        results = memory.search(query, limit=3)
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result[:100]}...")
    
    # Scenario 2: Conversation Vector Memory
    print("\nScenario 2: Conversation Vector Memory")
    
    # Create a conversation vector memory
    conversation_memory = ConversationVectorMemory(embedder=embedder)
    
    # Add some conversation messages
    print("Adding messages to conversation memory...")
    conversation_memory.add_message(Message(
        role="user",
        content="Can you explain how neural networks work?"
    ))
    
    conversation_memory.add_message(Message(
        role="assistant",
        content="Neural networks are computing systems inspired by the biological neural networks in human brains. They consist of nodes (neurons) connected by weights and process information using a connectionist approach. Deep learning uses multiple layers of these networks to solve complex problems."
    ))
    
    conversation_memory.add_message(Message(
        role="user",
        content="What are some applications of neural networks?"
    ))
    
    conversation_memory.add_message(Message(
        role="assistant",
        content="Neural networks have many applications, including: image and speech recognition, natural language processing, recommendation systems, medical diagnosis, financial forecasting, autonomous vehicles, and game playing."
    ))
    
    conversation_memory.add_message(Message(
        role="user",
        content="How is Python used in data science?"
    ))
    
    conversation_memory.add_message(Message(
        role="assistant",
        content="Python is widely used in data science because of libraries like NumPy for numerical computations, Pandas for data manipulation, Matplotlib and Seaborn for visualization, and scikit-learn, TensorFlow, and PyTorch for machine learning and deep learning. Its readability and extensive ecosystem make it ideal for data analysis workflows."
    ))
    
    # Search the conversation
    search_queries = [
        "deep learning",
        "Python libraries",
        "recognition technology"
    ]
    
    for query in search_queries:
        print(f"\nSearching conversation for: '{query}'")
        results = conversation_memory.search_messages(query, limit=2)
        for i, message in enumerate(results, 1):
            print(f"  {i}. [{message.role}]: {message.content[:100]}...")
    
    # Scenario 3: Agent with Vector Memory
    print("\nScenario 3: Agent with Vector Memory")
    
    # Create prompt registry
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content="You are a knowledgeable assistant with excellent memory capabilities.",
        agent_type="reactive"
    )
    
    # Create mock LLM client
    llm_client = MockLLMClient(responses={
        "What can you tell me about machine learning?": 
            "Machine learning is a field of artificial intelligence that focuses on developing systems that learn from data without being explicitly programmed. It encompasses various techniques including supervised learning, unsupervised learning, and reinforcement learning.",
            
        "Tell me about neural networks": 
            "Neural networks are computational models inspired by the human brain's structure and function. They consist of interconnected nodes (neurons) that process information. Deep neural networks have multiple layers and can learn complex patterns, making them powerful tools for tasks like image recognition and natural language processing."
    })
    
    # Create agent configuration
    agent_config = AgentConfig(
        name="MemoryAgent",
        agent_type="reactive",
        description="An agent with vector memory capabilities"
    )
    
    # Create agent with vector memory
    agent = MemoryEnhancedAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=registry,
        memory=conversation_memory  # Use the conversation memory we already populated
    )
    
    # Demonstrate regular interactions
    questions = [
        "What can you tell me about machine learning?",
        "Tell me about neural networks"
    ]
    
    for question in questions:
        print(f"\nUser: {question}")
        response = await agent.run(question)
        print(f"Agent: {response}")
    
    # Demonstrate memory search
    search_requests = [
        "search: deep learning",
        "search: Python data science",
        "search: applications"
    ]
    
    for request in search_requests:
        print(f"\nUser: {request}")
        response = await agent.run(request)
        print(f"Agent: {response}")


if __name__ == "__main__":
    asyncio.run(main())