"""Symphony backend registry module.

This package provides interfaces and implementations for different
storage backends used by Symphony services.
"""

from symphony.core.registry.backends.base import (
    StorageBackend, 
    BackendType,
    StorageBackendFactory,
    BackendProvider
)

__all__ = [
    'StorageBackend',
    'BackendType',
    'StorageBackendFactory',
    'BackendProvider',
]