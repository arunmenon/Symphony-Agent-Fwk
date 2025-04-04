"""File system implementation of the Repository interface."""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Type
from pydantic import BaseModel

from symphony.persistence.repository import Repository, T

class FileSystemRepository(Repository[T]):
    """File-based implementation of repository.
    
    Stores entities as JSON files on the file system. Data persists across
    application restarts. Each entity type is stored in its own subdirectory.
    """
    
    def __init__(self, model_class: Type[T], storage_path: str):
        """Initialize repository with model class and storage path.
        
        Args:
            model_class: The Pydantic model class for entities in this repository
            storage_path: The base directory for storing entity files
        """
        self.model_class = model_class
        self.storage_path = storage_path
        self.entity_type = model_class.__name__.lower()
        self.data_dir = os.path.join(storage_path, self.entity_type)
        
        # Create directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _get_file_path(self, entity_id: str) -> str:
        """Get file path for entity ID.
        
        Args:
            entity_id: The ID of the entity
            
        Returns:
            The file path for the entity
        """
        return os.path.join(self.data_dir, f"{entity_id}.json")
    
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
        
        file_path = self._get_file_path(entity_id)
        
        # Save to file asynchronously
        async with asyncio.Lock():
            with open(file_path, "w") as f:
                json.dump(entity_dict, f, indent=2)
        
        return entity_id
    
    async def find_by_id(self, id: str) -> Optional[T]:
        """Find entity by ID.
        
        Args:
            id: The ID of the entity to find
            
        Returns:
            The entity if found, None otherwise
        """
        file_path = self._get_file_path(id)
        
        if not os.path.exists(file_path):
            return None
        
        # Read from file asynchronously
        try:
            async with asyncio.Lock():
                with open(file_path, "r") as f:
                    entity_dict = json.load(f)
                
            return self.model_class.model_validate(entity_dict)
        except (json.JSONDecodeError, IOError):
            return None
    
    async def find_all(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[T]:
        """Find all entities matching filter criteria.
        
        Args:
            filter_criteria: Dictionary of field-value pairs to match
            
        Returns:
            List of matching entities
        """
        result = []
        
        # List all files in directory
        if not os.path.exists(self.data_dir):
            return []
            
        file_names = [f for f in os.listdir(self.data_dir) if f.endswith(".json")]
        
        for file_name in file_names:
            file_path = os.path.join(self.data_dir, file_name)
            
            try:
                async with asyncio.Lock():
                    with open(file_path, "r") as f:
                        entity_dict = json.load(f)
                
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
            except (json.JSONDecodeError, IOError):
                continue
        
        return result
    
    async def update(self, entity: T) -> bool:
        """Update an entity.
        
        Args:
            entity: The entity to update
            
        Returns:
            True if the entity was updated, False otherwise
        """
        # Check if entity exists first
        file_path = os.path.join(self.data_dir, f"{entity.id}.json")
        if not os.path.exists(file_path):
            return False
            
        # Entity exists, proceed with update
        await self.save(entity)
        return True
    
    async def delete(self, id: str) -> bool:
        """Delete an entity by ID.
        
        Args:
            id: The ID of the entity to delete
            
        Returns:
            True if the entity was deleted, False otherwise
        """
        file_path = self._get_file_path(id)
        
        if not os.path.exists(file_path):
            return False
        
        try:
            os.remove(file_path)
            return True
        except OSError:
            return False