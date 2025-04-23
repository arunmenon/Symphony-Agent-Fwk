"""File-based implementation of the KnowledgeGraph backend."""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, DefaultDict
from collections import defaultdict

from symphony.core.registry.backends.knowledge_graph.base import KnowledgeGraphBackend


class FileKnowledgeGraph(KnowledgeGraphBackend):
    """File-based implementation of knowledge graph.
    
    Stores entities and relationships as JSON files on disk. This implementation
    is suitable for development and small-scale applications where persistence is required.
    """
    
    class Provider:
        """Provider for creating FileKnowledgeGraph instances."""
        
        @staticmethod
        def create_backend(config: Dict[str, Any] = None) -> 'FileKnowledgeGraph':
            """Create a new FileKnowledgeGraph instance.
            
            Args:
                config: Configuration dictionary, must contain "path" key
                
            Returns:
                A new FileKnowledgeGraph instance
                
            Raises:
                ValueError: If path is not provided in config
            """
            if not config or "path" not in config:
                raise ValueError("FileKnowledgeGraph requires 'path' in configuration")
            
            return FileKnowledgeGraph(config["path"])
    
    def __init__(self, path: str):
        """Initialize file-based knowledge graph.
        
        Args:
            path: Path to directory for storing graph files
        """
        self.path = path
        self.entities_path = os.path.join(path, "entities")
        self.relations_path = os.path.join(path, "relations")
        
        # In-memory cache
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.outgoing: DefaultDict[str, Dict[str, Dict[str, Dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        self.incoming: DefaultDict[str, Dict[str, Dict[str, Dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        
        self.loaded = False
        self._lock = asyncio.Lock()
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the backend with configuration.
        
        Args:
            config: Configuration dictionary (path is already set in constructor)
        """
        # Create directories if they don't exist
        os.makedirs(self.entities_path, exist_ok=True)
        os.makedirs(self.relations_path, exist_ok=True)
    
    async def connect(self) -> None:
        """Connect to the storage backend.
        
        Loads all entities and relations from disk into memory for efficient query.
        """
        # Load data from disk if not already loaded
        if not self.loaded:
            await self._load_data()
            self.loaded = True
    
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        # Clear in-memory cache
        self.entities.clear()
        self.outgoing.clear()
        self.incoming.clear()
        self.loaded = False
    
    async def health_check(self) -> bool:
        """Check if the backend is healthy.
        
        Returns:
            True if directories exist and are writable
        """
        if not os.path.exists(self.entities_path) or not os.path.exists(self.relations_path):
            return False
        
        # Check if directories are writable
        try:
            test_file = os.path.join(self.entities_path, "healthcheck")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return True
        except (IOError, OSError):
            return False
    
    async def _load_data(self) -> None:
        """Load all entities and relations from disk."""
        async with self._lock:
            # Clear existing data
            self.entities.clear()
            self.outgoing.clear()
            self.incoming.clear()
            
            # Load entities
            if os.path.exists(self.entities_path):
                for filename in os.listdir(self.entities_path):
                    if not filename.endswith(".json"):
                        continue
                    
                    try:
                        entity_id = filename[:-5]  # Remove .json extension
                        file_path = os.path.join(self.entities_path, filename)
                        
                        with open(file_path, "r") as f:
                            entity = json.load(f)
                        
                        self.entities[entity_id] = entity
                    except Exception:
                        # Skip files that can't be loaded
                        continue
            
            # Load relations
            if os.path.exists(self.relations_path):
                for filename in os.listdir(self.relations_path):
                    if not filename.endswith(".json"):
                        continue
                    
                    try:
                        # Relation files are named: from_id--to_id--type.json
                        parts = filename[:-5].split("--")
                        if len(parts) != 3:
                            continue
                        
                        from_id, to_id, rel_type = parts
                        file_path = os.path.join(self.relations_path, filename)
                        
                        with open(file_path, "r") as f:
                            relation = json.load(f)
                        
                        # Store relation in memory
                        self.outgoing[from_id][to_id][rel_type] = relation.get("properties", {})
                        self.incoming[to_id][from_id][rel_type] = relation.get("properties", {})
                    except Exception:
                        # Skip files that can't be loaded
                        continue
    
    def _get_entity_path(self, entity_id: str) -> str:
        """Get file path for entity."""
        return os.path.join(self.entities_path, f"{entity_id}.json")
    
    def _get_relation_path(self, from_id: str, to_id: str, rel_type: str) -> str:
        """Get file path for relation."""
        filename = f"{from_id}--{to_id}--{rel_type}.json"
        return os.path.join(self.relations_path, filename)
    
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
        # Ensure data is loaded
        if not self.loaded:
            await self.connect()
        
        # Create entity object
        entity = {
            "id": entity_id,
            "type": entity_type,
            "properties": properties or {}
        }
        
        # Store in memory
        self.entities[entity_id] = entity
        
        # Save to disk
        file_path = self._get_entity_path(entity_id)
        async with self._lock:
            with open(file_path, "w") as f:
                json.dump(entity, f, indent=2)
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get an entity by ID.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            Dictionary containing the entity data, or None if not found
        """
        # Ensure data is loaded
        if not self.loaded:
            await self.connect()
        
        # Check memory cache first
        if entity_id in self.entities:
            return self.entities[entity_id]
        
        # Try to load from disk
        file_path = self._get_entity_path(entity_id)
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r") as f:
                entity = json.load(f)
            
            # Cache in memory
            self.entities[entity_id] = entity
            return entity
        except Exception:
            return None
    
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
        # Ensure data is loaded
        if not self.loaded:
            await self.connect()
        
        # Get existing entity
        entity = await self.get_entity(entity_id)
        if not entity:
            return False
        
        # Update properties
        entity["properties"].update(properties)
        
        # Save to disk
        file_path = self._get_entity_path(entity_id)
        async with self._lock:
            with open(file_path, "w") as f:
                json.dump(entity, f, indent=2)
        
        return True
    
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity from the graph.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            True if deleted, False if not found
        """
        # Ensure data is loaded
        if not self.loaded:
            await self.connect()
        
        # Check if entity exists
        if entity_id not in self.entities and not os.path.exists(self._get_entity_path(entity_id)):
            return False
        
        # Remove entity from memory
        if entity_id in self.entities:
            del self.entities[entity_id]
        
        # Remove entity file
        file_path = self._get_entity_path(entity_id)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Get all relations involving this entity
        relations_to_delete = []
        
        # Outgoing relations
        for to_id, rel_dict in self.outgoing.get(entity_id, {}).items():
            for rel_type in rel_dict:
                relations_to_delete.append((entity_id, to_id, rel_type))
        
        # Incoming relations
        for from_id, rel_dict in self.incoming.get(entity_id, {}).items():
            for rel_type in rel_dict:
                relations_to_delete.append((from_id, entity_id, rel_type))
        
        # Delete all relations
        for from_id, to_id, rel_type in relations_to_delete:
            await self.delete_relation(from_id, to_id, rel_type)
        
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
        # Ensure data is loaded
        if not self.loaded:
            await self.connect()
        
        # Check if entities exist
        if from_entity_id not in self.entities:
            raise ValueError(f"Source entity '{from_entity_id}' does not exist")
        
        if to_entity_id not in self.entities:
            raise ValueError(f"Target entity '{to_entity_id}' does not exist")
        
        # Create relation object
        relation_props = properties or {}
        relation = {
            "from_id": from_entity_id,
            "to_id": to_entity_id,
            "type": relation_type,
            "properties": relation_props
        }
        
        # Store in memory
        self.outgoing[from_entity_id][to_entity_id][relation_type] = relation_props
        self.incoming[to_entity_id][from_entity_id][relation_type] = relation_props
        
        # Save to disk
        file_path = self._get_relation_path(from_entity_id, to_entity_id, relation_type)
        async with self._lock:
            with open(file_path, "w") as f:
                json.dump(relation, f, indent=2)
    
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
        # Ensure data is loaded
        if not self.loaded:
            await self.connect()
        
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
        # Ensure data is loaded
        if not self.loaded:
            await self.connect()
        
        # Check if relation exists
        file_path = self._get_relation_path(from_entity_id, to_entity_id, relation_type)
        
        if (from_entity_id not in self.outgoing or
                to_entity_id not in self.outgoing[from_entity_id] or
                relation_type not in self.outgoing[from_entity_id][to_entity_id]) and not os.path.exists(file_path):
            return False
        
        # Remove relation from memory
        if (from_entity_id in self.outgoing and 
                to_entity_id in self.outgoing[from_entity_id] and
                relation_type in self.outgoing[from_entity_id][to_entity_id]):
            del self.outgoing[from_entity_id][to_entity_id][relation_type]
            
            # Clean up empty dictionaries
            if not self.outgoing[from_entity_id][to_entity_id]:
                del self.outgoing[from_entity_id][to_entity_id]
            
            if not self.outgoing[from_entity_id]:
                del self.outgoing[from_entity_id]
        
        if (to_entity_id in self.incoming and 
                from_entity_id in self.incoming[to_entity_id] and
                relation_type in self.incoming[to_entity_id][from_entity_id]):
            del self.incoming[to_entity_id][from_entity_id][relation_type]
            
            # Clean up empty dictionaries
            if not self.incoming[to_entity_id][from_entity_id]:
                del self.incoming[to_entity_id][from_entity_id]
            
            if not self.incoming[to_entity_id]:
                del self.incoming[to_entity_id]
        
        # Remove relation file
        if os.path.exists(file_path):
            os.remove(file_path)
        
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
        # Ensure data is loaded
        if not self.loaded:
            await self.connect()
        
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