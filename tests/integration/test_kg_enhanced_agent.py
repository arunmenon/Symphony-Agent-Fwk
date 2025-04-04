"""Integration tests for knowledge graph enhanced agents."""

import pytest
import asyncio
from typing import Dict, List, Optional, Any
from unittest.mock import MagicMock

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.agents.local_kg_enhanced import LocalKGEnhancedAgentMixin
from symphony.memory.local_kg_memory import (
    LocalKnowledgeGraphMemory, SimpleEmbeddingModel, KnowledgeTriplet
)
from symphony.utils.types import Message
from symphony.llm.base import MockLLMClient
from symphony.mcp.base import MCPManager, Context


class TestKGEnhancedAgent:
    """Test suite for knowledge graph enhanced agents."""
    
    @pytest.fixture
    def mock_mcp_manager(self):
        """Create a mock MCP manager for testing."""
        # Create a mock context
        mock_context = MagicMock(spec=Context)
        mock_context.state = {}
        
        # Create a mock MCPManager
        mock_manager = MagicMock(spec=MCPManager)
        
        # Setup methods to return sensible values
        mock_manager.get_context.return_value = mock_context
        mock_manager.prepare_agent_context.return_value = mock_context
        
        # Make update_context_state actually update the state
        def update_state(ctx, key, value):
            ctx.state[key] = value
        
        mock_manager.update_context_state.side_effect = update_state
        
        return mock_manager
    
    @pytest.fixture
    def kg_enhanced_agent(self, mock_llm_client, prompt_registry, kg_memory, mock_mcp_manager):
        """Create a KG enhanced agent for testing."""
        
        # Extend mock responses for KG operations
        additional_responses = {
            "Extract factual knowledge triplets": """
{"subject": "Earth", "predicate": "is", "object": "a planet", "confidence": 0.95}
{"subject": "Earth", "predicate": "orbits", "object": "Sun", "confidence": 0.98}
{"subject": "Mars", "predicate": "is", "object": "the fourth planet", "confidence": 0.97}
""",
            "Tell me about Earth": "Earth is the third planet from the Sun and the only known place in the universe where life exists.",
            "I want to search a knowledge graph": "Earth\nplanet\nSolar System\nthird planet\nlife\nwater\ncontinent"
        }
        
        # Create new mock client with combined responses
        responses = {**mock_llm_client.responses, **additional_responses}
        kg_llm = MockLLMClient(responses=responses)
        
        # Create a KG enhanced agent class
        class KGAgent(ReactiveAgent, LocalKGEnhancedAgentMixin):
            """A reactive agent with KG capabilities."""
            
            def __init__(self, **kwargs):
                """Initialize the agent."""
                super().__init__(**kwargs)
                # After ReactiveAgent is initialized, we need to set kg_memory to point to memory
                self.kg_memory = self.memory
            
            async def run(self, input_message: str) -> str:
                """Run with KG support."""
                # Check if this is a KG command
                if input_message.startswith("kg:"):
                    return await self.process_with_kg(input_message)
                    
                # Enrich with knowledge
                message = Message(role="user", content=input_message)
                enriched = await self.enrich_message_with_knowledge(message)
                
                # Process normally
                result = await super().run(enriched.content)
                
                # Extract knowledge
                await self.extract_knowledge_from_text(input_message)
                
                return result
                
            async def process_with_kg(self, input_message: str) -> str:
                """Process a KG command."""
                # Parse the command
                parts = input_message[3:].split(" ", 1)
                command = parts[0]
                args = parts[1] if len(parts) > 1 else ""
                
                # Process commands
                if command == "add":
                    # Format: kg:add subject|predicate|object
                    if "|" in args:
                        subject, predicate, object_text = args.split("|", 2)
                        triplet = await self.add_knowledge_triplet(
                            subject=subject,
                            predicate=predicate,
                            object=object_text
                        )
                        return f"Triplet added: {subject} {predicate} {object_text}"
                    else:
                        return "Invalid format. Use: kg:add subject|predicate|object"
                
                elif command == "extract":
                    # Format: kg:extract text to extract from
                    mode = "normal"
                    extraction_text = args
                    
                    # Check for mode flag
                    if args.startswith("--mode="):
                        mode_parts = args.split(" ", 1)
                        mode = mode_parts[0].split("=")[1]
                        extraction_text = mode_parts[1] if len(mode_parts) > 1 else ""
                    
                    triplets = await self.extract_knowledge_from_text(extraction_text)
                    return f"Extracted {len(triplets)} triplets in {mode} mode"
                
                elif command == "search":
                    # Format: kg:search query text
                    results = await self.search_knowledge(args)
                    return f"Search results for '{args}':\n" + "\n".join(
                        f"- {r.get('text', str(r))}" for r in results[:5]
                    )
                
                elif command == "semantic":
                    # Format: kg:semantic query text
                    results = await self.search_knowledge(args, semantic=True)
                    return f"Semantic search results for '{args}':\n" + "\n".join(
                        f"- {r.get('text', str(r))}" for r in results[:5]
                    )
                
                else:
                    return f"Unknown KG command: {command}"
        
        # Create agent instance
        config = AgentConfig(
            name="KGEnhancedAgent",
            agent_type="reactive",
            description="An agent with KG capabilities"
        )
        
        return KGAgent(
            config=config,
            llm_client=kg_llm,
            prompt_registry=prompt_registry,
            memory=kg_memory,
            mcp_manager=self.mock_mcp_manager
        )
    
    @pytest.mark.asyncio
    async def test_kg_agent_can_add_triplets(self, kg_enhanced_agent):
        """Test that the KG enhanced agent can add triplets."""
        # Add a triplet using the kg:add command
        response = await kg_enhanced_agent.run("kg:add Mercury|is|the innermost planet")
        
        assert "triplet added" in response.lower()
        
        # Verify that the triplet was added
        entity_info = await kg_enhanced_agent.get_entity_knowledge("Mercury")
        
        assert entity_info is not None
        assert entity_info.get("entity") is not None
        assert entity_info.get("entity").get("name") == "Mercury"
        
        # Check the relationship exists
        relationships = entity_info.get("relationships", [])
        found_relation = False
        
        for rel in relationships:
            if (rel.get("subject") == "Mercury" and 
                rel.get("predicate") == "is" and
                rel.get("object") == "the innermost planet"):
                found_relation = True
                break
        
        assert found_relation is True
    
    @pytest.mark.asyncio
    async def test_kg_agent_can_extract_knowledge(self, kg_enhanced_agent):
        """Test that the KG enhanced agent can extract knowledge."""
        # Extract knowledge from text
        response = await kg_enhanced_agent.run("kg:extract Earth is the third planet from the Sun and has one natural satellite called the Moon.")
        
        assert "extracted" in response.lower()
        
        # Verify that knowledge was extracted
        entity_info = await kg_enhanced_agent.get_entity_knowledge("Earth")
        
        assert entity_info is not None
        assert entity_info.get("entity") is not None
        
        # The exact triplets depend on the extraction, but we should have some relationships
        assert len(entity_info.get("relationships", [])) > 0
    
    @pytest.mark.asyncio
    async def test_kg_agent_can_search_knowledge(self, kg_enhanced_agent):
        """Test that the KG enhanced agent can search knowledge."""
        # Add some knowledge first
        await kg_enhanced_agent.add_knowledge_triplet(
            subject="Earth",
            predicate="is",
            object="a planet"
        )
        
        await kg_enhanced_agent.add_knowledge_triplet(
            subject="Mars",
            predicate="is",
            object="the red planet"
        )
        
        # Search for knowledge
        response = await kg_enhanced_agent.run("kg:search planet")
        
        assert "search results" in response.lower()
        assert "earth" in response.lower()
        assert "mars" in response.lower()
    
    @pytest.mark.asyncio
    async def test_kg_agent_can_enrich_messages(self, kg_enhanced_agent):
        """Test that the KG enhanced agent can enrich messages with knowledge."""
        # Add some knowledge first
        await kg_enhanced_agent.add_knowledge_triplet(
            subject="Earth",
            predicate="has",
            object="water"
        )
        
        await kg_enhanced_agent.add_knowledge_triplet(
            subject="Earth",
            predicate="has",
            object="atmosphere"
        )
        
        # Create a message
        message = Message(role="user", content="Tell me about Earth")
        
        # Enrich the message
        enriched = await kg_enhanced_agent.enrich_message_with_knowledge(message)
        
        # Check that knowledge was added
        assert "knowledge_context" in enriched.additional_kwargs
        knowledge_context = enriched.additional_kwargs["knowledge_context"]
        
        # Should have found the knowledge about Earth
        found_water = any("water" in item.lower() for item in knowledge_context)
        found_atmosphere = any("atmosphere" in item.lower() for item in knowledge_context)
        
        assert found_water or found_atmosphere
    
    @pytest.mark.asyncio
    async def test_kg_agent_semantic_search(self, kg_enhanced_agent):
        """Test that the KG enhanced agent can perform semantic search."""
        # Add some knowledge first
        await kg_enhanced_agent.add_knowledge_triplet(
            subject="Jupiter",
            predicate="is",
            object="the largest planet"
        )
        
        await kg_enhanced_agent.add_knowledge_triplet(
            subject="Jupiter",
            predicate="has",
            object="Great Red Spot"
        )
        
        # Perform semantic search
        response = await kg_enhanced_agent.run("kg:semantic big planets")
        
        assert "search results" in response.lower()
        assert "jupiter" in response.lower()
        
    @pytest.mark.asyncio
    async def test_kg_agent_knowledge_extraction_modes(self, kg_enhanced_agent):
        """Test that the KG enhanced agent can extract knowledge with different modes."""
        # Extract knowledge with aggressive mode
        response = await kg_enhanced_agent.run(
            "kg:extract --mode=aggressive The solar system contains eight planets, numerous dwarf planets, and countless smaller objects."
        )
        
        assert "extracted" in response.lower()
        assert "aggressive mode" in response.lower()
        
        # Check that some triplets were extracted
        search_results = await kg_enhanced_agent.search_knowledge("solar system")
        assert len(search_results) > 0