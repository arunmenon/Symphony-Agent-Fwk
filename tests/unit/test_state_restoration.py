"""Unit tests for Symphony state restoration."""

import os
import pytest
import shutil
import tempfile
import asyncio
from typing import Dict, List, Any, Optional

from symphony import Symphony
from symphony.core.state import (
    StateBundle,
    EntityReference,
    RestoreManager,
    RestorationContext,
    RestorationError
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir)


@pytest.fixture
async def symphony_with_state(temp_dir):
    """Create a Symphony instance with persistence and some state."""
    symphony = Symphony(persistence_enabled=True)
    await symphony.setup(state_dir=os.path.join(temp_dir, "state"))
    
    # Create some agents
    agent1 = await symphony.agents.create_agent({
        "name": "TestAgent1",
        "description": "First test agent",
        "agent_type": "reactive"
    })
    
    agent2 = await symphony.agents.create_agent({
        "name": "TestAgent2",
        "description": "Second test agent",
        "agent_type": "planning"
    })
    
    # Create memory
    memory = await symphony.agents.create_memory("conversation")
    agent1.memory = memory
    
    # Add data to memory
    if hasattr(memory, "items"):
        memory.items["test_key"] = "test_value"
    
    # Create checkpoint
    checkpoint_id = await symphony.create_checkpoint("test_state")
    
    return (symphony, checkpoint_id)


@pytest.mark.asyncio
async def test_restore_context():
    """Test RestorationContext."""
    # Create a Symphony instance
    symphony = Symphony()
    await symphony.setup()
    
    # Create restoration context
    context = RestorationContext(symphony)
    
    # Test entity registration
    test_entity = {"name": "Test Entity"}
    context.register_entity("TestType", "test_id", test_entity)
    
    # Test entity retrieval
    retrieved = context.get_entity("TestType", "test_id")
    assert retrieved is test_entity
    
    # Test pending reference
    ref = EntityReference("TestType", "ref_id")
    context.add_pending_reference(test_entity, "reference", ref)
    
    # Should be in pending references
    assert len(context.pending_references) == 1
    target, attr, ref_obj = context.pending_references[0]
    assert target is test_entity
    assert attr == "reference"
    assert ref_obj.entity_type == "TestType"
    assert ref_obj.entity_id == "ref_id"


@pytest.mark.asyncio
async def test_entity_reference():
    """Test EntityReference serialization/deserialization."""
    # Create an entity reference
    ref = EntityReference("Agent", "agent_123")
    
    # Convert to dict
    ref_dict = ref.to_dict()
    
    # Verify dict structure
    assert ref_dict["_type"] == "entity_reference"
    assert ref_dict["entity_type"] == "Agent"
    assert ref_dict["entity_id"] == "agent_123"
    
    # Deserialize
    restored = EntityReference.from_dict(ref_dict)
    
    # Verify restored reference
    assert restored.entity_type == "Agent"
    assert restored.entity_id == "agent_123"


@pytest.mark.asyncio
async def test_restoration_flow(temp_dir):
    """Test the full restoration flow."""
    # Part 1: Create a Symphony instance with state
    symphony1 = Symphony(persistence_enabled=True)
    await symphony1.setup(state_dir=os.path.join(temp_dir, "state"))
    
    # Create an agent
    agent1 = await symphony1.agents.create_agent({
        "name": "TestAgent",
        "description": "Test agent for restoration",
        "agent_type": "reactive"
    })
    
    # Create checkpoint
    checkpoint_id = await symphony1.create_checkpoint("test_checkpoint")
    
    # Part 2: Create a new Symphony instance and restore
    symphony2 = Symphony(persistence_enabled=True)
    await symphony2.setup(state_dir=os.path.join(temp_dir, "state"))
    
    # Restore from checkpoint
    await symphony2.resume_from_checkpoint(checkpoint_id)
    
    # Verify agent was restored
    agents = await symphony2.agents.get_all_agents()
    assert len(agents) > 0
    
    # Find the agent we created
    restored_agent = None
    for agent in agents:
        if agent.config.name == "TestAgent":
            restored_agent = agent
            break
    
    assert restored_agent is not None
    assert restored_agent.config.description == "Test agent for restoration"
    assert restored_agent.config.agent_type == "reactive"


@pytest.mark.asyncio
async def test_reference_resolution(temp_dir):
    """Test reference resolution during restoration."""
    # Create a Symphony instance with an agent and memory
    symphony1 = Symphony(persistence_enabled=True)
    await symphony1.setup(state_dir=os.path.join(temp_dir, "state"))
    
    # Create an agent
    agent = await symphony1.agents.create_agent({
        "name": "AgentWithMemory",
        "description": "Agent with memory reference",
        "agent_type": "reactive"
    })
    
    # Create memory and assign to agent
    memory = await symphony1.agents.create_memory("conversation")
    agent.memory = memory
    
    # Add data to memory
    if hasattr(memory, "items"):
        memory.items["reference_test"] = "test_value"
    
    # Create checkpoint
    checkpoint_id = await symphony1.create_checkpoint("reference_test")
    
    # Create a new Symphony instance and restore
    symphony2 = Symphony(persistence_enabled=True)
    await symphony2.setup(state_dir=os.path.join(temp_dir, "state"))
    
    # Restore from checkpoint
    await symphony2.resume_from_checkpoint(checkpoint_id)
    
    # Verify agent was restored
    agents = await symphony2.agents.get_all_agents()
    restored_agent = None
    for a in agents:
        if a.config.name == "AgentWithMemory":
            restored_agent = a
            break
    
    assert restored_agent is not None
    
    # Verify memory reference was restored
    assert hasattr(restored_agent, "memory")
    assert restored_agent.memory is not None
    
    # Verify memory data
    if hasattr(restored_agent.memory, "items"):
        assert "reference_test" in restored_agent.memory.items
        assert restored_agent.memory.items["reference_test"] == "test_value"