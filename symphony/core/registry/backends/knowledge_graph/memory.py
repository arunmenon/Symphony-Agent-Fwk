"""In-memory implementation of the KnowledgeGraph backend."""

from typing import List, Dict, Any, Optional, DefaultDict
from collections import defaultdict

from symphony.core.registry.backends.knowledge_graph.base import KnowledgeGraphBackend


class InMemoryKnowledgeGraph(KnowledgeGraphBackend):
    """In-memory implementation of knowledge graph.
    
    Stores entities and relationships in memory. This implementation is
    suitable for testing and small-scale applications.
    """
    
    class Provider:
        """Provider for creating InMemoryKnowledgeGraph instances."""
        
        @staticmethod
        def create_backend(config: Dict[str, Any] = None) -> 'InMemoryKnowledgeGraph':
            """Create a new InMemoryKnowledgeGraph instance.
            
            Args:
                config: Optional configuration (ignored for memory graph)
                
            Returns:
                A new InMemoryKnowledgeGraph instance
            """
            return InMemoryKnowledgeGraph()
    
    def __init__(self):
        """Initialize in-memory knowledge graph."""
        # Entities: {entity_id: {type, properties}}
        self.entities: Dict[str, Dict[str, Any]] = {}
        
        # Outgoing relations: {from_id: {to_id: {relation_type: {props}}}}
        self.outgoing: DefaultDict[str, Dict[str, Dict[str, Dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        
        # Incoming relations: {to_id: {from_id: {relation_type: {props}}}}
        self.incoming: DefaultDict[str, Dict[str, Dict[str, Dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(dict)
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the backend with configuration.
        
        Args:
            config: Configuration dictionary (ignored for memory graph)
        """
        pass  # No initialization needed for in-memory store
    
    async def connect(self) -> None:
        """Connect to the storage backend."""
        pass  # No connection needed for in-memory store
    
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        self.entities.clear()
        self.outgoing.clear()
        self.incoming.clear()
    
    async def health_check(self) -> bool:
        """Check if the backend is healthy.
        
        Returns:
            Always True for in-memory store
        """
        return True
    
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
        self.entities[entity_id] = {
            "id": entity_id,
            "type": entity_type,
            "properties": properties or {}
        }
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get an entity by ID.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            Dictionary containing the entity data, or None if not found
        """
        return self.entities.get(entity_id)
    
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
        if entity_id not in self.entities:
            return False
        
        # Merge with existing properties
        self.entities[entity_id]["properties"].update(properties)
        return True
    
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity from the graph.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            True if deleted, False if not found
        """
        if entity_id not in self.entities:
            return False
        
        # Remove entity
        del self.entities[entity_id]
        
        # Remove all relations
        if entity_id in self.outgoing:
            del self.outgoing[entity_id]
        
        for from_id in list(self.outgoing.keys()):
            if entity_id in self.outgoing[from_id]:
                del self.outgoing[from_id][entity_id]
        
        if entity_id in self.incoming:
            del self.incoming[entity_id]
        
        for to_id in list(self.incoming.keys()):
            if entity_id in self.incoming[to_id]:
                del self.incoming[to_id][entity_id]
        
        return True
    
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
        if from_entity_id not in self.entities:
            raise ValueError(f"Source entity '{from_entity_id}' does not exist")
        
        if to_entity_id not in self.entities:
            raise ValueError(f"Target entity '{to_entity_id}' does not exist")
        
        # Store relation
        relation_props = properties or {}
        self.outgoing[from_entity_id][to_entity_id][relation_type] = relation_props
        self.incoming[to_entity_id][from_entity_id][relation_type] = relation_props
    
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
        if entity_id not in self.entities:
            return []
        
        relations = []
        
        # Get outgoing relations
        if direction in ["outgoing", "both"]:
            for to_id, rel_dict in self.outgoing.get(entity_id, {}).items():
                for rel_type, props in rel_dict.items():
                    if relation_type is None or rel_type == relation_type:
                        relations.append({
                            "from_id": entity_id,
                            "to_id": to_id,
                            "type": rel_type,
                            "properties": props
                        })
        
        # Get incoming relations
        if direction in ["incoming", "both"]:
            for from_id, rel_dict in self.incoming.get(entity_id, {}).items():
                for rel_type, props in rel_dict.items():
                    if relation_type is None or rel_type == relation_type:
                        relations.append({
                            "from_id": from_id,
                            "to_id": entity_id,
                            "type": rel_type,
                            "properties": props
                        })
        
        return relations
    
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
        # Check if relation exists
        if (from_entity_id not in self.outgoing or
                to_entity_id not in self.outgoing[from_entity_id] or
                relation_type not in self.outgoing[from_entity_id][to_entity_id]):
            return False
        
        # Remove relation
        del self.outgoing[from_entity_id][to_entity_id][relation_type]
        del self.incoming[to_entity_id][from_entity_id][relation_type]
        
        # Clean up empty dictionaries
        if not self.outgoing[from_entity_id][to_entity_id]:
            del self.outgoing[from_entity_id][to_entity_id]
        
        if not self.outgoing[from_entity_id]:
            del self.outgoing[from_entity_id]
        
        if not self.incoming[to_entity_id][from_entity_id]:
            del self.incoming[to_entity_id][from_entity_id]
        
        if not self.incoming[to_entity_id]:
            del self.incoming[to_entity_id]
        
        return True
    
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
        if not relation_path:
            # Return starting entity if it exists
            entity = await self.get_entity(start_entity_id)
            return [entity] if entity else []
        
        # Start with the initial entity
        current_entities = [start_entity_id]
        
        # Traverse the path
        for relation_type in relation_path:
            next_entities = []
            
            for entity_id in current_entities:
                # Get all outgoing relations of the specified type
                for to_id, rel_dict in self.outgoing.get(entity_id, {}).items():
                    if relation_type in rel_dict:
                        next_entities.append(to_id)
            
            # Update current entities for next iteration
            current_entities = next_entities
            
            # Stop early if no entities found
            if not current_entities:
                return []
        
        # Fetch entity details for result entities
        result = []
        for entity_id in current_entities[:limit]:
            entity = await self.get_entity(entity_id)
            if entity:
                result.append(entity)
        
        return result