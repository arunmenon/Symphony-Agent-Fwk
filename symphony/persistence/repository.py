"""Abstract repository pattern for Symphony persistence."""

from typing import TypeVar, Generic, Optional, List, Dict, Any
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class Repository(Generic[T]):
    """Abstract repository for entity persistence.
    
    This defines a common interface for storing and retrieving entities,
    abstracting away the details of the underlying storage mechanism.
    """
    
    async def save(self, entity: T) -> str:
        """Save entity and return its ID."""
        raise NotImplementedError("Repository.save must be implemented by subclasses")
    
    async def find_by_id(self, id: str) -> Optional[T]:
        """Find entity by ID."""
        raise NotImplementedError("Repository.find_by_id must be implemented by subclasses")
    
    async def find_all(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[T]:
        """Find all entities matching filter criteria."""
        raise NotImplementedError("Repository.find_all must be implemented by subclasses")
    
    async def update(self, entity: T) -> bool:
        """Update an entity."""
        raise NotImplementedError("Repository.update must be implemented by subclasses")
    
    async def delete(self, id: str) -> bool:
        """Delete an entity by ID."""
        raise NotImplementedError("Repository.delete must be implemented by subclasses")