"""Base interfaces for storage backends.

This module defines the abstract interfaces for all storage backends 
used by the Symphony registry system.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, Any, Generic, Type, TypeVar, Optional, List, Protocol

T = TypeVar('T')

class BackendType(Enum):
    """Types of storage backends supported by Symphony."""
    VECTOR_STORE = auto()
    KNOWLEDGE_GRAPH = auto()
    CHECKPOINT_STORE = auto()


class StorageBackend(ABC, Generic[T]):
    """Abstract base class for all storage backends.
    
    Storage backends provide persistent storage for different types of
    Symphony data. Each backend type has specific operations, but all
    share a common lifecycle (initialize, connect, disconnect).
    """
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the backend with configuration.
        
        Args:
            config: Backend-specific configuration
        """
        pass
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is healthy and ready for use.
        
        Returns:
            True if healthy, False otherwise
        """
        pass


class BackendProvider(Protocol):
    """Protocol for backend provider factories.
    
    A provider must implement a create_backend method that returns
    an instance of a StorageBackend.
    """
    
    @staticmethod
    def create_backend(config: Dict[str, Any] = None) -> StorageBackend:
        """Create a new backend instance.
        
        Args:
            config: Optional configuration for the backend
            
        Returns:
            A configured StorageBackend instance
        """
        ...


class StorageBackendFactory:
    """Factory for creating and retrieving storage backends.
    
    This factory manages the creation of storage backends for different
    types of data storage. It supports registration of custom backend
    providers and maintains a registry of created backends.
    """
    
    _providers: Dict[BackendType, Dict[str, Type[BackendProvider]]] = {
        BackendType.VECTOR_STORE: {},
        BackendType.KNOWLEDGE_GRAPH: {},
        BackendType.CHECKPOINT_STORE: {},
    }
    
    _backends: Dict[BackendType, Dict[str, StorageBackend]] = {
        BackendType.VECTOR_STORE: {},
        BackendType.KNOWLEDGE_GRAPH: {},
        BackendType.CHECKPOINT_STORE: {},
    }
    
    @classmethod
    def register_provider(
        cls, 
        backend_type: BackendType, 
        name: str, 
        provider: Type[BackendProvider]
    ) -> None:
        """Register a backend provider.
        
        Args:
            backend_type: Type of backend (vector store, knowledge graph, etc.)
            name: Name of the provider (e.g., "memory", "redis", "postgres")
            provider: Provider class that implements BackendProvider
        """
        if backend_type not in cls._providers:
            raise ValueError(f"Unknown backend type: {backend_type}")
        
        cls._providers[backend_type][name] = provider
    
    @classmethod
    def list_providers(cls, backend_type: BackendType) -> List[str]:
        """List all registered providers for a backend type.
        
        Args:
            backend_type: Type of backend
            
        Returns:
            List of provider names
        """
        if backend_type not in cls._providers:
            raise ValueError(f"Unknown backend type: {backend_type}")
        
        return list(cls._providers[backend_type].keys())
    
    @classmethod
    async def create_backend(
        cls, 
        backend_type: BackendType, 
        provider_name: str,
        backend_name: str = "default",
        config: Optional[Dict[str, Any]] = None
    ) -> StorageBackend:
        """Create a new backend instance.
        
        Args:
            backend_type: Type of backend (vector store, knowledge graph, etc.)
            provider_name: Name of the provider to use
            backend_name: Name for this backend instance (default: "default")
            config: Optional configuration for the backend
            
        Returns:
            A configured StorageBackend instance
            
        Raises:
            ValueError: If the provider is not registered
        """
        if backend_type not in cls._providers:
            raise ValueError(f"Unknown backend type: {backend_type}")
        
        if provider_name not in cls._providers[backend_type]:
            raise ValueError(
                f"Provider '{provider_name}' not registered for {backend_type.name}"
            )
        
        # Check if backend already exists
        if (backend_name in cls._backends[backend_type]):
            return cls._backends[backend_type][backend_name]
        
        # Create new backend
        provider = cls._providers[backend_type][provider_name]
        backend = provider.create_backend(config or {})
        
        # Initialize and connect
        await backend.initialize(config or {})
        await backend.connect()
        
        # Store in registry
        cls._backends[backend_type][backend_name] = backend
        return backend
    
    @classmethod
    def get_backend(
        cls, 
        backend_type: BackendType, 
        backend_name: str = "default"
    ) -> Optional[StorageBackend]:
        """Get an existing backend instance.
        
        Args:
            backend_type: Type of backend
            backend_name: Name of the backend instance
            
        Returns:
            The backend instance, or None if not found
        """
        if backend_type not in cls._backends:
            return None
        
        return cls._backends[backend_type].get(backend_name)
    
    @classmethod
    async def shutdown_all(cls) -> None:
        """Shut down all backends properly.
        
        This method should be called during application shutdown to
        properly disconnect from all backends.
        """
        for backend_type in cls._backends:
            for backend in cls._backends[backend_type].values():
                await backend.disconnect()