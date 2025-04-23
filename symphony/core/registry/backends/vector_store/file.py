"""File-based implementation of the VectorStore backend."""

import os
import json
import numpy as np
import asyncio
from typing import List, Dict, Any, Optional

from symphony.core.registry.backends.vector_store.base import VectorStoreBackend


class FileVectorStore(VectorStoreBackend):
    """File-based implementation of vector store.
    
    Stores vectors as JSON files on disk. This implementation is suitable
    for development and small-scale applications where persistence is required.
    """
    
    class Provider:
        """Provider for creating FileVectorStore instances."""
        
        @staticmethod
        def create_backend(config: Dict[str, Any] = None) -> 'FileVectorStore':
            """Create a new FileVectorStore instance.
            
            Args:
                config: Configuration dictionary, must contain "path" key
                
            Returns:
                A new FileVectorStore instance
                
            Raises:
                ValueError: If path is not provided in config
            """
            if not config or "path" not in config:
                raise ValueError("FileVectorStore requires 'path' in configuration")
            
            return FileVectorStore(config["path"])
    
    def __init__(self, path: str):
        """Initialize file-based vector store.
        
        Args:
            path: Path to directory for storing vector files
        """
        self.path = path
        self.vectors_path = os.path.join(path, "vectors")
        self.vectors_loaded = False
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the backend with configuration.
        
        Args:
            config: Configuration dictionary (path is already set in constructor)
        """
        os.makedirs(self.vectors_path, exist_ok=True)
    
    async def connect(self) -> None:
        """Connect to the storage backend.
        
        Loads all vectors from disk into memory for efficient search.
        """
        # Load vectors and metadata from disk if not already loaded
        if not self.vectors_loaded:
            await self._load_vectors()
            self.vectors_loaded = True
    
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        # We don't need to do anything specific here
        self.vectors.clear()
        self.metadata.clear()
        self.vectors_loaded = False
    
    async def health_check(self) -> bool:
        """Check if the backend is healthy.
        
        Returns:
            True if vectors directory exists and is writable
        """
        if not os.path.exists(self.vectors_path):
            return False
        
        # Check if directory is writable
        try:
            test_file = os.path.join(self.vectors_path, "healthcheck")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return True
        except (IOError, OSError):
            return False
    
    async def _load_vectors(self) -> None:
        """Load all vectors from disk."""
        async with self._lock:
            # Clear existing data
            self.vectors.clear()
            self.metadata.clear()
            
            # List all files in vectors directory
            if not os.path.exists(self.vectors_path):
                return
            
            for filename in os.listdir(self.vectors_path):
                if not filename.endswith(".json"):
                    continue
                
                try:
                    vector_id = filename[:-5]  # Remove .json extension
                    file_path = os.path.join(self.vectors_path, filename)
                    
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    
                    self.vectors[vector_id] = np.array(data["vector"], dtype=np.float32)
                    self.metadata[vector_id] = data.get("metadata", {})
                except Exception:
                    # Skip files that can't be loaded
                    continue
    
    async def _save_vector(self, id: str) -> None:
        """Save a vector to disk.
        
        Args:
            id: ID of the vector to save
        """
        if id not in self.vectors:
            return
        
        file_path = os.path.join(self.vectors_path, f"{id}.json")
        
        async with self._lock:
            with open(file_path, "w") as f:
                json.dump({
                    "id": id,
                    "vector": self.vectors[id].tolist(),
                    "metadata": self.metadata.get(id, {})
                }, f)
    
    async def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a vector to the store.
        
        Args:
            id: Unique identifier for the vector
            vector: The embedding vector
            metadata: Optional metadata to store with the vector
        """
        # Store in memory
        self.vectors[id] = np.array(vector, dtype=np.float32)
        if metadata:
            self.metadata[id] = metadata
        else:
            self.metadata[id] = {}
        
        # Save to disk
        await self._save_vector(id)
    
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID.
        
        Args:
            id: Unique identifier for the vector
            
        Returns:
            Dictionary containing the vector and metadata, or None if not found
        """
        # Check if loaded in memory
        if id in self.vectors:
            return {
                "id": id,
                "vector": self.vectors[id].tolist(),
                "metadata": self.metadata.get(id, {})
            }
        
        # Try to load from disk
        file_path = os.path.join(self.vectors_path, f"{id}.json")
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            # Cache in memory
            self.vectors[id] = np.array(data["vector"], dtype=np.float32)
            self.metadata[id] = data.get("metadata", {})
            
            return data
        except Exception:
            return None
    
    async def delete(self, id: str) -> bool:
        """Delete a vector from the store.
        
        Args:
            id: Unique identifier for the vector
            
        Returns:
            True if deleted, False if not found
        """
        file_path = os.path.join(self.vectors_path, f"{id}.json")
        
        # Remove from memory
        found = id in self.vectors
        if found:
            del self.vectors[id]
            if id in self.metadata:
                del self.metadata[id]
        
        # Remove from disk
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        
        return found
    
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
        # Ensure vectors are loaded
        if not self.vectors_loaded:
            await self.connect()
        
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
        # Ensure vectors are loaded
        if not self.vectors_loaded:
            await self.connect()
        
        return len(self.vectors)