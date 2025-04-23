"""Vector store base interface.

This module defines the abstract interface for vector stores used for
embedding storage and similarity search.
"""

from abc import abstractmethod
from typing import List, Dict, Any, Optional, TypeVar, Generic

from symphony.core.registry.backends.base import StorageBackend

T = TypeVar('T')

class VectorStoreBackend(StorageBackend, Generic[T]):
    """Abstract base class for vector store backends.
    
    Vector stores provide storage for embedding vectors and support
    similarity search operations.
    """
    
    @abstractmethod
    async def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a vector to the store.
        
        Args:
            id: Unique identifier for the vector
            vector: The embedding vector
            metadata: Optional metadata to store with the vector
        """
        pass
    
    @abstractmethod
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID.
        
        Args:
            id: Unique identifier for the vector
            
        Returns:
            Dictionary containing the vector and metadata, or None if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete a vector from the store.
        
        Args:
            id: Unique identifier for the vector
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def search(
        self, 
        query_vector: List[float], 
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors.
        
        Args:
            query_vector: The query embedding vector
            limit: Maximum number of results to return
            metadata_filter: Optional filter on metadata fields
            
        Returns:
            List of dictionaries containing vector data and similarity scores
        """
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Get the number of vectors in the store.
        
        Returns:
            Number of vectors
        """
        pass