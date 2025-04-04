"""In-memory implementation of the Repository interface."""

from typing import Dict, List, Optional, Any, Type
from pydantic import BaseModel

from symphony.persistence.repository import Repository, T

class InMemoryRepository(Repository[T]):
    """In-memory implementation of repository.
    
    Stores entities in a dictionary in memory. Data is lost when the application
    restarts. This is useful for testing and simple applications.
    """
    
    def __init__(self, model_class: Type[T]):
        """Initialize repository with model class.
        
        Args:
            model_class: The Pydantic model class for entities in this repository
        """
        self.model_class = model_class
        self.storage: Dict[str, Dict[str, Any]] = {}
    
    async def save(self, entity: T) -> str:
        """Save entity and return its ID.
        
        Args:
            entity: The entity to save
            
        Returns:
            The ID of the saved entity
            
        Raises:
            ValueError: If the entity does not have an ID
        """
        entity_dict = entity.model_dump()
        entity_id = entity_dict.get("id")
        if not entity_id:
            raise ValueError("Entity must have an id field")
        
        self.storage[entity_id] = entity_dict
        return entity_id
    
    async def find_by_id(self, id: str) -> Optional[T]:
        """Find entity by ID.
        
        Args:
            id: The ID of the entity to find
            
        Returns:
            The entity if found, None otherwise
        """
        entity_dict = self.storage.get(id)
        if not entity_dict:
            return None
        
        return self.model_class.model_validate(entity_dict)
    
    async def find_all(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[T]:
        """Find all entities matching filter criteria.
        
        Args:
            filter_criteria: Dictionary of field-value pairs to match
            
        Returns:
            List of matching entities
        """
        result = []
        
        for entity_dict in self.storage.values():
            # Apply filters if provided
            if filter_criteria:
                matches = True
                for key, value in filter_criteria.items():
                    if entity_dict.get(key) != value:
                        matches = False
                        break
                        
                if not matches:
                    continue
                    
            result.append(self.model_class.model_validate(entity_dict))
            
        return result
    
    async def update(self, entity: T) -> bool:
        """Update an entity.
        
        Args:
            entity: The entity to update
            
        Returns:
            True if the entity was updated, False otherwise
        """
        entity_dict = entity.model_dump()
        entity_id = entity_dict.get("id")
        
        if not entity_id or entity_id not in self.storage:
            return False
            
        self.storage[entity_id] = entity_dict
        return True
    
    async def delete(self, id: str) -> bool:
        """Delete an entity by ID.
        
        Args:
            id: The ID of the entity to delete
            
        Returns:
            True if the entity was deleted, False otherwise
        """
        if id not in self.storage:
            return False
            
        del self.storage[id]
        return True