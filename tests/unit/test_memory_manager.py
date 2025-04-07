"""Tests for memory manager functionality."""

import asyncio
import time
from unittest import mock

import pytest

from symphony.memory.memory_manager import (
    ConversationMemoryManager,
    MemoryManager,
    WorkingMemory
)
from symphony.memory.vector_memory import VectorMemory
from symphony.utils.types import Message


@pytest.fixture
def working_memory():
    """Create a working memory for testing."""
    return WorkingMemory(retention_period=1.0)  # Short period for testing


@pytest.fixture
def long_term_memory():
    """Create a long-term memory for testing."""
    return VectorMemory()


@pytest.fixture
def memory_manager(working_memory, long_term_memory):
    """Create a memory manager for testing."""
    return MemoryManager(
        working_memory=working_memory,
        long_term_memory=long_term_memory
    )


@pytest.fixture
def conversation_memory_manager(working_memory, long_term_memory):
    """Create a conversation memory manager for testing."""
    return ConversationMemoryManager(
        working_memory=working_memory,
        long_term_memory=long_term_memory
    )


class TestWorkingMemory:
    """Tests for the WorkingMemory class."""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, working_memory):
        """Test storing and retrieving items."""
        # Store an item
        await working_memory.store("test_key", "test_value")
        
        # Retrieve the item
        value = await working_memory.retrieve("test_key")
        assert value == "test_value"
        
    @pytest.mark.asyncio
    async def test_expiration(self, working_memory):
        """Test that items expire after the retention period."""
        # Store an item
        await working_memory.store("test_key", "test_value")
        
        # Wait for longer than the retention period
        await asyncio.sleep(1.1)
        
        # Item should be expired
        value = await working_memory.retrieve("test_key")
        assert value is None
        
    @pytest.mark.asyncio
    async def test_cleanup(self, working_memory):
        """Test cleanup of expired items."""
        # Store multiple items
        await working_memory.store("key1", "value1")
        await working_memory.store("key2", "value2")
        
        # Wait for longer than the retention period
        await asyncio.sleep(1.1)
        
        # Store a new item
        await working_memory.store("key3", "value3")
        
        # Run cleanup
        await working_memory.cleanup()
        
        # Check which items are still available
        assert await working_memory.retrieve("key1") is None
        assert await working_memory.retrieve("key2") is None
        assert await working_memory.retrieve("key3") == "value3"


class TestMemoryManager:
    """Tests for the MemoryManager class."""
    
    @pytest.mark.asyncio
    async def test_store_with_low_importance(self, memory_manager):
        """Test storing with low importance only uses working memory."""
        # Store with low importance
        await memory_manager.store("key1", "value1", importance=0.3)
        
        # Should be in working memory
        working_result = await memory_manager.memories["working"].retrieve("key1")
        assert working_result == "value1"
        
        # Should not be in long-term memory
        long_term_result = await memory_manager.memories["long_term"].retrieve("key1")
        assert long_term_result is None
        
    @pytest.mark.asyncio
    async def test_store_with_high_importance(self, memory_manager):
        """Test storing with high importance uses both memories."""
        # Store with high importance
        await memory_manager.store("key2", "value2", importance=0.8)
        
        # Should be in working memory
        working_result = await memory_manager.memories["working"].retrieve("key2")
        assert working_result == "value2"
        
        # Should be in long-term memory
        long_term_result = await memory_manager.memories["long_term"].retrieve("key2")
        assert long_term_result == "value2"
        
    @pytest.mark.asyncio
    async def test_retrieve_from_specific_memory(self, memory_manager):
        """Test retrieving from a specific memory type."""
        # Store in both memories
        await memory_manager.store("key3", "value3", importance=0.8)
        
        # Retrieve only from long-term memory
        result = await memory_manager.retrieve("key3", memory_types=["long_term"])
        assert result == "value3"
        
    @pytest.mark.asyncio
    async def test_retrieve_from_working_memory_first(self, memory_manager):
        """Test retrieving from working memory first."""
        # Store different values in each memory
        await memory_manager.memories["working"].store("key4", "working_value")
        await memory_manager.memories["long_term"].store("key4", "long_term_value")
        
        # Retrieve should get working memory value
        result = await memory_manager.retrieve("key4")
        assert result == "working_value"
        
    @pytest.mark.asyncio
    async def test_add_memory_system(self, memory_manager):
        """Test adding a new memory system."""
        # Create and add a new memory system
        new_memory = mock.AsyncMock()
        memory_manager.add_memory_system("new_memory", new_memory)
        
        # Store in the new memory system
        await memory_manager.store("key5", "value5", memory_types=["new_memory"])
        
        # Check that store was called on the new memory system
        new_memory.store.assert_called_once_with("key5", "value5")
        
    @pytest.mark.asyncio
    async def test_consolidate(self, memory_manager):
        """Test memory consolidation."""
        # Mock cleanup method
        memory_manager.memories["working"].cleanup = mock.AsyncMock()
        
        # Run consolidation
        await memory_manager.consolidate()
        
        # Verify cleanup was called
        memory_manager.memories["working"].cleanup.assert_called_once()


class TestConversationMemoryManager:
    """Tests for the ConversationMemoryManager class."""
    
    @pytest.mark.asyncio
    async def test_add_message(self, conversation_memory_manager):
        """Test adding a message to the conversation memory manager."""
        # Create a message
        message = Message(role="user", content="Hello, how are you?")
        
        # Add the message
        await conversation_memory_manager.add_message(message)
        
        # Check the message was added
        messages = conversation_memory_manager.get_messages()
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "Hello, how are you?"
        
    @pytest.mark.asyncio
    async def test_search_conversation(self, conversation_memory_manager):
        """Test searching the conversation history."""
        # Add several messages
        messages = [
            Message(role="user", content="What is machine learning?"),
            Message(role="assistant", content="Machine learning is a subset of AI that enables systems to learn from data."),
            Message(role="user", content="How does deep learning differ?"),
            Message(role="assistant", content="Deep learning uses neural networks with many layers to learn complex patterns."),
        ]
        
        for message in messages:
            await conversation_memory_manager.add_message(message)
        
        # Search for machine learning
        results = await conversation_memory_manager.search_conversation("machine learning")
        assert len(results) > 0
        assert "machine learning" in results[0].content.lower()
        
    @pytest.mark.asyncio
    async def test_importance_strategy(self, conversation_memory_manager):
        """Test the importance strategy."""
        # Test message with question
        question_message = Message(role="user", content="What is the deadline?")
        question_importance = await conversation_memory_manager.importance_strategy.calculate_importance(
            question_message.content, {"role": question_message.role}
        )
        assert question_importance > 0.5
        
        # Test message with action keyword
        action_message = Message(role="user", content="We must complete this by Friday.")
        action_importance = await conversation_memory_manager.importance_strategy.calculate_importance(
            action_message.content, {"role": action_message.role}
        )
        assert action_importance > 0.5
        
        # Test regular message
        regular_message = Message(role="assistant", content="Here's some information.")
        regular_importance = await conversation_memory_manager.importance_strategy.calculate_importance(
            regular_message.content, {"role": regular_message.role}
        )
        assert regular_importance >= 0.0