"""Storage providers for Symphony state persistence.

This module provides storage backends for persisting Symphony state.
The initial implementation focuses on file-based storage with
atomic operations to ensure state consistency.
"""

import os
import json
import shutil
import tempfile
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import uuid

from .serialization import StateBundle


class StorageError(Exception):
    """Base exception for storage-related errors."""
    pass


class TransactionError(StorageError):
    """Exception raised when a transaction operation fails."""
    pass


class Transaction:
    """A transaction for atomic storage operations."""
    
    def __init__(self, provider: 'FileStorageProvider', transaction_id: str):
        self.provider = provider
        self.transaction_id = transaction_id
        self.temp_dir = os.path.join(
            provider.base_path, 
            "transactions", 
            transaction_id
        )
        self.operations = []
        self.committed = False
        self.rolled_back = False
        
        # Create transaction directory
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def store(self, key: str, data: bytes) -> None:
        """Store data at key within transaction."""
        if self.committed or self.rolled_back:
            raise TransactionError("Transaction already finalized")
        
        # Normalize key (remove leading slashes)
        key = key.lstrip('/')
        
        # Create parent directories
        key_path = os.path.join(self.temp_dir, key)
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        
        # Write to temporary file first
        with tempfile.NamedTemporaryFile(delete=False, dir=self.temp_dir) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        
        # Move to final location within transaction
        try:
            shutil.move(tmp_path, key_path)
            self.operations.append(("store", key))
        except Exception as e:
            # Clean up temp file if move fails
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except:
                pass
            raise TransactionError(f"Failed to store {key}: {e}")
    
    async def commit(self) -> bool:
        """Commit the transaction atomically."""
        if self.committed:
            return True
            
        if self.rolled_back:
            raise TransactionError("Cannot commit a rolled back transaction")
        
        try:
            # Create marker file to indicate transaction is ready
            ready_file = os.path.join(self.temp_dir, ".ready")
            with open(ready_file, 'w') as f:
                f.write(datetime.utcnow().isoformat())
            
            # Move all files to their final locations
            for op, key in self.operations:
                if op == "store":
                    src_path = os.path.join(self.temp_dir, key)
                    dst_path = os.path.join(self.provider.base_path, "data", key)
                    
                    # Create parent directories
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    # Move file to final location
                    shutil.move(src_path, dst_path)
            
            # Mark as committed
            self.committed = True
            
            # Clean up transaction directory
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                
            return True
        except Exception as e:
            # Log error but don't delete transaction directory
            # This allows manual recovery if needed
            raise TransactionError(f"Failed to commit transaction {self.transaction_id}: {e}")
    
    async def rollback(self) -> None:
        """Roll back the transaction, discarding all changes."""
        if self.committed:
            raise TransactionError("Cannot roll back a committed transaction")
            
        if self.rolled_back:
            return
            
        try:
            # Clean up transaction directory
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            
            self.rolled_back = True
        except Exception as e:
            raise TransactionError(f"Failed to roll back transaction {self.transaction_id}: {e}")


class FileStorageProvider:
    """File-based storage provider for Symphony state."""
    
    def __init__(self, base_path: str = ".symphony/state"):
        """Initialize file storage provider.
        
        Args:
            base_path: Base directory for state storage
        """
        self.base_path = os.path.abspath(base_path)
        
        # Create directory structure
        os.makedirs(os.path.join(self.base_path, "data"), exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "transactions"), exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "checkpoints"), exist_ok=True)
        
    async def store(self, key: str, data: bytes) -> None:
        """Store data at key.
        
        Args:
            key: Storage key (will be converted to path)
            data: Data to store
        """
        # Normalize key (remove leading slashes)
        key = key.lstrip('/')
        
        # Create parent directories
        key_path = os.path.join(self.base_path, "data", key)
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        
        # Write to temporary file first
        with tempfile.NamedTemporaryFile(delete=False, dir=os.path.dirname(key_path)) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        
        # Move to final location (atomic on most filesystems)
        try:
            shutil.move(tmp_path, key_path)
        except Exception as e:
            # Clean up temp file if move fails
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except:
                pass
            raise StorageError(f"Failed to store {key}: {e}")
    
    async def retrieve(self, key: str) -> Optional[bytes]:
        """Retrieve data stored at key.
        
        Args:
            key: Storage key
            
        Returns:
            Data if found, None if not found
        """
        # Normalize key
        key = key.lstrip('/')
        
        # Get file path
        key_path = os.path.join(self.base_path, "data", key)
        
        # Check if file exists
        if not os.path.exists(key_path):
            return None
        
        # Read file
        try:
            with open(key_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise StorageError(f"Failed to retrieve {key}: {e}")
    
    async def delete(self, key: str) -> bool:
        """Delete data stored at key.
        
        Args:
            key: Storage key
            
        Returns:
            True if deleted, False if not found
        """
        # Normalize key
        key = key.lstrip('/')
        
        # Get file path
        key_path = os.path.join(self.base_path, "data", key)
        
        # Check if file exists
        if not os.path.exists(key_path):
            return False
        
        # Delete file
        try:
            os.unlink(key_path)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete {key}: {e}")
    
    async def create_transaction(self) -> Transaction:
        """Create a new transaction.
        
        Returns:
            Transaction object
        """
        transaction_id = f"tx_{uuid.uuid4().hex}"
        return Transaction(self, transaction_id)
    
    async def list_keys(self, prefix: str = "") -> List[str]:
        """List keys with given prefix.
        
        Args:
            prefix: Key prefix to filter by
            
        Returns:
            List of matching keys
        """
        # Normalize prefix
        prefix = prefix.lstrip('/')
        
        # Get directory path
        dir_path = os.path.join(self.base_path, "data", prefix)
        
        # Check if directory exists
        if not os.path.exists(dir_path):
            return []
        
        # Build list of keys
        keys = []
        prefix_len = len(os.path.join(self.base_path, "data"))
        
        for root, _, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Convert path back to key
                key = file_path[prefix_len:].lstrip('/')
                keys.append(key)
        
        return keys
    
    async def store_bundle(self, bundle: StateBundle, key: Optional[str] = None) -> str:
        """Store a state bundle.
        
        Args:
            bundle: StateBundle to store
            key: Optional storage key, if not provided will be generated
            
        Returns:
            Storage key where bundle was stored
        """
        if key is None:
            # Generate key from bundle properties
            key = f"entities/{bundle.entity_type}/{bundle.entity_id}.json"
        
        # Serialize bundle
        data = bundle.serialize()
        
        # Store data
        await self.store(key, data)
        
        return key
    
    async def retrieve_bundle(self, key: str) -> Optional[StateBundle]:
        """Retrieve a state bundle.
        
        Args:
            key: Storage key
            
        Returns:
            StateBundle if found, None if not found
        """
        # Retrieve data
        data = await self.retrieve(key)
        
        # Return None if not found
        if data is None:
            return None
        
        # Deserialize bundle
        try:
            return StateBundle.deserialize(data)
        except Exception as e:
            raise StorageError(f"Failed to deserialize bundle at {key}: {e}")