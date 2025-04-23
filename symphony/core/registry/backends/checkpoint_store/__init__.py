"""Checkpoint store backends for Symphony.

This module defines interfaces and implementations for checkpoint store backends
used for saving and restoring application state.
"""

from symphony.core.registry.backends.checkpoint_store.base import CheckpointStoreBackend
from symphony.core.registry.backends.checkpoint_store.memory import InMemoryCheckpointStore
from symphony.core.registry.backends.checkpoint_store.file import FileCheckpointStore

# Register built-in providers
from symphony.core.registry.backends.base import BackendType, StorageBackendFactory

# Register default providers
StorageBackendFactory.register_provider(
    BackendType.CHECKPOINT_STORE, 
    "memory", 
    InMemoryCheckpointStore.Provider
)

StorageBackendFactory.register_provider(
    BackendType.CHECKPOINT_STORE, 
    "file", 
    FileCheckpointStore.Provider
)

__all__ = [
    'CheckpointStoreBackend',
    'InMemoryCheckpointStore',
    'FileCheckpointStore',
]