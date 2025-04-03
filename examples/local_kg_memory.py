"""Example demonstrating Symphony's local knowledge graph memory capabilities."""

import asyncio
import datetime
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.agents.local_kg_enhanced import LocalKGEnhancedAgentMixin
from symphony.llm.base import MockLLMClient
from symphony.memory.local_kg_memory import (
    ConversationKnowledgeGraphMemory,
    KnowledgeTriplet,
    LocalKnowledgeGraphMemory,
    SimpleEmbeddingModel,
)
from symphony.prompts.registry import PromptRegistry
from symphony.utils.types import Message


class LocalKGEnhancedAgent(ReactiveAgent, LocalKGEnhancedAgentMixin):
    """A reactive agent with local knowledge graph capabilities."""
    
    async def run(self, input_message: str) -> str:
        """Run the agent with knowledge graph augmentation."""
        # Check if the message is a KG-specific command
        if input_message.startswith("kg:"):
            return await self.process_with_kg(input_message)
            
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
        if self.kg_memory:
            # Extract from user input
            await self.extract_knowledge_from_text(input_message)
            
            # Extract from agent response
            await self.extract_knowledge_from_text(result)
        
        # Restore original system prompt
        self.system_prompt = original_system_prompt
        
        return result


async def main():
    """Run the example."""
    print("=== Local Knowledge Graph Memory Example ===\n")
    
    # Create a temporary file for storage
    storage_path = Path("./temp_kg.pkl")
    
    # Create a prompt registry
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content=(
            "You are a knowledgeable assistant with a local knowledge graph memory. "
            "Use your knowledge to provide accurate and helpful information. "
            "When you learn new facts, you store them in your knowledge graph."
        ),
        agent_type="reactive"
    )
    
    # Create mock LLM for triplet extraction and agent responses
    llm_client = MockLLMClient(responses={
        # Triplet extraction
        "Extract factual knowledge triplets": """
{"subject": "Earth", "predicate": "is", "object": "a planet", "confidence": 0.95}
{"subject": "Earth", "predicate": "orbits", "object": "the Sun", "confidence": 0.98}
{"subject": "Sun", "predicate": "is", "object": "a star", "confidence": 0.99}
{"subject": "Mercury", "predicate": "is", "object": "the innermost planet", "confidence": 0.93}
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
    
    # Create embedding model
    embedding_model = SimpleEmbeddingModel(dimension=128)
    
    # Create a local KG memory
    kg_memory = LocalKnowledgeGraphMemory(
        llm_client=llm_client,
        embedding_model=embedding_model,
        storage_path=str(storage_path),
        auto_extract=True
    )
    
    # Add some initial knowledge
    print("Adding initial knowledge...")
    await kg_memory.add_triplet(
        subject="Sun",
        predicate="has_diameter",
        object="1.4 million kilometers",
        confidence=1.0,
        source="initial_data"
    )
    
    await kg_memory.add_triplet(
        subject="Earth",
        predicate="has_diameter",
        object="12,742 kilometers",
        confidence=1.0,
        source="initial_data"
    )
    
    await kg_memory.add_triplet(
        subject="Earth",
        predicate="has_atmosphere",
        object="nitrogen and oxygen",
        confidence=1.0,
        source="initial_data"
    )
    
    # Create agent configuration
    agent_config = AgentConfig(
        name="LocalKnowledgeAgent",
        agent_type="reactive",
        description="An agent with local knowledge graph capabilities"
    )
    
    # Create the KG-enhanced agent
    agent = LocalKGEnhancedAgent(
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
    
    # Scenario 4: Knowledge Extraction with Different Modes
    print("Scenario 4: Knowledge Extraction with Different Modes")
    
    # Standard extraction
    print("User: kg:extract The Sun's surface temperature is about 5,500 degrees Celsius")
    response = await agent.run("kg:extract The Sun's surface temperature is about 5,500 degrees Celsius")
    print(f"Agent:\n{response}\n")
    
    # Aggressive extraction
    print("User: kg:extract --mode=aggressive Jupiter is the largest planet in our solar system. It has a Great Red Spot and over 79 moons. The four largest moons are called the Galilean moons.")
    response = await agent.run("kg:extract --mode=aggressive Jupiter is the largest planet in our solar system. It has a Great Red Spot and over 79 moons. The four largest moons are called the Galilean moons.")
    print(f"Agent:\n{response}\n")
    
    # Entity-focused extraction
    print("User: kg:extract --mode=entity-focused Venus is the second planet from the Sun and is known as the morning and evening star. It has a thick atmosphere of carbon dioxide and sulfuric acid clouds.")
    response = await agent.run("kg:extract --mode=entity-focused Venus is the second planet from the Sun and is known as the morning and evening star. It has a thick atmosphere of carbon dioxide and sulfuric acid clouds.")
    print(f"Agent:\n{response}\n")
    
    # Check the extracted knowledge
    print("User: kg:entity Sun")
    response = await agent.run("kg:entity Sun")
    print(f"Agent:\n{response}\n")
    
    # Scenario 5: Entity Information
    print("Scenario 5: Entity Information")
    print("User: kg:entity Mars")
    response = await agent.run("kg:entity Mars")
    print(f"Agent:\n{response}\n")
    
    # Scenario 6: Knowledge Extraction Command
    print("Scenario 6: Knowledge Extraction Command")
    print("User: kg:extract Jupiter is the largest planet in our solar system and has a Great Red Spot")
    response = await agent.run("kg:extract Jupiter is the largest planet in our solar system and has a Great Red Spot")
    print(f"Agent:\n{response}\n")
    
    # Scenario 7: Advanced Knowledge Graph Features
    print("Scenario 7: Advanced Knowledge Graph Features")
    
    # Add some complex information about exoplanets for advanced search
    complex_text = """
    Exoplanets are planets outside our solar system. The first confirmed detection of an exoplanet was in 1992. 
    Hot Jupiters are a type of exoplanet that are gas giants like Jupiter but orbit very close to their star. 
    Super-Earths are exoplanets with a mass higher than Earth's but substantially lower than Neptune's. 
    The habitable zone, also known as the Goldilocks zone, is the region around a star where conditions might be suitable for life.
    Proxima Centauri b is an exoplanet orbiting within the habitable zone of the red dwarf star Proxima Centauri.
    TRAPPIST-1 is a planetary system with seven rocky planets, several of which may be in the habitable zone.
    """
    
    print("User: kg:deepextract" + complex_text)
    response = await agent.run("kg:deepextract" + complex_text)
    print(f"Agent:\n{response}\n")
    
    # Semantic search
    print("User: kg:semantic planets where life might exist")
    response = await agent.run("kg:semantic planets where life might exist")
    print(f"Agent:\n{response}\n")
    
    # Search with document inclusion
    print("User: kg:search exoplanet --docs --limit=3")
    response = await agent.run("kg:search exoplanet --docs --limit=3")
    print(f"Agent:\n{response}\n")
    
    # Scenario 8: Conversation KG Memory
    print("Scenario 8: Conversation Knowledge Graph Memory")
    
    # Create a conversation memory
    conv_memory = ConversationKnowledgeGraphMemory(
        llm_client=llm_client,
        embedding_model=embedding_model,
        auto_extract=True
    )
    
    # Create agent with conversation memory
    conv_agent_config = AgentConfig(
        name="ConversationKGAgent",
        agent_type="reactive",
        description="An agent with conversation knowledge graph capabilities"
    )
    
    conv_agent = LocalKGEnhancedAgent(
        config=conv_agent_config,
        llm_client=llm_client,
        prompt_registry=registry,
        memory=conv_memory
    )
    
    # Add some messages
    print("Adding conversation messages...")
    await conv_memory.add_message(Message(role="user", content="Saturn has beautiful rings made of ice and rock"))
    await conv_memory.add_message(Message(role="assistant", content="Yes, Saturn's rings are indeed made of ice and rock particles. They're one of the most distinctive features of our solar system."))
    await conv_memory.add_message(Message(role="user", content="Pluto was reclassified as a dwarf planet in 2006"))
    
    # Search conversation
    print("Searching conversation knowledge...")
    results = await conv_memory.search_conversation("ring", limit=2)
    
    print("Conversation search results for 'ring':")
    for result in results:
        message = result["message"]
        score = result["score"]
        print(f"- {message.role}: {message.content} (score: {score:.2f})")
        
    # Final knowledge graph search
    print("\nFinal Knowledge State:")
    print("User: kg:search planet")
    response = await agent.run("kg:search planet")
    print(f"Agent:\n{response}")
    
    # Scenario 9: Graph Export
    print("\nScenario 9: Graph Export")
    
    # Export to JSON
    json_path = Path("./temp_kg_export.json")
    print(f"Exporting knowledge graph to {json_path}...")
    kg_data = kg_memory.export_graph(format="json", filepath=str(json_path))
    
    # Show some stats about the export
    print(f"Exported {len(kg_data['entities'])} entities, {len(kg_data['relationships'])} relationships, and {len(kg_data['triplets'])} triplets")
    
    # Show an example of one entity and its relationships
    if kg_data['entities']:
        sample_entity = kg_data['entities'][0]
        print(f"\nSample Entity: {sample_entity['name']} (ID: {sample_entity['id']})")
        print(f"Type: {sample_entity['type'] or 'unknown'}")
        print("Properties:", ", ".join([f"{k}: {v}" for k, v in sample_entity['properties'].items()]))
    
    # Clean up
    if storage_path.exists():
        storage_path.unlink()
    if json_path.exists():
        json_path.unlink()
    

if __name__ == "__main__":
    asyncio.run(main())