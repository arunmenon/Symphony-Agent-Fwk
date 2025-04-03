"""Vector-based memory implementation for semantic search."""

import json
import os
import pickle
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field

from symphony.memory.base import BaseMemory
from symphony.utils.types import Message


class MemoryEntry(BaseModel):
    """An entry in vector memory."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: float = Field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at
        }


class SimpleEmbedder:
    """Simple embedding implementation using a bag-of-words approach.
    
    This is a placeholder for demonstration. In a real implementation,
    you would use a proper embedding model like sentence-transformers,
    OpenAI embeddings, etc.
    """
    
    def __init__(self, dimension: int = 50):
        """Initialize the embedder."""
        self.dimension = dimension
        self.word_vectors: Dict[str, List[float]] = {}
        
    def _get_word_vector(self, word: str) -> List[float]:
        """Get a vector for a word, creating a new one if needed."""
        if word not in self.word_vectors:
            # Create a deterministic but seemingly random vector based on the word
            seed = sum(ord(c) for c in word)
            np.random.seed(seed)
            self.word_vectors[word] = np.random.randn(self.dimension).tolist()
        
        return self.word_vectors[word]
    
    def embed(self, text: str) -> List[float]:
        """Create an embedding for a text string."""
        # Simple preprocessing - lowercase and remove punctuation
        text = text.lower()
        for char in '.,!?;:()[]{}"\'':
            text = text.replace(char, ' ')
            
        words = text.split()
        if not words:
            return [0.0] * self.dimension
            
        # Average word vectors
        vectors = [self._get_word_vector(word) for word in words]
        avg_vector = np.mean(vectors, axis=0)
        
        # Normalize to unit length
        norm = np.linalg.norm(avg_vector)
        if norm > 0:
            avg_vector = avg_vector / norm
            
        return avg_vector.tolist()


class VectorMemory(BaseMemory):
    """Memory implementation with vector embeddings for semantic search."""
    
    def __init__(
        self, 
        embedder = None,
        persist_path: Optional[str] = None,
        load_on_init: bool = True
    ):
        """Initialize the vector memory.
        
        Args:
            embedder: The embedding model to use (defaults to SimpleEmbedder)
            persist_path: Optional path to persist memory to disk
            load_on_init: Whether to load from persist_path on initialization
        """
        self.embedder = embedder or SimpleEmbedder()
        self.entries: Dict[str, MemoryEntry] = {}
        self.persist_path = persist_path
        
        # Load from disk if specified
        if persist_path and load_on_init and os.path.exists(persist_path):
            self.load()
    
    def store(self, key: str, value: Any) -> None:
        """Store a value in memory with the given key."""
        content = str(value)
        
        # Create embedding
        embedding = self.embedder.embed(content)
        
        # Create and store entry
        entry = MemoryEntry(
            id=key,
            content=content,
            embedding=embedding
        )
        self.entries[key] = entry
        
        # Persist if path is set
        if self.persist_path:
            self.save()
    
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value from memory by key."""
        entry = self.entries.get(key)
        return entry.content if entry else None
    
    def search(
        self, 
        query: str, 
        limit: Optional[int] = None,
        threshold: float = 0.0,
        include_metadata: bool = False
    ) -> List[Any]:
        """Search for items similar to the query.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            threshold: Minimum similarity score (0-1)
            include_metadata: Whether to include metadata in results
            
        Returns:
            List of content strings or (content, metadata) tuples if include_metadata=True
        """
        if not self.entries:
            return []
            
        # Create query embedding
        query_embedding = self.embedder.embed(query)
        
        # Calculate similarity with all entries
        similarities: List[Tuple[str, float]] = []
        for key, entry in self.entries.items():
            if entry.embedding:
                similarity = self._cosine_similarity(query_embedding, entry.embedding)
                if similarity >= threshold:
                    similarities.append((key, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Apply limit
        if limit:
            similarities = similarities[:limit]
            
        # Format results
        results = []
        for key, similarity in similarities:
            entry = self.entries[key]
            if include_metadata:
                results.append((entry.content, entry.metadata))
            else:
                results.append(entry.content)
                
        return results
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
            
        # Convert to numpy arrays
        a = np.array(vec1)
        b = np.array(vec2)
        
        # Calculate similarity
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)
    
    def save(self) -> None:
        """Save memory to disk."""
        if not self.persist_path:
            return
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            
            # Serialize entries
            with open(self.persist_path, "wb") as f:
                pickle.dump(self.entries, f)
        except Exception as e:
            print(f"Error saving vector memory: {e}")
    
    def load(self) -> None:
        """Load memory from disk."""
        if not self.persist_path or not os.path.exists(self.persist_path):
            return
            
        try:
            with open(self.persist_path, "rb") as f:
                self.entries = pickle.load(f)
        except Exception as e:
            print(f"Error loading vector memory: {e}")
    
    def clear(self) -> None:
        """Clear all entries."""
        self.entries = {}
        
        # Remove persisted file if it exists
        if self.persist_path and os.path.exists(self.persist_path):
            try:
                os.remove(self.persist_path)
            except Exception as e:
                print(f"Error removing persisted memory file: {e}")
                
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory."""
        return {
            "entry_count": len(self.entries),
            "total_characters": sum(len(entry.content) for entry in self.entries.values()),
            "oldest_entry": min(entry.created_at for entry in self.entries.values()) if self.entries else None,
            "newest_entry": max(entry.created_at for entry in self.entries.values()) if self.entries else None
        }


class ConversationVectorMemory(VectorMemory):
    """Vector memory specialized for storing conversation messages."""
    
    def __init__(
        self,
        embedder = None,
        persist_path: Optional[str] = None,
        load_on_init: bool = True
    ):
        """Initialize conversation vector memory."""
        super().__init__(embedder, persist_path, load_on_init)
        self._messages: List[Message] = []
    
    def add_message(self, message: Message) -> None:
        """Add a message to the conversation history."""
        self._messages.append(message)
        
        # Store in vector memory with a unique key
        key = f"message_{len(self._messages)}"
        value = message.content
        metadata = {
            "role": message.role,
            "index": len(self._messages) - 1,
            "timestamp": time.time(),
            **message.additional_kwargs
        }
        
        # Create and store entry manually to include metadata
        content = str(value)
        embedding = self.embedder.embed(content)
        
        # Create and store entry
        entry = MemoryEntry(
            id=key,
            content=content,
            metadata=metadata,
            embedding=embedding
        )
        self.entries[key] = entry
        
        # Persist if path is set
        if self.persist_path:
            self.save()
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get the conversation history."""
        if limit is not None:
            return self._messages[-limit:]
        return self._messages
    
    def search_messages(
        self, 
        query: str, 
        limit: Optional[int] = None
    ) -> List[Message]:
        """Search conversation history for messages similar to the query."""
        # Get content and metadata
        results = self.search(query, limit, include_metadata=True)
        
        # Convert to Messages
        messages = []
        for content, metadata in results:
            role = metadata.get("role", "unknown")
            # Remove known metadata fields, keep any additional_kwargs
            additional_kwargs = {k: v for k, v in metadata.items() 
                               if k not in ("role", "index", "timestamp")}
            
            messages.append(Message(
                role=role,
                content=content,
                additional_kwargs=additional_kwargs
            ))
            
        return messages
    
    def clear(self) -> None:
        """Clear conversation history."""
        super().clear()
        self._messages = []