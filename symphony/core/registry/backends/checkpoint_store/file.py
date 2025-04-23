"""File-based implementation of the CheckpointStore backend."""

import os
import json
import time
import asyncio
from typing import List, Dict, Any, Optional

from symphony.core.registry.backends.checkpoint_store.base import CheckpointStoreBackend


class FileCheckpointStore(CheckpointStoreBackend):
    """File-based implementation of checkpoint store.
    
    Stores checkpoints as JSON files on disk. This implementation is suitable
    for persistent checkpointing across application restarts.
    """
    
    class Provider:
        """Provider for creating FileCheckpointStore instances."""
        
        @staticmethod
        def create_backend(config: Dict[str, Any] = None) -> 'FileCheckpointStore':
            """Create a new FileCheckpointStore instance.
            
            Args:
                config: Configuration dictionary, must contain "path" key
                
            Returns:
                A new FileCheckpointStore instance
                
            Raises:
                ValueError: If path is not provided in config
            """
            if not config or "path" not in config:
                raise ValueError("FileCheckpointStore requires 'path' in configuration")
            
            return FileCheckpointStore(config["path"])
    
    def __init__(self, path: str):
        """Initialize file-based checkpoint store.
        
        Args:
            path: Path to directory for storing checkpoint files
        """
        self.path = path
        self.checkpoints_path = os.path.join(path, "checkpoints")
        self.metadata_path = os.path.join(path, "metadata")
        self.metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the backend with configuration.
        
        Args:
            config: Configuration dictionary (path is already set in constructor)
        """
        # Create directories if they don't exist
        os.makedirs(self.checkpoints_path, exist_ok=True)
        os.makedirs(self.metadata_path, exist_ok=True)
    
    async def connect(self) -> None:
        """Connect to the storage backend.
        
        Loads checkpoint metadata into memory for efficient access.
        """
        # Load metadata for all checkpoints
        await self._load_metadata()
    
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        # Clear metadata cache
        self.metadata_cache.clear()
    
    async def health_check(self) -> bool:
        """Check if the backend is healthy.
        
        Returns:
            True if directories exist and are writable
        """
        if not os.path.exists(self.checkpoints_path) or not os.path.exists(self.metadata_path):
            return False
        
        # Check if directories are writable
        try:
            test_file = os.path.join(self.checkpoints_path, "healthcheck")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return True
        except (IOError, OSError):
            return False
    
    async def _load_metadata(self) -> None:
        """Load metadata for all checkpoints."""
        async with self._lock:
            # Clear existing metadata cache
            self.metadata_cache.clear()
            
            # List all metadata files
            if not os.path.exists(self.metadata_path):
                return
            
            for filename in os.listdir(self.metadata_path):
                if not filename.endswith(".json"):
                    continue
                
                try:
                    checkpoint_id = filename[:-5]  # Remove .json extension
                    file_path = os.path.join(self.metadata_path, filename)
                    
                    with open(file_path, "r") as f:
                        metadata = json.load(f)
                    
                    self.metadata_cache[checkpoint_id] = metadata
                except Exception:
                    # Skip files that can't be loaded
                    continue
    
    def _get_checkpoint_path(self, checkpoint_id: str) -> str:
        """Get file path for checkpoint data."""
        return os.path.join(self.checkpoints_path, f"{checkpoint_id}.json")
    
    def _get_metadata_path(self, checkpoint_id: str) -> str:
        """Get file path for checkpoint metadata."""
        return os.path.join(self.metadata_path, f"{checkpoint_id}.json")
    
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
        # Prepare metadata
        meta = metadata or {}
        meta["timestamp"] = time.time()
        meta["checkpoint_id"] = checkpoint_id
        
        # Save data file
        data_path = self._get_checkpoint_path(checkpoint_id)
        metadata_path = self._get_metadata_path(checkpoint_id)
        
        async with self._lock:
            # Save data
            with open(data_path, "w") as f:
                json.dump(data, f, indent=2)
            
            # Save metadata
            with open(metadata_path, "w") as f:
                json.dump(meta, f, indent=2)
        
        # Update metadata cache
        self.metadata_cache[checkpoint_id] = meta
    
    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get a checkpoint by ID.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            
        Returns:
            Dictionary containing the checkpoint data and metadata,
            or None if not found
        """
        # Check if checkpoint exists
        data_path = self._get_checkpoint_path(checkpoint_id)
        if not os.path.exists(data_path):
            return None
        
        try:
            # Load data
            with open(data_path, "r") as f:
                data = json.load(f)
            
            # Get metadata (from cache or load if needed)
            metadata = self.metadata_cache.get(checkpoint_id)
            if not metadata:
                metadata_path = self._get_metadata_path(checkpoint_id)
                if os.path.exists(metadata_path):
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    self.metadata_cache[checkpoint_id] = metadata
                else:
                    metadata = {"checkpoint_id": checkpoint_id}
            
            return {
                "checkpoint_id": checkpoint_id,
                "data": data,
                "metadata": metadata
            }
        except Exception:
            return None
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            
        Returns:
            True if deleted, False if not found
        """
        data_path = self._get_checkpoint_path(checkpoint_id)
        metadata_path = self._get_metadata_path(checkpoint_id)
        
        # Check if checkpoint exists
        if not os.path.exists(data_path) and not os.path.exists(metadata_path):
            return False
        
        # Delete files
        if os.path.exists(data_path):
            os.remove(data_path)
        
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
        
        # Remove from cache
        if checkpoint_id in self.metadata_cache:
            del self.metadata_cache[checkpoint_id]
        
        return True
    
    async def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints.
        
        Returns:
            List of checkpoint metadata dictionaries
        """
        # Ensure metadata is loaded
        if not self.metadata_cache:
            await self._load_metadata()
        
        return [
            {
                "checkpoint_id": checkpoint_id,
                "metadata": metadata
            }
            for checkpoint_id, metadata in self.metadata_cache.items()
        ]
    
    async def get_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Get the most recent checkpoint.
        
        Returns:
            The latest checkpoint, or None if no checkpoints exist
        """
        # Ensure metadata is loaded
        if not self.metadata_cache:
            await self._load_metadata()
        
        if not self.metadata_cache:
            return None
        
        # Find checkpoint with highest timestamp
        latest_id = max(
            self.metadata_cache.keys(),
            key=lambda cid: self.metadata_cache[cid].get("timestamp", 0)
        )
        
        return await self.get_checkpoint(latest_id)