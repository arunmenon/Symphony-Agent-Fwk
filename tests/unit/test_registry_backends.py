"""Tests for Symphony registry backends."""

import os
import pytest
import tempfile
import asyncio
from typing import Dict, Any, List

from symphony.core.registry.backends.base import (
    StorageBackend, 
    BackendType,
    StorageBackendFactory
)

from symphony.core.registry.backends.vector_store import (
    InMemoryVectorStore, 
    FileVectorStore
)

from symphony.core.registry.backends.knowledge_graph import (
    InMemoryKnowledgeGraph,
    FileKnowledgeGraph
)

from symphony.core.registry.backends.checkpoint_store import (
    InMemoryCheckpointStore,
    FileCheckpointStore
)

from symphony.core.registry import ServiceRegistry


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file-based backends."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
async def registry():
    """Create a ServiceRegistry instance for testing."""
    registry = ServiceRegistry()
    yield registry
    await registry.shutdown()


@pytest.mark.asyncio
async def test_vector_store_memory_backend():
    """Test in-memory vector store backend."""
    # Create backend
    backend = await StorageBackendFactory.create_backend(
        BackendType.VECTOR_STORE, 
        "memory",
        "test_memory"
    )
    
    assert isinstance(backend, InMemoryVectorStore)
    
    # Test operations
    await backend.add("test1", [0.1, 0.2, 0.3], {"name": "Test 1"})
    await backend.add("test2", [0.4, 0.5, 0.6], {"name": "Test 2"})
    
    # Get single vector
    vector = await backend.get("test1")
    assert vector is not None
    assert vector["id"] == "test1"
    assert len(vector["vector"]) == 3
    assert vector["metadata"]["name"] == "Test 1"
    
    # Search
    results = await backend.search([0.1, 0.2, 0.3], limit=1)
    assert len(results) == 1
    assert results[0]["id"] == "test1"
    
    # Search with filter
    results = await backend.search(
        [0.1, 0.2, 0.3], 
        metadata_filter={"name": "Test 2"}
    )
    assert len(results) == 1
    assert results[0]["id"] == "test2"
    
    # Count
    count = await backend.count()
    assert count == 2
    
    # Delete
    deleted = await backend.delete("test1")
    assert deleted
    
    # Verify deletion
    vector = await backend.get("test1")
    assert vector is None
    
    # Cleanup
    await backend.disconnect()


@pytest.mark.asyncio
async def test_vector_store_file_backend(temp_dir):
    """Test file-based vector store backend."""
    # Create backend
    config = {"path": os.path.join(temp_dir, "vector_store")}
    backend = await StorageBackendFactory.create_backend(
        BackendType.VECTOR_STORE, 
        "file",
        "test_file",
        config
    )
    
    assert isinstance(backend, FileVectorStore)
    
    # Test operations
    await backend.add("test1", [0.1, 0.2, 0.3], {"name": "Test 1"})
    await backend.add("test2", [0.4, 0.5, 0.6], {"name": "Test 2"})
    
    # Get single vector
    vector = await backend.get("test1")
    assert vector is not None
    assert vector["id"] == "test1"
    assert len(vector["vector"]) == 3
    assert vector["metadata"]["name"] == "Test 1"
    
    # Search
    results = await backend.search([0.1, 0.2, 0.3], limit=1)
    assert len(results) == 1
    assert results[0]["id"] == "test1"
    
    # Count
    count = await backend.count()
    assert count == 2
    
    # Delete
    deleted = await backend.delete("test1")
    assert deleted
    
    # Verify deletion
    vector = await backend.get("test1")
    assert vector is None
    
    # Cleanup
    await backend.disconnect()


@pytest.mark.asyncio
async def test_knowledge_graph_memory_backend():
    """Test in-memory knowledge graph backend."""
    # Create backend
    backend = await StorageBackendFactory.create_backend(
        BackendType.KNOWLEDGE_GRAPH, 
        "memory",
        "test_memory"
    )
    
    assert isinstance(backend, InMemoryKnowledgeGraph)
    
    # Add entities
    await backend.add_entity("person1", "person", {"name": "Alice"})
    await backend.add_entity("person2", "person", {"name": "Bob"})
    await backend.add_entity("document1", "document", {"title": "Report"})
    
    # Add relations
    await backend.add_relation("person1", "document1", "AUTHORED", {"date": "2023-01-01"})
    await backend.add_relation("person2", "document1", "REVIEWED", {"date": "2023-01-02"})
    
    # Get entity
    entity = await backend.get_entity("person1")
    assert entity is not None
    assert entity["id"] == "person1"
    assert entity["type"] == "person"
    assert entity["properties"]["name"] == "Alice"
    
    # Get relations
    relations = await backend.get_relations("document1", direction="incoming")
    assert len(relations) == 2
    
    # Query
    results = await backend.query("person1", ["AUTHORED"])
    assert len(results) == 1
    assert results[0]["id"] == "document1"
    
    # Delete relation
    deleted = await backend.delete_relation("person1", "document1", "AUTHORED")
    assert deleted
    
    # Verify relation deletion
    relations = await backend.get_relations("document1", direction="incoming")
    assert len(relations) == 1
    
    # Delete entity
    deleted = await backend.delete_entity("person1")
    assert deleted
    
    # Verify entity deletion
    entity = await backend.get_entity("person1")
    assert entity is None
    
    # Cleanup
    await backend.disconnect()


@pytest.mark.asyncio
async def test_checkpoint_store_memory_backend():
    """Test in-memory checkpoint store backend."""
    # Create backend
    backend = await StorageBackendFactory.create_backend(
        BackendType.CHECKPOINT_STORE, 
        "memory",
        "test_memory"
    )
    
    assert isinstance(backend, InMemoryCheckpointStore)
    
    # Save checkpoints
    await backend.save_checkpoint(
        "cp1", 
        {"state": "initial"},
        {"name": "Initial State"}
    )
    
    await asyncio.sleep(0.1)  # Ensure different timestamps
    
    await backend.save_checkpoint(
        "cp2", 
        {"state": "updated"},
        {"name": "Updated State"}
    )
    
    # Get checkpoint
    checkpoint = await backend.get_checkpoint("cp1")
    assert checkpoint is not None
    assert checkpoint["checkpoint_id"] == "cp1"
    assert checkpoint["data"]["state"] == "initial"
    assert checkpoint["metadata"]["name"] == "Initial State"
    
    # List checkpoints
    checkpoints = await backend.list_checkpoints()
    assert len(checkpoints) == 2
    
    # Get latest checkpoint
    latest = await backend.get_latest_checkpoint()
    assert latest is not None
    assert latest["checkpoint_id"] == "cp2"
    
    # Delete checkpoint
    deleted = await backend.delete_checkpoint("cp1")
    assert deleted
    
    # Verify deletion
    checkpoint = await backend.get_checkpoint("cp1")
    assert checkpoint is None
    
    # Cleanup
    await backend.disconnect()


@pytest.mark.asyncio
async def test_registry_backend_integration(registry):
    """Test integration of backends with registry."""
    # Register backends
    vector_store = await registry.register_backend(
        BackendType.VECTOR_STORE,
        "memory",
        "default"
    )
    
    knowledge_graph = await registry.register_backend(
        BackendType.KNOWLEDGE_GRAPH,
        "memory",
        "default"
    )
    
    checkpoint_store = await registry.register_backend(
        BackendType.CHECKPOINT_STORE,
        "memory",
        "default"
    )
    
    # Test basic operations on each backend
    await vector_store.add("test1", [0.1, 0.2, 0.3], {"name": "Test Vector"})
    vector = await vector_store.get("test1")
    assert vector is not None
    
    await knowledge_graph.add_entity("entity1", "test", {"name": "Test Entity"})
    entity = await knowledge_graph.get_entity("entity1")
    assert entity is not None
    
    await checkpoint_store.save_checkpoint(
        "cp1", 
        {"state": "test"},
        {"name": "Test Checkpoint"}
    )
    checkpoint = await checkpoint_store.get_checkpoint("cp1")
    assert checkpoint is not None
    
    # Get backends from registry
    vs = registry.get_backend(BackendType.VECTOR_STORE)
    kg = registry.get_backend(BackendType.KNOWLEDGE_GRAPH)
    cs = registry.get_backend(BackendType.CHECKPOINT_STORE)
    
    assert vs is vector_store
    assert kg is knowledge_graph
    assert cs is checkpoint_store
    
    # List backends
    vector_stores = registry.list_backends(BackendType.VECTOR_STORE)
    assert "default" in vector_stores