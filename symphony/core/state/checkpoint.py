"""Checkpoint management for Symphony.

This module provides checkpoint creation and restoration capabilities,
ensuring consistent state across all entities in a Symphony instance.
"""

import os
import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Set, Type, Tuple

from .serialization import StateBundle, create_state_bundle
from .storage import FileStorageProvider, Transaction, StorageError


class CheckpointError(Exception):
    """Exception raised for checkpoint-related errors."""
    pass


class Checkpoint:
    """Represents a consistent checkpoint of Symphony state."""
    
    def __init__(
        self,
        checkpoint_id: str,
        created_at: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.checkpoint_id = checkpoint_id
        self.created_at = created_at
        self.name = name
        self.metadata = metadata or {}
        self.entities = []
    
    def add_entity(self, entity_type: str, entity_id: str, bundle_key: str) -> None:
        """Add entity to checkpoint."""
        self.entities.append({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "bundle_key": bundle_key
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at,
            "name": self.name,
            "metadata": self.metadata,
            "entities": self.entities
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """Create Checkpoint from dictionary."""
        checkpoint = cls(
            checkpoint_id=data["checkpoint_id"],
            created_at=data["created_at"],
            name=data.get("name"),
            metadata=data.get("metadata", {})
        )
        
        for entity in data.get("entities", []):
            checkpoint.add_entity(
                entity_type=entity["entity_type"],
                entity_id=entity["entity_id"],
                bundle_key=entity["bundle_key"]
            )
        
        return checkpoint


class CheckpointManager:
    """Manages creation and restoration of consistent checkpoints."""
    
    def __init__(self, storage_provider: FileStorageProvider):
        """Initialize checkpoint manager.
        
        Args:
            storage_provider: Storage provider for persistence
        """
        self.storage = storage_provider
    
    async def _discover_entities(self, symphony_instance) -> List[Tuple[str, Any]]:
        """Discover all stateful entities in Symphony instance.
        
        Args:
            symphony_instance: Symphony instance
            
        Returns:
            List of (entity_type, entity) pairs
        """
        entities = []
        
        # Discover agents
        if hasattr(symphony_instance, "agents"):
            agents = []
            
            # Handle different agent collection patterns
            if hasattr(symphony_instance.agents, "get_all_agents"):
                agents = await symphony_instance.agents.get_all_agents()
            elif hasattr(symphony_instance.agents, "agents"):
                agents = symphony_instance.agents.agents.values()
            elif hasattr(symphony_instance, "_agents"):
                agents = symphony_instance._agents.values()
                
            for agent in agents:
                entities.append(("Agent", agent))
        
        # Discover memories
        if hasattr(symphony_instance, "memory") and symphony_instance.memory:
            entities.append(("Memory", symphony_instance.memory))
        elif hasattr(symphony_instance, "_memory") and symphony_instance._memory:
            entities.append(("Memory", symphony_instance._memory))
        
        # Discover active workflows
        if hasattr(symphony_instance, "workflows"):
            workflows = []
            
            # Handle different workflow collection patterns
            if hasattr(symphony_instance.workflows, "get_all_workflows"):
                workflows = await symphony_instance.workflows.get_all_workflows()
            elif hasattr(symphony_instance.workflows, "active_workflows"):
                workflows = symphony_instance.workflows.active_workflows.values()
            elif hasattr(symphony_instance, "_workflows"):
                workflows = symphony_instance._workflows.values()
                
            for workflow in workflows:
                entities.append(("Workflow", workflow))
        
        # Discover tasks
        if hasattr(symphony_instance, "tasks"):
            tasks = []
            
            # Handle different task collection patterns
            if hasattr(symphony_instance.tasks, "get_all_tasks"):
                tasks = await symphony_instance.tasks.get_all_tasks()
            elif hasattr(symphony_instance.tasks, "tasks"):
                tasks = symphony_instance.tasks.tasks.values()
            elif hasattr(symphony_instance, "_tasks"):
                tasks = symphony_instance._tasks.values()
                
            for task in tasks:
                entities.append(("Task", task))
        
        return entities
    
    async def create_checkpoint(
        self, 
        symphony_instance, 
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create checkpoint of Symphony state.
        
        Args:
            symphony_instance: Symphony instance
            name: Optional checkpoint name
            metadata: Optional metadata to store with checkpoint
            
        Returns:
            Checkpoint ID
        """
        # Generate checkpoint ID
        checkpoint_id = f"ckpt_{uuid.uuid4().hex}"
        
        # Create checkpoint object
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            created_at=datetime.utcnow().isoformat(),
            name=name,
            metadata=metadata or {}
        )
        
        # Discover entities to checkpoint
        entities = await self._discover_entities(symphony_instance)
        
        # Start transaction
        transaction = await self.storage.create_transaction()
        
        try:
            # Create state bundles for each entity
            for entity_type, entity in entities:
                try:
                    # Create state bundle
                    bundle = create_state_bundle(entity, entity_type)
                    
                    # Store bundle in transaction
                    bundle_key = f"checkpoints/{checkpoint_id}/entities/{entity_type}/{bundle.entity_id}.json"
                    await transaction.store(bundle_key, bundle.serialize())
                    
                    # Add to checkpoint manifest
                    checkpoint.add_entity(
                        entity_type=entity_type,
                        entity_id=bundle.entity_id,
                        bundle_key=bundle_key
                    )
                except Exception as e:
                    # Log error but continue with other entities
                    print(f"Error checkpointing {entity_type} {getattr(entity, 'id', id(entity))}: {e}")
            
            # Store checkpoint manifest
            manifest_key = f"checkpoints/{checkpoint_id}/manifest.json"
            await transaction.store(
                manifest_key,
                json.dumps(checkpoint.to_dict()).encode('utf-8')
            )
            
            # Store in latest checkpoint reference
            await transaction.store(
                "checkpoints/latest.txt",
                checkpoint_id.encode('utf-8')
            )
            
            # Commit transaction
            await transaction.commit()
            
            return checkpoint_id
            
        except Exception as e:
            # Roll back transaction if anything fails
            await transaction.rollback()
            raise CheckpointError(f"Failed to create checkpoint: {e}")
    
    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get checkpoint by ID.
        
        Args:
            checkpoint_id: Checkpoint ID
            
        Returns:
            Checkpoint if found, None if not found
        """
        # Get manifest
        manifest_key = f"checkpoints/{checkpoint_id}/manifest.json"
        manifest_data = await self.storage.retrieve(manifest_key)
        
        if not manifest_data:
            return None
        
        try:
            # Parse manifest
            manifest = json.loads(manifest_data.decode('utf-8'))
            return Checkpoint.from_dict(manifest)
        except Exception as e:
            raise CheckpointError(f"Failed to load checkpoint {checkpoint_id}: {e}")
    
    async def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """Get latest checkpoint.
        
        Returns:
            Latest checkpoint if any, None otherwise
        """
        # Get latest checkpoint ID
        latest_data = await self.storage.retrieve("checkpoints/latest.txt")
        
        if not latest_data:
            return None
        
        checkpoint_id = latest_data.decode('utf-8').strip()
        return await self.get_checkpoint(checkpoint_id)
    
    async def list_checkpoints(self) -> List[Checkpoint]:
        """List all checkpoints.
        
        Returns:
            List of checkpoints
        """
        # List checkpoint directories
        checkpoints = []
        
        # Get all manifest files
        keys = await self.storage.list_keys("checkpoints")
        manifest_keys = [k for k in keys if k.endswith("/manifest.json")]
        
        for key in manifest_keys:
            try:
                # Get manifest data
                manifest_data = await self.storage.retrieve(key)
                
                if manifest_data:
                    # Parse manifest
                    manifest = json.loads(manifest_data.decode('utf-8'))
                    checkpoints.append(Checkpoint.from_dict(manifest))
            except Exception as e:
                # Log error but continue with other checkpoints
                print(f"Error loading checkpoint manifest {key}: {e}")
        
        # Sort by creation time (newest first)
        checkpoints.sort(key=lambda c: c.created_at, reverse=True)
        
        return checkpoints
    
    async def restore_checkpoint(self, symphony_instance, checkpoint_id: str) -> None:
        """Restore Symphony state from checkpoint.
        
        Args:
            symphony_instance: Symphony instance to restore
            checkpoint_id: Checkpoint ID to restore from
            
        Raises:
            CheckpointError: If checkpoint not found or restoration fails
        """
        # Get checkpoint manifest
        checkpoint = await self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise CheckpointError(f"Checkpoint {checkpoint_id} not found")
        
        try:
            # Import RestoreManager (here to avoid circular imports)
            from .restore import restore_manager, RestorationError
            
            # Use restore manager to restore from checkpoint
            await restore_manager.restore_from_checkpoint(
                checkpoint.to_dict(),
                symphony_instance
            )
            
            print(f"Restored Symphony state from checkpoint: {checkpoint_id}")
            
        except RestorationError as e:
            raise CheckpointError(f"Failed to restore checkpoint {checkpoint_id}: {e}")
        except ImportError as e:
            raise CheckpointError(f"Restoration module not available: {e}")
        except Exception as e:
            raise CheckpointError(f"Unexpected error restoring checkpoint {checkpoint_id}: {e}")
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete checkpoint.
        
        Args:
            checkpoint_id: Checkpoint ID
            
        Returns:
            True if deleted, False if not found
        """
        # Get checkpoint
        checkpoint = await self.get_checkpoint(checkpoint_id)
        
        if not checkpoint:
            return False
        
        # Delete all checkpoint files
        keys = await self.storage.list_keys(f"checkpoints/{checkpoint_id}")
        
        for key in keys:
            await self.storage.delete(key)
        
        # Delete manifest
        manifest_key = f"checkpoints/{checkpoint_id}/manifest.json"
        await self.storage.delete(manifest_key)
        
        # Update latest reference if this was the latest
        latest = await self.get_latest_checkpoint()
        if latest and latest.checkpoint_id == checkpoint_id:
            # Find next latest
            checkpoints = await self.list_checkpoints()
            if checkpoints:
                # Update latest reference
                await self.storage.store(
                    "checkpoints/latest.txt",
                    checkpoints[0].checkpoint_id.encode('utf-8')
                )
            else:
                # No checkpoints left
                await self.storage.delete("checkpoints/latest.txt")
        
        return True