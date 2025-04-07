"""Example demonstrating Symphony's memory manager capabilities.

This example showcases how to use Symphony's multi-tier memory system with
various memory types including working memory, long-term (vector) memory,
and knowledge graph memory.

Key concepts demonstrated:
1. Creating and configuring different memory types
2. Storing information with importance-based routing
3. Retrieving information from specific memory systems
4. Memory consolidation (transferring important info to long-term storage)
5. Creating an agent with advanced memory capabilities
6. Conversation searching and knowledge extraction

The memory manager provides a centralized system for memory coordination,
automatically routing important information to appropriate storage tiers
and providing unified retrieval capabilities.

IMPORTANT: For production use, especially with LLM-based memory components,
use powerful/advanced models for optimal results, as importance assessment
requires sophisticated reasoning for effective memory operations.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.memory.memory_manager import ConversationMemoryManager, MemoryManager, WorkingMemory
from symphony.memory.vector_memory import VectorMemory, SimpleEmbedder
from symphony.memory.local_kg_memory import LocalKnowledgeGraphMemory, SimpleEmbeddingModel
from symphony.utils.types import Message


class SimpleMemoryAgent:
    """Simple agent with memory capabilities."""
    
    def __init__(self, memory=None):
        """Initialize the agent with memory manager."""
        # Create memory manager if none provided
        self.memory = memory or ConversationMemoryManager()
        self.responses = {
            "What can you tell me about memory management?": 
                "Memory management involves efficiently organizing, storing, and retrieving information. In AI systems, it's crucial for maintaining context, prioritizing important information, and simulating human-like recall.",
                
            "Why is working memory important?": 
                "Working memory is crucial because it holds immediately relevant information for current tasks. It has limited capacity but fast access, helping to maintain focus on what's important right now. In AI systems, it provides quick access to recent context without the overhead of searching through long-term memory.",
                
            "search: memory systems": 
                "I'll check my memory for information about memory systems."
        }
    
    async def run(self, input_message: str) -> str:
        """Run the agent with memory management."""
        # Check if the message is a search query
        if input_message.startswith("search:"):
            query = input_message[7:].strip()
            return await self._search_memory(query)
            
        # Add user message to memory
        user_message = Message(role="user", content=input_message)
        await self.memory.add_message(user_message)
        
        # Get response (simulated)
        response = self.responses.get(input_message, "I don't have a specific answer for that.")
        
        # Add assistant's response to memory
        assistant_message = Message(role="assistant", content=response)
        await self.memory.add_message(assistant_message)
            
        return response
    
    async def _search_memory(self, query: str) -> str:
        """Search memory for relevant information."""
        results = await self.memory.search_conversation(query, limit=5)
        
        # Format results
        if not results:
            return "I couldn't find any relevant information in my memory."
            
        formatted_results = ["Here's what I found in my memory:"]
        for i, message in enumerate(results, 1):
            formatted_results.append(f"\n{i}. [{message.role}]: {message.content}")
        
        return "\n".join(formatted_results)


class MockLLMClient:
    """Simple mock LLM client for demonstration purposes."""
    
    async def generate(self, prompt: str) -> str:
        """Generate a response for the given prompt."""
        # For knowledge graph extraction, return some sample triplets
        if "Extract knowledge triplets" in prompt:
            return """{"subject": "memory manager", "predicate": "coordinates", "object": "memory systems", "confidence": 0.95}
{"subject": "working memory", "predicate": "has characteristic", "object": "short-term storage", "confidence": 0.9}
{"subject": "long-term memory", "predicate": "stores", "object": "important information", "confidence": 0.85}
{"subject": "memory consolidation", "predicate": "moves", "object": "information between memory systems", "confidence": 0.9}"""
        
        # Default response
        return "This is a mock response."


async def main():
    """Run the memory manager example."""
    print("=== Memory Manager Example ===\n")
    
    # Scenario 1: Basic Memory Manager
    print("Scenario 1: Basic Memory Manager")
    
    # Create memory components with explicit configuration
    working_memory = WorkingMemory(retention_period=3600)  # 1 hour retention
    vector_memory = VectorMemory(embedder=SimpleEmbedder(dimension=128))
    
    # Create a memory manager
    memory_manager = MemoryManager(
        working_memory=working_memory,
        long_term_memory=vector_memory
    )
    
    # Store information with different importance levels
    print("Storing information with different importance levels...")
    await memory_manager.store(
        key="task_reminder", 
        value="Remember to complete the project by Friday",
        importance=0.9  # High importance
    )
    
    await memory_manager.store(
        key="casual_fact",
        value="The weather is nice today",
        importance=0.3  # Low importance
    )
    
    # Retrieve information
    print("\nRetrieving information...")
    important_info = await memory_manager.retrieve(key="task_reminder")
    casual_info = await memory_manager.retrieve(key="casual_fact")
    
    print(f"Important info: {important_info}")
    print(f"Casual info: {casual_info}")
    
    # Simulate time passing and memory consolidation
    print("\nSimulating memory consolidation...")
    await memory_manager.consolidate()
    
    # Scenario 2: Conversation Memory Manager with Knowledge Graph
    print("\nScenario 2: Conversation Memory Manager with Knowledge Graph")
    
    # Create a mock LLM client for knowledge extraction
    mock_llm = MockLLMClient()
    
    # Create a temporary storage path for the knowledge graph
    kg_storage_path = os.path.join(os.path.dirname(__file__), "temp_kg.pkl")
    
    # Create memory components
    working_memory = WorkingMemory(retention_period=3600)
    vector_memory = VectorMemory(embedder=SimpleEmbedder(dimension=128))
    
    # Create a knowledge graph memory with the mock LLM client
    kg_memory = LocalKnowledgeGraphMemory(
        llm_client=mock_llm,
        embedding_model=SimpleEmbeddingModel(dimension=128),
        storage_path=kg_storage_path,
        auto_extract=True
    )
    
    # Create a conversation memory manager with all memory systems
    conversation_memory = ConversationMemoryManager(
        working_memory=working_memory,
        long_term_memory=vector_memory,
        kg_memory=kg_memory
    )
    
    # Add some conversation messages
    print("Adding messages to conversation memory...")
    await conversation_memory.add_message(Message(
        role="user",
        content="What are the key benefits of using a memory manager?"
    ))
    
    await conversation_memory.add_message(Message(
        role="assistant",
        content="The key benefits of using a memory manager include: centralized control over different memory systems, automatic prioritization of information, flexible storage strategies based on importance, and efficient retrieval across multiple memory types."
    ))
    
    await conversation_memory.add_message(Message(
        role="user",
        content="How does the importance scoring work?"
    ))
    
    await conversation_memory.add_message(Message(
        role="assistant",
        content="Importance scoring uses heuristics to determine what information should be retained longer. Questions, action items, and critical decisions receive higher scores. The system can be extended with more sophisticated scoring mechanisms like semantic relevance, recency, and alignment with goals."
    ))
    
    await conversation_memory.add_message(Message(
        role="user",
        content="Can you provide an example of memory consolidation?"
    ))
    
    await conversation_memory.add_message(Message(
        role="assistant",
        content="Memory consolidation moves important information from working memory to long-term memory. For example, if you mention a critical deadline during our conversation, that information would initially be stored in working memory. During consolidation, its high importance score would trigger it to be transferred to long-term memory for persistent storage, while less important details might be discarded from working memory."
    ))
    
    # Run memory consolidation to extract knowledge
    print("\nRunning memory consolidation to extract knowledge triplets...")
    await conversation_memory.consolidate()
    
    # Search conversation using different memory systems
    search_queries = [
        "importance scoring",
        "memory consolidation",
        "benefits"
    ]
    
    print("\nSearch results from combined memory systems:")
    for query in search_queries:
        print(f"\nSearching for: '{query}'")
        results = await conversation_memory.search_conversation(query, limit=1)
        for i, message in enumerate(results, 1):
            print(f"  {i}. [{message.role}]: {message.content[:100]}...")
    
    # Scenario 3: Agent with Memory Manager
    print("\nScenario 3: Agent with Memory Manager")
    
    # Create agent with conversation memory manager
    agent = SimpleMemoryAgent(memory=conversation_memory)  # Use the conversation memory we already populated
    
    # Demonstrate interactions
    questions = [
        "What can you tell me about memory management?",
        "Why is working memory important?",
        "search: memory systems"
    ]
    
    for question in questions:
        print(f"\nUser: {question}")
        response = await agent.run(question)
        print(f"Agent: {response}")
        
    # Clean up temporary files
    if os.path.exists(kg_storage_path):
        os.remove(kg_storage_path)


if __name__ == "__main__":
    asyncio.run(main())