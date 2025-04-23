"""Symphony service registry module.

This package provides a registry for Symphony services and components,
including pluggable backends for different storage mechanisms.
"""

from symphony.core.registry.base import ServiceRegistry
from symphony.core.registry.backends.base import (
    StorageBackend,
    BackendType,
    StorageBackendFactory,
    BackendProvider
)

# Re-export all symbols from base
__all__ = [
    'ServiceRegistry',
    'StorageBackend',
    'BackendType',
    'StorageBackendFactory',
    'BackendProvider',
]