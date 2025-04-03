"""Base memory interface and implementations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar

from symphony.utils.types import ContextItem, Message

T = TypeVar("T")


class BaseMemory(ABC):
    """Abstract base class for all memory implementations."""
    
    @abstractmethod
    def store(self, key: str, value: Any) -> None:
        """Store a value in memory with the given key."""
        pass
    
    @abstractmethod
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value from memory by key."""
        pass
    
    @abstractmethod
    def search(self, query: str, limit: Optional[int] = None) -> List[Any]:
        """Search memory for items matching the query."""
        pass
    

class InMemoryMemory(BaseMemory):
    """Simple in-memory implementation of memory."""
    
    def __init__(self):
        self._storage: Dict[str, Any] = {}
    
    def store(self, key: str, value: Any) -> None:
        """Store a value in memory with the given key."""
        self._storage[key] = value
    
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value from memory by key."""
        return self._storage.get(key)
    
    def search(self, query: str, limit: Optional[int] = None) -> List[Any]:
        """Search memory for items matching the query.
        
        This implementation just does a basic string search in keys.
        A real implementation would use vector search or similar.
        """
        results = [
            value for key, value in self._storage.items() 
            if query.lower() in key.lower()
        ]
        
        if limit is not None:
            results = results[:limit]
            
        return results


class ConversationMemory(InMemoryMemory):
    """Memory for storing conversation history."""
    
    def __init__(self):
        super().__init__()
        self._messages: List[Message] = []
    
    def add_message(self, message: Message) -> None:
        """Add a message to the conversation history."""
        self._messages.append(message)
        
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get the conversation history, optionally limited to the last N messages."""
        if limit is not None:
            return self._messages[-limit:]
        return self._messages
    
    def clear(self) -> None:
        """Clear the conversation history."""
        self._messages = []
        
    def to_context_items(self) -> List[ContextItem]:
        """Convert conversation history to context items."""
        return [
            ContextItem(
                content=f"{msg.role}: {msg.content}",
                metadata={"role": msg.role}
            )
            for msg in self._messages
        ]