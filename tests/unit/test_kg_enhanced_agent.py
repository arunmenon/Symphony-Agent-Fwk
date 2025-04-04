"""Unit tests for knowledge graph enhanced agent mixin."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, ANY

from symphony.agents.kg_enhanced import KnowledgeGraphEnhancedAgentMixin
from symphony.memory.kg_memory import (
    KnowledgeGraphMemory, Triplet, ConversationKnowledgeGraphMemory
)
from symphony.utils.types import Message


class TestKGEnhancedAgent:
    """Test suite for KG enhanced agent mixin."""
    
    @pytest.fixture
    def mock_kg_memory(self):
        """Create a mock KG memory."""
        memory = MagicMock(spec=KnowledgeGraphMemory)
        
        # Set up mock responses
        memory.add_triplet.return_value = True
        memory.search.return_value = [
            {"text": "Symphony is a framework", "score": 0.95},
            {"text": "Symphony supports agents", "score": 0.9}
        ]
        memory.extract_and_store.return_value = [
            Triplet(
                subject="Symphony",
                predicate="is",
                object="framework",
                confidence=0.95
            )
        ]
        memory.get_entity_connections.return_value = {
            "entity": {
                "name": "Symphony",
                "id": "entity1"
            },
            "relationships": [
                {
                    "subject": "Symphony",
                    "predicate": "is",
                    "object": "framework"
                }
            ]
        }
        
        return memory
    
    @pytest.fixture
    def kg_enhanced_agent(self, mock_kg_memory):
        """Create a KG enhanced agent for testing."""
        # Create a simple class that inherits from the mixin
        class TestAgent(KnowledgeGraphEnhancedAgentMixin):
            def __init__(self, memory):
                self.memory = memory
                self.id = "test_agent"
                super().__init__()
        
        return TestAgent(mock_kg_memory)
    
    def test_init_kg_memory(self, kg_enhanced_agent, mock_kg_memory):
        """Test initializing KG memory."""
        # Should have set kg_memory to the memory instance
        assert kg_enhanced_agent.kg_memory is mock_kg_memory
    
    def test_init_kg_memory_not_kg(self):
        """Test initializing with non-KG memory."""
        # Create memory that's not a KG memory
        memory = MagicMock()
        
        # Create agent
        class TestAgent(KnowledgeGraphEnhancedAgentMixin):
            def __init__(self, memory):
                self.memory = memory
                self.id = "test_agent"
                super().__init__()
        
        agent = TestAgent(memory)
        
        # Should have set kg_memory to None
        assert agent.kg_memory is None
    
    def test_init_no_memory(self):
        """Test initializing with no memory."""
        # Create agent without memory
        class TestAgent(KnowledgeGraphEnhancedAgentMixin):
            def __init__(self):
                self.id = "test_agent"
                super().__init__()
        
        agent = TestAgent()
        
        # Should have set kg_memory to None
        assert agent.kg_memory is None
    
    @pytest.mark.asyncio
    async def test_add_knowledge_triplet(self, kg_enhanced_agent, mock_kg_memory):
        """Test adding a knowledge triplet."""
        # Add a triplet
        result = await kg_enhanced_agent.add_knowledge_triplet(
            subject="Symphony",
            predicate="is",
            object="framework",
            confidence=0.95,
            source="test"
        )
        
        # Check result
        assert result is True
        
        # Check that add_triplet was called with correct parameters
        mock_kg_memory.add_triplet.assert_called_once_with(ANY)
        triplet = mock_kg_memory.add_triplet.call_args[0][0]
        assert triplet.subject == "Symphony"
        assert triplet.predicate == "is"
        assert triplet.object == "framework"
        assert triplet.confidence == 0.95
        assert triplet.source == "test"
    
    @pytest.mark.asyncio
    async def test_add_knowledge_triplet_no_memory(self):
        """Test adding a knowledge triplet with no memory."""
        # Create agent without KG memory
        class TestAgent(KnowledgeGraphEnhancedAgentMixin):
            def __init__(self):
                self.id = "test_agent"
                super().__init__()
        
        agent = TestAgent()
        
        # Try to add a triplet
        result = await agent.add_knowledge_triplet(
            subject="Symphony",
            predicate="is",
            object="framework"
        )
        
        # Should return False
        assert result is False
    
    @pytest.mark.asyncio
    async def test_search_knowledge(self, kg_enhanced_agent, mock_kg_memory):
        """Test searching knowledge."""
        # Search knowledge
        results = await kg_enhanced_agent.search_knowledge(
            query="Symphony",
            limit=5,
            semantic=True
        )
        
        # Check results
        assert len(results) == 2
        assert results[0]["text"] == "Symphony is a framework"
        assert results[1]["text"] == "Symphony supports agents"
        
        # Check that search was called with correct parameters
        mock_kg_memory.search.assert_called_once_with(
            query="Symphony",
            limit=5,
            semantic=True
        )
    
    @pytest.mark.asyncio
    async def test_search_knowledge_no_memory(self):
        """Test searching knowledge with no memory."""
        # Create agent without KG memory
        class TestAgent(KnowledgeGraphEnhancedAgentMixin):
            def __init__(self):
                self.id = "test_agent"
                super().__init__()
        
        agent = TestAgent()
        
        # Try to search knowledge
        results = await agent.search_knowledge(query="Symphony")
        
        # Should return empty list
        assert results == []
    
    @pytest.mark.asyncio
    async def test_extract_knowledge_from_text(self, kg_enhanced_agent, mock_kg_memory):
        """Test extracting knowledge from text."""
        # Extract knowledge
        triplets = await kg_enhanced_agent.extract_knowledge_from_text(
            text="Symphony is a framework."
        )
        
        # Check results
        assert len(triplets) == 1
        assert triplets[0].subject == "Symphony"
        assert triplets[0].predicate == "is"
        assert triplets[0].object == "framework"
        
        # Check that extract_and_store was called with correct parameters
        mock_kg_memory.extract_and_store.assert_called_once_with(
            text="Symphony is a framework.",
            source="test_agent"
        )
    
    @pytest.mark.asyncio
    async def test_extract_knowledge_no_memory(self):
        """Test extracting knowledge with no memory."""
        # Create agent without KG memory
        class TestAgent(KnowledgeGraphEnhancedAgentMixin):
            def __init__(self):
                self.id = "test_agent"
                super().__init__()
        
        agent = TestAgent()
        
        # Try to extract knowledge
        triplets = await agent.extract_knowledge_from_text(
            text="Symphony is a framework."
        )
        
        # Should return empty list
        assert triplets == []
    
    @pytest.mark.asyncio
    async def test_get_entity_knowledge(self, kg_enhanced_agent, mock_kg_memory):
        """Test getting entity knowledge."""
        # Get entity knowledge
        knowledge = await kg_enhanced_agent.get_entity_knowledge("Symphony")
        
        # Check results
        assert knowledge["entity"]["name"] == "Symphony"
        assert len(knowledge["relationships"]) == 1
        assert knowledge["relationships"][0]["subject"] == "Symphony"
        assert knowledge["relationships"][0]["predicate"] == "is"
        assert knowledge["relationships"][0]["object"] == "framework"
        
        # Check that get_entity_connections was called with correct parameters
        mock_kg_memory.get_entity_connections.assert_called_once_with("Symphony")
    
    @pytest.mark.asyncio
    async def test_get_entity_knowledge_no_memory(self):
        """Test getting entity knowledge with no memory."""
        # Create agent without KG memory
        class TestAgent(KnowledgeGraphEnhancedAgentMixin):
            def __init__(self):
                self.id = "test_agent"
                super().__init__()
        
        agent = TestAgent()
        
        # Try to get entity knowledge
        knowledge = await agent.get_entity_knowledge("Symphony")
        
        # Should return empty dict
        assert knowledge == {}
    
    @pytest.mark.asyncio
    async def test_query_relevant_knowledge(self, kg_enhanced_agent, mock_kg_memory):
        """Test querying relevant knowledge."""
        # Query relevant knowledge
        statements = await kg_enhanced_agent.query_relevant_knowledge(
            context="Tell me about Symphony",
            limit=5
        )
        
        # Check results
        assert len(statements) == 2
        assert statements[0] == "Symphony is a framework"
        assert statements[1] == "Symphony supports agents"
        
        # Check that search was called with correct parameters
        mock_kg_memory.search.assert_called_once_with(
            query="Tell me about Symphony",
            limit=5,
            semantic=True
        )
    
    @pytest.mark.asyncio
    async def test_query_relevant_knowledge_no_memory(self):
        """Test querying relevant knowledge with no memory."""
        # Create agent without KG memory
        class TestAgent(KnowledgeGraphEnhancedAgentMixin):
            def __init__(self):
                self.id = "test_agent"
                super().__init__()
        
        agent = TestAgent()
        
        # Try to query relevant knowledge
        statements = await agent.query_relevant_knowledge("Symphony")
        
        # Should return empty list
        assert statements == []
    
    @pytest.mark.asyncio
    async def test_enrich_message_with_knowledge(self, kg_enhanced_agent, mock_kg_memory):
        """Test enriching a message with knowledge."""
        # Create a message
        message = Message(role="user", content="Tell me about Symphony")
        
        # Enrich the message
        enriched = await kg_enhanced_agent.enrich_message_with_knowledge(message)
        
        # Check results
        assert enriched.role == "user"
        assert enriched.content == "Tell me about Symphony"
        assert "knowledge_context" in enriched.additional_kwargs
        assert len(enriched.additional_kwargs["knowledge_context"]) == 2
        assert enriched.additional_kwargs["knowledge_context"][0] == "Symphony is a framework"
        assert enriched.additional_kwargs["knowledge_context"][1] == "Symphony supports agents"
    
    @pytest.mark.asyncio
    async def test_enrich_message_no_memory(self):
        """Test enriching a message with no memory."""
        # Create agent without KG memory
        class TestAgent(KnowledgeGraphEnhancedAgentMixin):
            def __init__(self):
                self.id = "test_agent"
                super().__init__()
        
        agent = TestAgent()
        
        # Create a message
        message = Message(role="user", content="Tell me about Symphony")
        
        # Try to enrich the message
        enriched = await agent.enrich_message_with_knowledge(message)
        
        # Should return the original message
        assert enriched is message
    
    @pytest.mark.asyncio
    async def test_enrich_non_user_message(self, kg_enhanced_agent):
        """Test enriching a non-user message."""
        # Create a non-user message
        message = Message(role="assistant", content="Symphony is a framework")
        
        # Enrich the message
        enriched = await kg_enhanced_agent.enrich_message_with_knowledge(message)
        
        # Should return the original message
        assert enriched is message