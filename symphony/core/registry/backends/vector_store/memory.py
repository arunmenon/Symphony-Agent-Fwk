"""In-memory implementation of the VectorStore backend."""

import numpy as np
from typing import List, Dict, Any, Optional

from symphony.core.registry.backends.vector_store.base import VectorStoreBackend


class InMemoryVectorStore(VectorStoreBackend):
    """In-memory implementation of vector store.
    
    Stores vectors in memory using numpy arrays for efficient similarity search.
    This implementation is suitable for testing and small-scale applications.
    """
    
    class Provider:
        """Provider for creating InMemoryVectorStore instances."""
        
        @staticmethod
        def create_backend(config: Dict[str, Any] = None) -> 'InMemoryVectorStore':
            """Create a new InMemoryVectorStore instance.
            
            Args:
                config: Optional configuration (ignored for memory store)
                
            Returns:
                A new InMemoryVectorStore instance
            """
            return InMemoryVectorStore()
    
    def __init__(self):
        """Initialize in-memory vector store."""
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the backend with configuration.
        
        Args:
            config: Configuration dictionary (ignored for memory store)
        """
        pass  # No initialization needed for in-memory store
    
    async def connect(self) -> None:
        """Connect to the storage backend."""
        pass  # No connection needed for in-memory store
    
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        self.vectors.clear()
        self.metadata.clear()
    
    async def health_check(self) -> bool:
        """Check if the backend is healthy.
        
        Returns:
            Always True for in-memory store
        """
        return True
    
    async def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a vector to the store.
        
        Args:
            id: Unique identifier for the vector
            vector: The embedding vector
            metadata: Optional metadata to store with the vector
        """
        self.vectors[id] = np.array(vector, dtype=np.float32)
        if metadata:
            self.metadata[id] = metadata
        else:
            self.metadata[id] = {}
    
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID.
        
        Args:
            id: Unique identifier for the vector
            
        Returns:
            Dictionary containing the vector and metadata, or None if not found
        """
        if id not in self.vectors:
            return None
        
        return {
            "id": id,
            "vector": self.vectors[id].tolist(),
            "metadata": self.metadata.get(id, {})
        }
    
    async def delete(self, id: str) -> bool:
        """Delete a vector from the store.
        
        Args:
            id: Unique identifier for the vector
            
        Returns:
            True if deleted, False if not found
        """
        if id not in self.vectors:
            return False
        
        del self.vectors[id]
        if id in self.metadata:
            del self.metadata[id]
        
        return True
    
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
        if not self.vectors:
            return []
        
        query_np = np.array(query_vector, dtype=np.float32)
        
        # Filter by metadata if provided
        ids_to_search = []
        if metadata_filter:
            for id, meta in self.metadata.items():
                match = True
                for key, value in metadata_filter.items():
                    if meta.get(key) != value:
                        match = False
                        break
                if match:
                    ids_to_search.append(id)
        else:
            ids_to_search = list(self.vectors.keys())
        
        if not ids_to_search:
            return []
        
        # Calculate cosine similarity
        results = []
        for id in ids_to_search:
            vector = self.vectors[id]
            # Normalize vectors for cosine similarity
            norm_query = query_np / np.linalg.norm(query_np)
            norm_vector = vector / np.linalg.norm(vector)
            # Calculate cosine similarity
            similarity = np.dot(norm_query, norm_vector)
            results.append({
                "id": id,
                "similarity": float(similarity),
                "vector": vector.tolist(),
                "metadata": self.metadata.get(id, {})
            })
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Limit results
        return results[:limit]
    
    async def count(self) -> int:
        """Get the number of vectors in the store.
        
        Returns:
            Number of vectors
        """
        return len(self.vectors)