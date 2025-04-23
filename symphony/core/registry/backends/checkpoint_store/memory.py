"""In-memory implementation of the CheckpointStore backend."""

import time
from typing import List, Dict, Any, Optional

from symphony.core.registry.backends.checkpoint_store.base import CheckpointStoreBackend


class InMemoryCheckpointStore(CheckpointStoreBackend):
    """In-memory implementation of checkpoint store.
    
    Stores checkpoints in memory. This implementation is suitable for
    testing and non-persistent use cases.
    """
    
    class Provider:
        """Provider for creating InMemoryCheckpointStore instances."""
        
        @staticmethod
        def create_backend(config: Dict[str, Any] = None) -> 'InMemoryCheckpointStore':
            """Create a new InMemoryCheckpointStore instance.
            
            Args:
                config: Optional configuration (ignored for memory store)
                
            Returns:
                A new InMemoryCheckpointStore instance
            """
            return InMemoryCheckpointStore()
    
    def __init__(self):
        """Initialize in-memory checkpoint store."""
        self.checkpoints: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the backend with configuration.
        
        Args:
            config: Configuration dictionary (ignored for memory store)
        """
        pass  # No initialization needed for in-memory store
    
    async def connect(self) -> None:
        """Connect to the storage backend."""
        pass  # No connection needed for in-memory store
    
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        self.checkpoints.clear()
        self.metadata.clear()
    
    async def health_check(self) -> bool:
        """Check if the backend is healthy.
        
        Returns:
            Always True for in-memory store
        """
        return True
    
    async def save_checkpoint(
        self, 
        checkpoint_id: str, 
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save a checkpoint.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            data: Checkpoint data to store
            metadata: Optional metadata about the checkpoint
        """
        # Store checkpoint data
        self.checkpoints[checkpoint_id] = data
        
        # Store metadata with timestamp
        self.metadata[checkpoint_id] = metadata or {}
        self.metadata[checkpoint_id]["timestamp"] = time.time()
        self.metadata[checkpoint_id]["checkpoint_id"] = checkpoint_id
    
    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get a checkpoint by ID.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            
        Returns:
            Dictionary containing the checkpoint data and metadata,
            or None if not found
        """
        if checkpoint_id not in self.checkpoints:
            return None
        
        return {
            "checkpoint_id": checkpoint_id,
            "data": self.checkpoints[checkpoint_id],
            "metadata": self.metadata.get(checkpoint_id, {})
        }
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            
        Returns:
            True if deleted, False if not found
        """
        if checkpoint_id not in self.checkpoints:
            return False
        
        del self.checkpoints[checkpoint_id]
        if checkpoint_id in self.metadata:
            del self.metadata[checkpoint_id]
        
        return True
    
    async def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints.
        
        Returns:
            List of checkpoint metadata dictionaries
        """
        return [
            {
                "checkpoint_id": checkpoint_id,
                "metadata": metadata
            }
            for checkpoint_id, metadata in self.metadata.items()
        ]
    
    async def get_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Get the most recent checkpoint.
        
        Returns:
            The latest checkpoint, or None if no checkpoints exist
        """
        if not self.metadata:
            return None
        
        # Find checkpoint with highest timestamp
        latest_id = max(
            self.metadata.keys(),
            key=lambda cid: self.metadata[cid].get("timestamp", 0)
        )
        
        return await self.get_checkpoint(latest_id)