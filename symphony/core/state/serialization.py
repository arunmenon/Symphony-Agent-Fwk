"""State serialization utilities for Symphony.

This module provides internal utilities for serializing and deserializing
Symphony entities such as agents, memories, and workflows. These utilities
handle the complexities of circular references and non-serializable objects.
"""

import json
import inspect
from datetime import datetime
import uuid
from typing import Dict, Any, Optional, List, Set, Type, Tuple

class EntityReference:
    """Reference to another entity in serialized state."""
    
    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        
    def to_dict(self) -> Dict[str, str]:
        return {
            "_type": "entity_reference",
            "entity_type": self.entity_type,
            "entity_id": self.entity_id
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'EntityReference':
        return cls(
            entity_type=data["entity_type"],
            entity_id=data["entity_id"]
        )


class StateBundle:
    """Container for serialized entity state."""
    
    def __init__(
        self, 
        entity_type: str, 
        entity_id: str,
        state_version: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None
    ):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.state_version = state_version
        self.data = data
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "state_version": self.state_version,
            "data": self.data,
            "metadata": self.metadata,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateBundle':
        """Create StateBundle from dictionary."""
        return cls(
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            state_version=data["state_version"],
            data=data["data"],
            metadata=data["metadata"],
            created_at=data["created_at"]
        )
    
    def serialize(self, format: str = "json") -> bytes:
        """Serialize to bytes."""
        if format == "json":
            return json.dumps(self.to_dict()).encode('utf-8')
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @classmethod
    def deserialize(cls, data: bytes, format: str = "json") -> 'StateBundle':
        """Deserialize from bytes."""
        if format == "json":
            return cls.from_dict(json.loads(data.decode('utf-8')))
        else:
            raise ValueError(f"Unsupported format: {format}")


class StateEncoder:
    """Encodes Symphony entities for serialization."""
    
    @staticmethod
    def encode_agent(agent) -> Dict[str, Any]:
        """Encode agent state."""
        # Extract basic properties
        state = {
            "id": agent.id,
            "config": agent.config.dict() if hasattr(agent.config, "dict") else agent.config,
            "type": agent.__class__.__name__,
        }
        
        # Capture interaction history if available
        if hasattr(agent, "_interaction_history"):
            state["interaction_history"] = agent._interaction_history
        
        # Handle memory reference
        if hasattr(agent, "memory") and agent.memory:
            state["memory"] = EntityReference(
                "Memory", 
                agent.memory.id if hasattr(agent.memory, "id") else str(id(agent.memory))
            ).to_dict()
        
        # Handle tools references
        if hasattr(agent, "tools") and agent.tools:
            state["tools"] = [
                EntityReference(
                    "Tool", 
                    tool.id if hasattr(tool, "id") else str(id(tool))
                ).to_dict()
                for tool in agent.tools
            ]
        
        return state
    
    @staticmethod
    def encode_memory(memory) -> Dict[str, Any]:
        """Encode memory state."""
        state = {
            "id": memory.id if hasattr(memory, "id") else str(id(memory)),
            "type": memory.__class__.__name__,
        }
        
        # Handle different memory types
        if hasattr(memory, "items"):
            # For simple dictionary-like memory
            state["items"] = StateEncoder._encode_memory_items(memory.items)
        
        if hasattr(memory, "working_memory") and memory.working_memory:
            # For multi-tier memory
            state["working_memory"] = StateEncoder._encode_memory_items(
                memory.working_memory.items if hasattr(memory.working_memory, "items") else {}
            )
        
        if hasattr(memory, "long_term_memory") and memory.long_term_memory:
            # Reference to long-term memory
            state["long_term_memory"] = EntityReference(
                "Memory",
                memory.long_term_memory.id if hasattr(memory.long_term_memory, "id") 
                else str(id(memory.long_term_memory))
            ).to_dict()
        
        return state
    
    @staticmethod
    def _encode_memory_items(items) -> List[Dict[str, Any]]:
        """Encode memory items, handling complex objects."""
        encoded_items = []
        for key, value in items.items():
            try:
                # Try to encode each item
                encoded_items.append({
                    "key": key,
                    "value": value if isinstance(value, (str, int, float, bool, list, dict)) else str(value),
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                # If encoding fails, store as string representation
                encoded_items.append({
                    "key": key,
                    "value": f"<non-serializable: {type(value).__name__}>",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
        return encoded_items
    
    @staticmethod
    def encode_workflow(workflow) -> Dict[str, Any]:
        """Encode workflow state."""
        state = {
            "id": workflow.id if hasattr(workflow, "id") else str(id(workflow)),
            "type": workflow.__class__.__name__,
            "name": getattr(workflow, "name", "unnamed"),
            "status": getattr(workflow, "status", "unknown")
        }
        
        # Handle workflow steps/tasks
        if hasattr(workflow, "steps"):
            state["steps"] = []
            for step in workflow.steps:
                step_data = {
                    "id": step.id if hasattr(step, "id") else str(id(step)),
                    "name": getattr(step, "name", "unnamed"),
                    "status": getattr(step, "status", "unknown")
                }
                
                # Handle agent reference in step
                if hasattr(step, "agent") and step.agent:
                    step_data["agent"] = EntityReference(
                        "Agent",
                        step.agent.id if hasattr(step.agent, "id") else str(id(step.agent))
                    ).to_dict()
                
                state["steps"].append(step_data)
        
        return state
    
    @staticmethod
    def encode_task(task) -> Dict[str, Any]:
        """Encode task state."""
        state = {
            "id": task.id if hasattr(task, "id") else str(id(task)),
            "type": task.__class__.__name__,
            "name": getattr(task, "name", "unnamed"),
            "status": getattr(task, "status", "unknown"),
            "query": getattr(task, "query", ""),
            "result": getattr(task, "result", None)
        }
        
        # Handle agent reference
        if hasattr(task, "agent") and task.agent:
            state["agent"] = EntityReference(
                "Agent",
                task.agent.id if hasattr(task.agent, "id") else str(id(task.agent))
            ).to_dict()
        
        return state


class StateDecoder:
    """Decodes serialized state into Symphony entities."""
    
    @staticmethod
    def decode_agent(data: Dict[str, Any], registry: Any) -> Any:
        """Decode agent state, resolving references using registry."""
        # Placeholder for now - will be implemented in full version
        # This requires integration with the actual agent classes
        raise NotImplementedError("Agent decoding not yet implemented")
    
    @staticmethod
    def decode_memory(data: Dict[str, Any], registry: Any) -> Any:
        """Decode memory state, resolving references using registry."""
        # Placeholder for now - will be implemented in full version
        raise NotImplementedError("Memory decoding not yet implemented")
    
    @staticmethod
    def decode_workflow(data: Dict[str, Any], registry: Any) -> Any:
        """Decode workflow state, resolving references using registry."""
        # Placeholder for now - will be implemented in full version
        raise NotImplementedError("Workflow decoding not yet implemented")
    
    @staticmethod
    def decode_task(data: Dict[str, Any], registry: Any) -> Any:
        """Decode task state, resolving references using registry."""
        # Placeholder for now - will be implemented in full version
        raise NotImplementedError("Task decoding not yet implemented")


def create_state_bundle(entity, entity_type: Optional[str] = None) -> StateBundle:
    """Create a state bundle for the given entity."""
    # Determine entity type if not provided
    if entity_type is None:
        entity_type = entity.__class__.__name__
    
    # Get entity ID
    entity_id = getattr(entity, "id", str(id(entity)))
    
    # Select encoder based on entity type
    if entity_type == "Agent" or "Agent" in entity.__class__.__name__:
        data = StateEncoder.encode_agent(entity)
    elif entity_type == "Memory" or "Memory" in entity.__class__.__name__:
        data = StateEncoder.encode_memory(entity)
    elif entity_type == "Workflow" or "Workflow" in entity.__class__.__name__:
        data = StateEncoder.encode_workflow(entity)
    elif entity_type == "Task" or "Task" in entity.__class__.__name__:
        data = StateEncoder.encode_task(entity)
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    
    # Create state bundle
    return StateBundle(
        entity_type=entity_type,
        entity_id=entity_id,
        state_version="1.0",
        data=data
    )