"""Knowledge graph backends for Symphony.

This module defines interfaces and implementations for knowledge graph backends
used for storing structured relationships between entities.
"""

from symphony.core.registry.backends.knowledge_graph.base import KnowledgeGraphBackend
from symphony.core.registry.backends.knowledge_graph.memory import InMemoryKnowledgeGraph
from symphony.core.registry.backends.knowledge_graph.file import FileKnowledgeGraph

# Register built-in providers
from symphony.core.registry.backends.base import BackendType, StorageBackendFactory

# Register default providers
StorageBackendFactory.register_provider(
    BackendType.KNOWLEDGE_GRAPH, 
    "memory", 
    InMemoryKnowledgeGraph.Provider
)

StorageBackendFactory.register_provider(
    BackendType.KNOWLEDGE_GRAPH, 
    "file", 
    FileKnowledgeGraph.Provider
)

__all__ = [
    'KnowledgeGraphBackend',
    'InMemoryKnowledgeGraph',
    'FileKnowledgeGraph',
]