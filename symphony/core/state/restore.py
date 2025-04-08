"""State restoration utilities for Symphony.

This module provides capabilities for restoring Symphony entities from
serialized state, handling the complexities of instantiating entities
and resolving references between them.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Type, Tuple, Callable, Union

from .serialization import StateBundle, EntityReference


logger = logging.getLogger(__name__)


class RestorationError(Exception):
    """Exception raised during state restoration."""
    pass


class RestorationContext:
    """Context for state restoration process.
    
    Tracks entities being restored and provides access to Symphony
    components needed during restoration.
    """
    
    def __init__(self, symphony_instance):
        """Initialize restoration context.
        
        Args:
            symphony_instance: Symphony instance to restore into
        """
        self.symphony = symphony_instance
        self.registry = symphony_instance.registry
        
        # Track entities by type and ID
        self.entities: Dict[str, Dict[str, Any]] = {}
        
        # Track references to resolve
        self.pending_references: List[Tuple[Any, str, EntityReference]] = []
    
    def register_entity(self, entity_type: str, entity_id: str, entity: Any) -> None:
        """Register a restored entity.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            entity: Restored entity instance
        """
        if entity_type not in self.entities:
            self.entities[entity_type] = {}
        
        self.entities[entity_type][entity_id] = entity
    
    def get_entity(self, entity_type: str, entity_id: str) -> Optional[Any]:
        """Get a restored entity by type and ID.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            
        Returns:
            Entity if found, None otherwise
        """
        return self.entities.get(entity_type, {}).get(entity_id)
    
    def add_pending_reference(self, target: Any, attribute: str, reference: EntityReference) -> None:
        """Add a reference to be resolved.
        
        Args:
            target: Object containing the reference
            attribute: Attribute name to set
            reference: Reference to resolve
        """
        self.pending_references.append((target, attribute, reference))
    
    async def resolve_references(self) -> None:
        """Resolve all pending references."""
        for target, attribute, reference in self.pending_references:
            entity = self.get_entity(reference.entity_type, reference.entity_id)
            if entity:
                setattr(target, attribute, entity)
            else:
                logger.warning(
                    f"Could not resolve reference: {reference.entity_type}:{reference.entity_id} "
                    f"for {target.__class__.__name__}.{attribute}"
                )


class EntityRestorer:
    """Base class for entity restorers.
    
    Entity restorers are responsible for restoring a specific type of entity
    from serialized state.
    """
    
    @property
    def entity_type(self) -> str:
        """Get entity type this restorer handles."""
        raise NotImplementedError("Subclasses must implement entity_type")
    
    async def can_restore(self, data: Dict[str, Any]) -> bool:
        """Check if this restorer can restore the given data.
        
        Args:
            data: Entity data
            
        Returns:
            True if this restorer can restore the data
        """
        return True
    
    async def restore(self, entity_id: str, data: Dict[str, Any], context: RestorationContext) -> Any:
        """Restore an entity from serialized state.
        
        Args:
            entity_id: Entity ID
            data: Entity data
            context: Restoration context
            
        Returns:
            Restored entity
        """
        raise NotImplementedError("Subclasses must implement restore")


class AgentRestorer(EntityRestorer):
    """Restorer for Agent entities."""
    
    @property
    def entity_type(self) -> str:
        return "Agent"
    
    async def restore(self, entity_id: str, data: Dict[str, Any], context: RestorationContext) -> Any:
        """Restore an agent from serialized state."""
        try:
            # Get agent config from data
            agent_config = data.get("config", {})
            agent_type = data.get("type", "ReactiveAgent")
            
            # Use the agent facade to create the agent
            if hasattr(context.symphony, "agents"):
                # Create the agent
                agent = await context.symphony.agents.create_agent(agent_config)
                
                # Restore interaction history if available
                if "interaction_history" in data and hasattr(agent, "_interaction_history"):
                    agent._interaction_history = data["interaction_history"]
                
                # Register agent with Symphony
                context.register_entity("Agent", entity_id, agent)
                
                # Handle memory reference
                if "memory" in data and isinstance(data["memory"], dict) and data["memory"].get("_type") == "entity_reference":
                    memory_ref = EntityReference.from_dict(data["memory"])
                    context.add_pending_reference(agent, "memory", memory_ref)
                
                # Handle tools references
                if "tools" in data and isinstance(data["tools"], list):
                    tool_refs = []
                    for tool_data in data["tools"]:
                        if isinstance(tool_data, dict) and tool_data.get("_type") == "entity_reference":
                            tool_ref = EntityReference.from_dict(tool_data)
                            tool_refs.append(tool_ref)
                    
                    # We'll handle tools differently since it's a list
                    # For now, we'll just log that tools need to be restored
                    if tool_refs:
                        logger.info(f"Agent {entity_id} has {len(tool_refs)} tools to restore")
                
                return agent
            else:
                raise RestorationError(f"Symphony instance does not have agents facade")
                
        except Exception as e:
            raise RestorationError(f"Failed to restore Agent {entity_id}: {e}")


class MemoryRestorer(EntityRestorer):
    """Restorer for Memory entities."""
    
    @property
    def entity_type(self) -> str:
        return "Memory"
    
    async def restore(self, entity_id: str, data: Dict[str, Any], context: RestorationContext) -> Any:
        """Restore a memory from serialized state."""
        try:
            # Get memory type from data
            memory_type = data.get("type", "ConversationMemory")
            
            # Create memory based on type
            if hasattr(context.symphony, "agents") and hasattr(context.symphony.agents, "create_memory"):
                memory = await context.symphony.agents.create_memory(memory_type)
                
                # Restore items if available
                if "items" in data and isinstance(data["items"], list):
                    if hasattr(memory, "items"):
                        for item in data["items"]:
                            key = item.get("key")
                            value = item.get("value")
                            if key is not None and value is not None:
                                memory.items[key] = value
                
                # Register memory
                context.register_entity("Memory", entity_id, memory)
                
                # Handle references to other memories
                if "long_term_memory" in data and isinstance(data["long_term_memory"], dict) and data["long_term_memory"].get("_type") == "entity_reference":
                    lt_ref = EntityReference.from_dict(data["long_term_memory"])
                    context.add_pending_reference(memory, "long_term_memory", lt_ref)
                
                return memory
            else:
                raise RestorationError(f"Symphony instance does not support memory creation")
                
        except Exception as e:
            raise RestorationError(f"Failed to restore Memory {entity_id}: {e}")


class WorkflowRestorer(EntityRestorer):
    """Restorer for Workflow entities."""
    
    @property
    def entity_type(self) -> str:
        return "Workflow"
    
    async def restore(self, entity_id: str, data: Dict[str, Any], context: RestorationContext) -> Any:
        """Restore a workflow from serialized state."""
        try:
            # For now, we'll just create a placeholder for workflows
            # since restoring a workflow fully requires more complex logic
            logger.info(f"Creating placeholder for workflow {entity_id}")
            
            # The real implementation would use the workflow tracker and
            # recreate the workflow structure from the serialized data
            
            # For example:
            # workflow_tracker = context.registry.get("workflow_tracker")
            # workflow = await workflow_tracker.create_workflow(
            #     name=data.get("name", "Restored Workflow"),
            #     description=data.get("description", ""),
            #     metadata=data.get("metadata", {})
            # )
            
            return None
                
        except Exception as e:
            raise RestorationError(f"Failed to restore Workflow {entity_id}: {e}")


class TaskRestorer(EntityRestorer):
    """Restorer for Task entities."""
    
    @property
    def entity_type(self) -> str:
        return "Task"
    
    async def restore(self, entity_id: str, data: Dict[str, Any], context: RestorationContext) -> Any:
        """Restore a task from serialized state."""
        try:
            # For now, we'll just create a placeholder for tasks
            # since restoring a task fully requires more complex logic
            logger.info(f"Creating placeholder for task {entity_id}")
            
            # The real implementation would use the task manager and
            # recreate the task from the serialized data
            
            return None
                
        except Exception as e:
            raise RestorationError(f"Failed to restore Task {entity_id}: {e}")


class RestoreManager:
    """Manager for restoring Symphony state from checkpoints."""
    
    def __init__(self):
        """Initialize restore manager."""
        self.restorers: Dict[str, EntityRestorer] = {}
        
        # Register default restorers
        self.register_restorer(AgentRestorer())
        self.register_restorer(MemoryRestorer())
        self.register_restorer(WorkflowRestorer())
        self.register_restorer(TaskRestorer())
    
    def register_restorer(self, restorer: EntityRestorer) -> None:
        """Register an entity restorer.
        
        Args:
            restorer: Entity restorer to register
        """
        self.restorers[restorer.entity_type] = restorer
    
    async def restore_entity(
        self, 
        entity_type: str, 
        entity_id: str, 
        data: Dict[str, Any], 
        context: RestorationContext
    ) -> Optional[Any]:
        """Restore an entity from serialized state.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            data: Entity data
            context: Restoration context
            
        Returns:
            Restored entity if successful, None otherwise
        """
        # Get restorer for entity type
        restorer = self.restorers.get(entity_type)
        if not restorer:
            logger.warning(f"No restorer found for entity type: {entity_type}")
            return None
        
        # Check if restorer can handle this data
        if not await restorer.can_restore(data):
            logger.warning(f"Restorer for {entity_type} cannot restore entity {entity_id}")
            return None
        
        # Restore entity
        try:
            entity = await restorer.restore(entity_id, data, context)
            return entity
        except Exception as e:
            logger.error(f"Failed to restore {entity_type} {entity_id}: {e}")
            return None
    
    async def restore_from_checkpoint(
        self,
        checkpoint_data: Dict[str, Any],
        symphony_instance: Any
    ) -> RestorationContext:
        """Restore Symphony state from a checkpoint.
        
        Args:
            checkpoint_data: Checkpoint data
            symphony_instance: Symphony instance to restore into
            
        Returns:
            Restoration context with restored entities
            
        Raises:
            RestorationError: If restoration fails
        """
        # Create restoration context
        context = RestorationContext(symphony_instance)
        
        try:
            # Extract entities from checkpoint
            entities = checkpoint_data.get("entities", [])
            
            # Phase 1: Create all entities
            logger.info(f"Restoring {len(entities)} entities")
            for entity_data in entities:
                entity_type = entity_data.get("entity_type")
                entity_id = entity_data.get("entity_id")
                bundle_key = entity_data.get("bundle_key")
                
                if not entity_type or not entity_id or not bundle_key:
                    logger.warning(f"Incomplete entity data: {entity_data}")
                    continue
                
                # Get entity state bundle
                bundle_data = await symphony_instance._state_storage.retrieve(bundle_key)
                if not bundle_data:
                    logger.warning(f"Entity state not found: {bundle_key}")
                    continue
                
                # Deserialize bundle
                try:
                    bundle = StateBundle.deserialize(bundle_data)
                    
                    # Restore entity
                    await self.restore_entity(entity_type, entity_id, bundle.data, context)
                    
                except Exception as e:
                    logger.error(f"Failed to deserialize state bundle {bundle_key}: {e}")
            
            # Phase 2: Resolve references between entities
            logger.info(f"Resolving {len(context.pending_references)} references")
            await context.resolve_references()
            
            return context
            
        except Exception as e:
            raise RestorationError(f"Failed to restore from checkpoint: {e}")
    

# Create singleton instance
restore_manager = RestoreManager()

# Public API function to register custom restorers
def register_entity_restorer(restorer: EntityRestorer) -> None:
    """Register a custom entity restorer.
    
    Use this function to register restorers for custom entity types.
    
    Args:
        restorer: Entity restorer to register
    """
    restore_manager.register_restorer(restorer)