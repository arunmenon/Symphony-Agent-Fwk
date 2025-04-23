"""Checkpoint store base interface.

This module defines the abstract interface for checkpoint store backends
used for saving and restoring application state.
"""

from abc import abstractmethod
from typing import List, Dict, Any, Optional

from symphony.core.registry.backends.base import StorageBackend


class CheckpointStoreBackend(StorageBackend):
    """Abstract base class for checkpoint store backends.
    
    Checkpoint stores provide storage for application state checkpoints,
    allowing saving and restoring the state of a Symphony instance.
    """
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get a checkpoint by ID.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            
        Returns:
            Dictionary containing the checkpoint data, or None if not found
        """
        pass
    
    @abstractmethod
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints.
        
        Returns:
            List of checkpoint metadata dictionaries
        """
        pass
    
    @abstractmethod
    async def get_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Get the most recent checkpoint.
        
        Returns:
            The latest checkpoint, or None if no checkpoints exist
        """
        pass