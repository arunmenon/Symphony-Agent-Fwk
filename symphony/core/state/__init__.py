"""State management for Symphony.

This package provides persistence capabilities for Symphony entities,
allowing for checkpointing and resumption of complex workflows.
"""

from .serialization import StateBundle, create_state_bundle, EntityReference
from .storage import FileStorageProvider, StorageError
from .checkpoint import CheckpointManager, Checkpoint, CheckpointError
from .restore import RestoreManager, RestorationContext, RestorationError, EntityRestorer, register_entity_restorer

__all__ = [
    'StateBundle',
    'create_state_bundle',
    'EntityReference',
    'FileStorageProvider',
    'StorageError',
    'CheckpointManager',
    'Checkpoint',
    'CheckpointError',
    'RestoreManager',
    'RestorationContext',
    'RestorationError',
    'EntityRestorer',
    'register_entity_restorer',
]