"""Unit tests for Symphony state management."""

import os
import pytest
import shutil
import tempfile
import asyncio
from typing import Dict, List, Any, Optional

from symphony import Symphony
from symphony.core.state import (
    StateBundle, 
    FileStorageProvider, 
    CheckpointManager
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir)


@pytest.fixture
async def storage_provider(temp_dir):
    """Create a storage provider for testing."""
    provider = FileStorageProvider(os.path.join(temp_dir, "state"))
    yield provider


@pytest.fixture
async def checkpoint_manager(storage_provider):
    """Create a checkpoint manager for testing."""
    manager = CheckpointManager(storage_provider)
    yield manager


@pytest.fixture
async def symphony_instance(temp_dir):
    """Create a Symphony instance with persistence enabled."""
    symphony = Symphony(persistence_enabled=True)
    await symphony.setup(state_dir=os.path.join(temp_dir, "state"))
    yield symphony


@pytest.mark.asyncio
async def test_state_bundle_serialization():
    """Test StateBundle serialization and deserialization."""
    # Create a state bundle
    bundle = StateBundle(
        entity_type="Agent",
        entity_id="test_agent_1",
        state_version="1.0",
        data={"name": "Test Agent", "history": ["message1", "message2"]},
        metadata={"created_by": "test"}
    )
    
    # Serialize the bundle
    serialized = bundle.serialize()
    
    # Deserialize the bundle
    deserialized = StateBundle.deserialize(serialized)
    
    # Verify deserialized bundle matches original
    assert deserialized.entity_type == bundle.entity_type
    assert deserialized.entity_id == bundle.entity_id
    assert deserialized.state_version == bundle.state_version
    assert deserialized.data == bundle.data
    assert deserialized.metadata == bundle.metadata


@pytest.mark.asyncio
async def test_file_storage_provider(storage_provider):
    """Test FileStorageProvider basic operations."""
    # Create test data
    test_data = b'{"test": "data"}'
    test_key = "test/data.json"
    
    # Store data
    await storage_provider.store(test_key, test_data)
    
    # Retrieve data
    retrieved = await storage_provider.retrieve(test_key)
    assert retrieved == test_data
    
    # List keys
    keys = await storage_provider.list_keys("test")
    assert test_key in keys
    
    # Delete data
    result = await storage_provider.delete(test_key)
    assert result is True
    
    # Verify deleted
    retrieved = await storage_provider.retrieve(test_key)
    assert retrieved is None


@pytest.mark.asyncio
async def test_checkpoint_creation(symphony_instance):
    """Test checkpoint creation and retrieval."""
    # Create a test agent
    agent_config = {"name": "TestAgent", "description": "Test agent", "agent_type": "reactive"}
    agent = await symphony_instance.agents.create_agent(agent_config)
    
    # Create a checkpoint
    checkpoint_id = await symphony_instance.create_checkpoint("test_checkpoint")
    assert checkpoint_id is not None
    
    # List checkpoints
    checkpoints = await symphony_instance.list_checkpoints()
    assert len(checkpoints) == 1
    assert checkpoints[0]["id"] == checkpoint_id
    assert checkpoints[0]["name"] == "test_checkpoint"
    
    # Delete checkpoint
    result = await symphony_instance.delete_checkpoint(checkpoint_id)
    assert result is True
    
    # Verify deleted
    checkpoints = await symphony_instance.list_checkpoints()
    assert len(checkpoints) == 0


@pytest.mark.asyncio
async def test_transaction_atomicity(storage_provider):
    """Test transaction atomicity."""
    # Create a transaction
    transaction = await storage_provider.create_transaction()
    
    # Store multiple items
    await transaction.store("test/item1.json", b'{"item": 1}')
    await transaction.store("test/item2.json", b'{"item": 2}')
    
    # Commit transaction
    await transaction.commit()
    
    # Verify both items were stored
    item1 = await storage_provider.retrieve("test/item1.json")
    item2 = await storage_provider.retrieve("test/item2.json")
    assert item1 == b'{"item": 1}'
    assert item2 == b'{"item": 2}'
    
    # Create a transaction that will be rolled back
    transaction2 = await storage_provider.create_transaction()
    
    # Store an item
    await transaction2.store("test/item3.json", b'{"item": 3}')
    
    # Roll back transaction
    await transaction2.rollback()
    
    # Verify item was not stored
    item3 = await storage_provider.retrieve("test/item3.json")
    assert item3 is None