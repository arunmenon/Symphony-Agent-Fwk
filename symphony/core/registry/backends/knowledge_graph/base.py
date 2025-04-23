"""Knowledge graph base interface.

This module defines the abstract interface for knowledge graph backends
used for storing structured relationships between entities.
"""

from abc import abstractmethod
from typing import List, Dict, Any, Optional

from symphony.core.registry.backends.base import StorageBackend


class KnowledgeGraphBackend(StorageBackend):
    """Abstract base class for knowledge graph backends.
    
    Knowledge graphs provide storage for entities and their relationships,
    supporting graph-based queries and traversals.
    """
    
    @abstractmethod
    async def add_entity(
        self, 
        entity_id: str, 
        entity_type: str, 
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an entity to the graph.
        
        Args:
            entity_id: Unique identifier for the entity
            entity_type: Type of the entity
            properties: Optional properties to store with the entity
        """
        pass
    
    @abstractmethod
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get an entity by ID.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            Dictionary containing the entity data, or None if not found
        """
        pass
    
    @abstractmethod
    async def update_entity(
        self, 
        entity_id: str, 
        properties: Dict[str, Any]
    ) -> bool:
        """Update an entity's properties.
        
        Args:
            entity_id: Unique identifier for the entity
            properties: New properties to set (merges with existing)
            
        Returns:
            True if updated, False if entity not found
        """
        pass
    
    @abstractmethod
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity from the graph.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def add_relation(
        self, 
        from_entity_id: str, 
        to_entity_id: str, 
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a relation between entities.
        
        Args:
            from_entity_id: ID of the source entity
            to_entity_id: ID of the target entity
            relation_type: Type of relation
            properties: Optional properties for the relation
            
        Raises:
            ValueError: If either entity does not exist
        """
        pass
    
    @abstractmethod
    async def get_relations(
        self, 
        entity_id: str, 
        relation_type: Optional[str] = None,
        direction: str = "outgoing"
    ) -> List[Dict[str, Any]]:
        """Get relations for an entity.
        
        Args:
            entity_id: ID of the entity
            relation_type: Optional filter by relation type
            direction: "outgoing", "incoming", or "both"
            
        Returns:
            List of relation dictionaries
        """
        pass
    
    @abstractmethod
    async def delete_relation(
        self, 
        from_entity_id: str, 
        to_entity_id: str, 
        relation_type: str
    ) -> bool:
        """Delete a relation between entities.
        
        Args:
            from_entity_id: ID of the source entity
            to_entity_id: ID of the target entity
            relation_type: Type of relation
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def query(
        self, 
        start_entity_id: str,
        relation_path: List[str],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query for entities connected through a path of relations.
        
        Args:
            start_entity_id: ID of the starting entity
            relation_path: List of relation types to traverse
            limit: Maximum number of results
            
        Returns:
            List of entity dictionaries matching the query
        """
        pass