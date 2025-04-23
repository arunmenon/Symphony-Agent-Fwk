"""Vector store backends for Symphony.

This module defines interfaces and implementations for vector store backends
used for embedding storage and similarity search.
"""

from symphony.core.registry.backends.vector_store.base import VectorStoreBackend
from symphony.core.registry.backends.vector_store.memory import InMemoryVectorStore
from symphony.core.registry.backends.vector_store.file import FileVectorStore

# Register built-in providers
from symphony.core.registry.backends.base import BackendType, StorageBackendFactory

# Register default providers
StorageBackendFactory.register_provider(
    BackendType.VECTOR_STORE, 
    "memory", 
    InMemoryVectorStore.Provider
)

StorageBackendFactory.register_provider(
    BackendType.VECTOR_STORE, 
    "file", 
    FileVectorStore.Provider
)

__all__ = [
    'VectorStoreBackend',
    'InMemoryVectorStore',
    'FileVectorStore',
]