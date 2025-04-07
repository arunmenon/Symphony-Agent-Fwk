"""Example demonstrating Symphony's knowledge graph memory capabilities.

This example showcases Symphony's knowledge graph memory system, which extracts and
stores structured relationships from unstructured text, enabling more sophisticated
knowledge representation and reasoning capabilities.

Key concepts demonstrated:
1. Knowledge graph memory creation and configuration
2. Knowledge extraction from text into subject-predicate-object triplets
3. Storing structured knowledge relationships
4. Querying the knowledge graph for specific relationships
5. Agent integration with knowledge graph capabilities
6. Graph-based reasoning and relationship traversal

Knowledge graph memory provides a structured way to represent relationships between
entities, enabling more sophisticated reasoning, fact validation, and relationship
exploration than flat vector storage alone.

IMPORTANT: For optimal knowledge extraction, use advanced language models with
strong reasoning capabilities that can accurately identify relationships and
generate consistent knowledge triplets.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.agents.kg_enhanced import KnowledgeGraphEnhancedAgentMixin
from symphony.llm.base import MockLLMClient
from symphony.memory.kg_memory import (
    ConversationKnowledgeGraphMemory,
    GraphitiConfig,
    KnowledgeGraphMemory,
    Triplet,
)
from symphony.prompts.registry import PromptRegistry
from symphony.utils.types import Message


class KGEnhancedAgent(ReactiveAgent, KnowledgeGraphEnhancedAgentMixin):
    """A reactive agent with knowledge graph capabilities."""
    
    async def run(self, input_message: str) -> str:
        """Run the agent with knowledge graph augmentation."""
        # Check if the message is a KG-specific command
        if input_message.startswith("kg:"):
            return await self._handle_kg_command(input_message[3:].strip())
            
        # Enrich the message with knowledge if using a KG memory
        message = Message(role="user", content=input_message)
        enriched_message = await self.enrich_message_with_knowledge(message)
        
        # Add knowledge context to system prompt if available
        original_system_prompt = self.system_prompt
        
        if "knowledge_context" in enriched_message.additional_kwargs:
            knowledge = enriched_message.additional_kwargs["knowledge_context"]
            if knowledge:
                knowledge_str = "\n".join([f"- {item}" for item in knowledge])
                self.system_prompt = f"{original_system_prompt}\n\nRelevant Knowledge:\n{knowledge_str}"
        
        # Run with the enriched message
        result = await super().run(enriched_message.content)
        
        # Extract knowledge from the input and response
        if self.kg_memory and hasattr(self.kg_memory, "extract_and_store"):
            # Extract from user input
            await self.extract_knowledge_from_text(input_message)
            
            # Extract from agent response
            await self.extract_knowledge_from_text(result)
        
        # Restore original system prompt
        self.system_prompt = original_system_prompt
        
        return result
    
    async def _handle_kg_command(self, command: str) -> str:
        """Handle knowledge graph specific commands.
        
        Args:
            command: The command to handle (without the "kg:" prefix)
            
        Returns:
            Result of the command
        """
        if not self.kg_memory:
            return "Knowledge graph memory is not available."
            
        parts = command.split(" ", 1)
        cmd = parts[0].lower()
        
        if cmd == "add" and len(parts) > 1:
            # Format: add subject|predicate|object
            try:
                triplet_parts = parts[1].split("|")
                if len(triplet_parts) == 3:
                    subject, predicate, object_value = triplet_parts
                    success = await self.add_knowledge_triplet(
                        subject=subject.strip(),
                        predicate=predicate.strip(),
                        object=object_value.strip()
                    )
                    return f"Knowledge triplet added: {subject} {predicate} {object_value}" if success else "Failed to add triplet."
                else:
                    return "Invalid triplet format. Use: add subject|predicate|object"
            except Exception as e:
                return f"Error adding triplet: {str(e)}"
                
        elif cmd == "search" and len(parts) > 1:
            # Format: search query
            query = parts[1]
            results = await self.search_knowledge(query, limit=5)
            
            if not results:
                return f"No results found for query: {query}"
                
            formatted_results = ["Knowledge graph search results:"]
            for i, result in enumerate(results, 1):
                if isinstance(result, dict) and "subject" in result and "predicate" in result and "object" in result:
                    formatted_results.append(f"{i}. {result['subject']} {result['predicate']} {result['object']}")
                else:
                    formatted_results.append(f"{i}. {result}")
                    
            return "\n".join(formatted_results)
            
        elif cmd == "entity" and len(parts) > 1:
            # Format: entity name
            entity = parts[1]
            connections = await self.get_entity_knowledge(entity)
            
            if not connections or not connections.get("triplets"):
                return f"No information found for entity: {entity}"
                
            formatted_results = [f"Knowledge about entity '{entity}':"]
            for triplet in connections.get("triplets", []):
                if "subject" in triplet and "predicate" in triplet and "object" in triplet:
                    if triplet["subject"] == entity:
                        formatted_results.append(f"- {triplet['predicate']} {triplet['object']}")
                    else:
                        formatted_results.append(f"- Is {triplet['predicate']} by {triplet['subject']}")
                        
            return "\n".join(formatted_results)
        
        else:
            return (
                "Available KG commands:\n"
                "- kg:add subject|predicate|object - Add a knowledge triplet\n"
                "- kg:search query - Search the knowledge graph\n"
                "- kg:entity name - Get information about an entity"
            )


# Mock Graphiti client for examples
class MockGraphitiClient:
    """Mock Graphiti client for examples."""
    
    def __init__(self):
        self.triplets = []
        self.documents = {}
    
    async def ingest_text(self, text, document_id=None):
        """Mock ingest text."""
        if not document_id:
            document_id = f"doc_{len(self.documents)}"
        self.documents[document_id] = text
        return {"success": True, "document_id": document_id}
    
    async def add_triplet(self, triplet):
        """Mock add triplet."""
        self.triplets.append(triplet)
        return {"success": True, "triplet_id": len(self.triplets)}
    
    async def search(self, query, limit=10, use_semantic=True, filters=None):
        """Mock search."""
        # Simple word matching for demonstration
        query_words = query.lower().split()
        results = []
        
        # Search in triplets
        for triplet in self.triplets:
            triplet_text = f"{triplet.subject} {triplet.predicate} {triplet.object}".lower()
            score = sum(1 for word in query_words if word in triplet_text) / len(query_words) if query_words else 0
            
            if score > 0:
                results.append({
                    "subject": triplet.subject,
                    "predicate": triplet.predicate,
                    "object": triplet.object,
                    "score": score,
                    "confidence": triplet.confidence,
                    "source": triplet.source,
                    "metadata": triplet.metadata
                })
        
        # Search in documents
        for doc_id, text in self.documents.items():
            text_lower = text.lower()
            score = sum(1 for word in query_words if word in text_lower) / len(query_words) if query_words else 0
            
            if score > 0:
                results.append({
                    "text": text,
                    "id": doc_id,
                    "score": score,
                    "type": "document"
                })
        
        # Sort by score and limit
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        if limit:
            results = results[:limit]
            
        return {"success": True, "results": results}
    
    async def get_entity_connections(self, entity_name):
        """Mock get entity connections."""
        triplets = []
        
        for triplet in self.triplets:
            if triplet.subject.lower() == entity_name.lower() or triplet.object.lower() == entity_name.lower():
                triplets.append({
                    "subject": triplet.subject,
                    "predicate": triplet.predicate,
                    "object": triplet.object,
                    "confidence": triplet.confidence,
                    "source": triplet.source,
                    "metadata": triplet.metadata
                })
                
        return {"success": True, "triplets": triplets}


# Monkey patch the GraphitiClient to use the mock
import symphony.memory.kg_memory
original_client = symphony.memory.kg_memory.GraphitiClient


class MockGraphitiAdapter(symphony.memory.kg_memory.GraphitiClient):
    """Adapter for the mock Graphiti client."""
    
    def __init__(self, config):
        """Initialize the mock client."""
        self.mock = MockGraphitiClient()
        super().__init__(config)
    
    async def ingest_text(self, text, document_id=None):
        """Forward to mock."""
        return await self.mock.ingest_text(text, document_id)
    
    async def add_triplet(self, triplet):
        """Forward to mock."""
        return await self.mock.add_triplet(triplet)
    
    async def search(self, query, limit=10, use_semantic=True, filters=None):
        """Forward to mock."""
        return await self.mock.search(query, limit, use_semantic, filters)
    
    async def get_entity_connections(self, entity_name):
        """Forward to mock."""
        return await self.mock.get_entity_connections(entity_name)


# Replace with mock for example
symphony.memory.kg_memory.GraphitiClient = MockGraphitiAdapter


async def main():
    """Run the example."""
    print("=== Knowledge Graph Memory Example ===\n")
    
    # Create a prompt registry
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a knowledgeable assistant with a knowledge graph memory. "
            "Use your knowledge to provide accurate and helpful information. "
            "When you learn new facts, you store them in your knowledge graph."
        ),
        agent_type="reactive"
    )
    
    # Create mock LLM for triplet extraction and agent responses
    llm_client = MockLLMClient(responses={
        # Triplet extraction
        "Extract factual knowledge triplets": """
{"subject": "Earth", "predicate": "is", "object": "a planet"}
{"subject": "Earth", "predicate": "orbits", "object": "the Sun"}
{"subject": "Sun", "predicate": "is", "object": "a star"}
{"subject": "Mercury", "predicate": "is", "object": "the innermost planet"}
        """,
        
        # Regular responses
        "Tell me about Earth": (
            "Earth is a planet in our solar system. It orbits the Sun and is the third planet from the Sun. "
            "It's the only known astronomical object to harbor life."
        ),
        "What do you know about the Sun?": (
            "The Sun is a star at the center of our solar system. It's a nearly perfect sphere of hot plasma that "
            "provides energy to Earth and other planets through solar radiation."
        ),
        "Tell me about the solar system": (
            "The solar system consists of the Sun and the objects that orbit it, including eight planets (Mercury, Venus, "
            "Earth, Mars, Jupiter, Saturn, Uranus, and Neptune), dwarf planets, moons, asteroids, comets, and other bodies."
        )
    })
    
    # Create a KG memory configuration
    config = GraphitiConfig(
        endpoint="http://localhost:8000",  # Not used with mock
        project_id="example"
    )
    
    # Create a KG memory
    kg_memory = KnowledgeGraphMemory(
        graphiti_config=config,
        llm_client=llm_client,
        auto_extract=True
    )
    
    # Add some initial knowledge
    print("Adding initial knowledge...")
    await kg_memory.add_triplet(Triplet(
        subject="Sun",
        predicate="has_diameter",
        object="1.4 million kilometers",
        confidence=1.0,
        source="initial_data"
    ))
    
    await kg_memory.add_triplet(Triplet(
        subject="Earth",
        predicate="has_diameter",
        object="12,742 kilometers",
        confidence=1.0,
        source="initial_data"
    ))
    
    await kg_memory.add_triplet(Triplet(
        subject="Earth",
        predicate="has_atmosphere",
        object="nitrogen and oxygen",
        confidence=1.0,
        source="initial_data"
    ))
    
    # Create agent configuration
    agent_config = AgentConfig(
        name="KnowledgeAgent",
        agent_type="reactive",
        description="An agent with knowledge graph capabilities"
    )
    
    # Create the KG-enhanced agent
    agent = KGEnhancedAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=registry,
        memory=kg_memory
    )
    
    # Scenario 1: Knowledge Graph Search
    print("\nScenario 1: Knowledge Graph Search")
    print("User: kg:search planet")
    response = await agent.run("kg:search planet")
    print(f"Agent:\n{response}\n")
    
    # Scenario 2: Adding Knowledge
    print("Scenario 2: Adding Knowledge")
    print("User: kg:add Mars|is|the fourth planet")
    response = await agent.run("kg:add Mars|is|the fourth planet")
    print(f"Agent: {response}")
    
    print("User: kg:add Mars|has_color|red")
    response = await agent.run("kg:add Mars|has_color|red")
    print(f"Agent: {response}\n")
    
    # Scenario 3: Query with Knowledge Enrichment
    print("Scenario 3: Query with Knowledge Enrichment")
    print("User: Tell me about Earth")
    response = await agent.run("Tell me about Earth")
    print(f"Agent: {response}\n")
    
    # Scenario 4: Knowledge Extraction from Conversation
    print("Scenario 4: Knowledge Extraction from Conversation")
    print("User: The Sun's surface temperature is about 5,500 degrees Celsius")
    response = await agent.run("The Sun's surface temperature is about 5,500 degrees Celsius")
    print(f"Agent: Thank you for that information. I've added it to my knowledge graph.\n")
    
    # Check the extracted knowledge
    print("User: kg:entity Sun")
    response = await agent.run("kg:entity Sun")
    print(f"Agent:\n{response}\n")
    
    # Scenario 5: Complex Entity Information
    print("Scenario 5: Complex Entity Information")
    print("User: Tell me everything you know about the solar system")
    response = await agent.run("Tell me everything you know about the solar system")
    print(f"Agent: {response}\n")
    
    # Final knowledge graph search
    print("Final Knowledge State:")
    print("User: kg:search planet")
    response = await agent.run("kg:search planet")
    print(f"Agent:\n{response}")


if __name__ == "__main__":
    asyncio.run(main())