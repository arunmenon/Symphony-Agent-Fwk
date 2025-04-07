"""Memory manager for Symphony."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from symphony.memory.base import BaseMemory, InMemoryMemory
from symphony.memory.kg_memory import KnowledgeGraphMemory
from symphony.memory.local_kg_memory import LocalKnowledgeGraphMemory
from symphony.memory.vector_memory import VectorMemory
from symphony.utils.types import Message


class WorkingMemory(InMemoryMemory):
    """Short-term working memory with automatic expiration."""
    
    def __init__(self, retention_period: float = 3600.0):
        """Initialize working memory.
        
        Args:
            retention_period: How long (in seconds) to retain items by default
        """
        super().__init__()
        self.retention_period = retention_period
        self._timestamps: Dict[str, float] = {}
        
    async def store(self, key: str, value: Any, importance: float = 0.5) -> None:
        """Store a value in memory with the given key."""
        self._storage[key] = value
        self._timestamps[key] = time.time()
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value from memory by key if it hasn't expired."""
        if key not in self._storage:
            return None
            
        # Check if the item has expired
        timestamp = self._timestamps.get(key, 0)
        if time.time() - timestamp > self.retention_period:
            # Item has expired, remove it
            del self._storage[key]
            del self._timestamps[key]
            return None
            
        return self._storage[key]
    
    async def cleanup(self) -> None:
        """Remove expired items from memory."""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self._timestamps.items()
            if current_time - timestamp > self.retention_period
        ]
        
        for key in expired_keys:
            if key in self._storage:
                del self._storage[key]
            if key in self._timestamps:
                del self._timestamps[key]


class MemoryManager:
    """Central memory manager that coordinates different memory systems.
    
    This is a simplified implementation that will evolve over time.
    """
    
    def __init__(
        self,
        working_memory: Optional[WorkingMemory] = None,
        long_term_memory: Optional[VectorMemory] = None,
        kg_memory: Optional[Union[KnowledgeGraphMemory, LocalKnowledgeGraphMemory]] = None
    ):
        """Initialize the memory manager.
        
        Args:
            working_memory: Working memory instance (will create one if not provided)
            long_term_memory: Long-term memory instance (will create one if not provided)
            kg_memory: Optional knowledge graph memory for semantic relationships
        """
        self.memories = {
            "working": working_memory or WorkingMemory(),
            "long_term": long_term_memory or VectorMemory()
        }
        
        # Add knowledge graph memory if provided
        if kg_memory:
            self.memories["kg"] = kg_memory
        
    async def store(
        self, 
        key: str, 
        value: Any, 
        importance: float = 0.5,
        memory_types: Optional[List[str]] = None
    ) -> None:
        """Store information in memory.
        
        Args:
            key: Unique identifier for the information
            value: The information to store
            importance: How important this information is (0.0-1.0)
            memory_types: Which memory systems to store in (if None, uses rules)
        """
        # Convert value to string if needed for vector memory
        content = str(value) if not isinstance(value, str) else value
        
        # Determine which memory systems to use
        if memory_types is None:
            memory_types = ["working"]
            
            # Important items go to long-term memory too
            if importance > 0.7:
                memory_types.append("long_term")
                
            # Very important items also go to knowledge graph if available
            if importance > 0.8 and "kg" in self.memories:
                memory_types.append("kg")
        
        # Store in each specified memory system
        tasks = []
        for memory_type in memory_types:
            if memory_type in self.memories:
                memory = self.memories[memory_type]
                tasks.append(memory.store(key, content))
                
        # Run storage operations concurrently
        await asyncio.gather(*tasks)
    
    async def retrieve(
        self, 
        key: Optional[str] = None, 
        query: Optional[str] = None,
        memory_types: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> Any:
        """Retrieve information from memory.
        
        Args:
            key: Specific key to retrieve
            query: Search query for semantic search
            memory_types: Which memory systems to search (if None, uses default order)
            limit: Maximum number of results for queries
            
        Returns:
            Retrieved information or search results
        """
        if key is not None:
            # When retrieving by key, check working memory first
            if memory_types is None:
                memory_types = ["working", "long_term"]
                
            for memory_type in memory_types:
                if memory_type in self.memories:
                    memory = self.memories[memory_type]
                    result = await memory.retrieve(key)
                    if result is not None:
                        return result
                        
            # Not found in any memory
            return None
            
        elif query is not None:
            # For semantic search, use appropriate memory systems
            if memory_types is None:
                # Set default memory types based on what's available
                memory_types = []
                
                # Prioritize knowledge graph for semantic searches if available
                if "kg" in self.memories:
                    memory_types.append("kg")
                    
                # Also include vector memory
                if "long_term" in self.memories:
                    memory_types.append("long_term")
                
                # If no semantic memories are available, fall back to working memory
                if not memory_types:
                    memory_types = ["working"]
                
            results = []
            for memory_type in memory_types:
                if memory_type in self.memories:
                    memory = self.memories[memory_type]
                    # All memory types should support search
                    search_results = memory.search(query, limit=limit)
                    results.extend(search_results)
                    
            return results
            
        # If neither key nor query is provided
        return None
    
    def add_memory_system(self, name: str, memory_system: BaseMemory) -> None:
        """Add a new memory system to the manager.
        
        Args:
            name: Identifier for the memory system
            memory_system: The memory system instance
        """
        self.memories[name] = memory_system
        
    async def consolidate(self) -> None:
        """Move important information from working to long-term memory.
        
        This represents a simplified memory consolidation process that will
        be expanded in future versions.
        """
        working_memory = self.memories.get("working")
        long_term_memory = self.memories.get("long_term")
        kg_memory = self.memories.get("kg")
        
        if not working_memory:
            return
        
        # Clean up expired items from working memory
        if isinstance(working_memory, WorkingMemory):
            await working_memory.cleanup()
            
        # In a future implementation, this would:
        # 1. Analyze all working memory items and calculate importance
        # 2. Move important items to long-term memory
        # 3. Extract relationships and concepts for knowledge graph
        # 4. Compress or summarize related information
        # 5. Forget low-importance items after they expire
        
        # Here's a placeholder for extracting knowledge triplets for the knowledge graph
        if kg_memory and hasattr(kg_memory, "extract_and_store") and hasattr(working_memory, "_storage"):
            try:
                # Select a few important items from working memory
                # In a real implementation, this would use a proper importance scoring mechanism
                items = list(working_memory._storage.items())
                if items:
                    # Just process the most recent item for demonstration
                    key, value = items[-1]
                    
                    # Extract and store knowledge if the value is a string
                    if isinstance(value, str) and len(value) > 50:
                        await kg_memory.extract_and_store(
                            text=value,
                            source=f"consolidation:{key}"
                        )
            except Exception as e:
                # Just log and continue if extraction fails
                print(f"Error during knowledge extraction: {str(e)}")


class ConversationMemoryManager(MemoryManager):
    """Memory manager specialized for conversation history."""
    
    def __init__(
        self,
        working_memory: Optional[WorkingMemory] = None,
        long_term_memory: Optional[VectorMemory] = None,
        kg_memory: Optional[Union[KnowledgeGraphMemory, LocalKnowledgeGraphMemory]] = None
    ):
        """Initialize conversation memory manager."""
        super().__init__(working_memory, long_term_memory, kg_memory)
        self._messages: List[Message] = []
        
    async def add_message(self, message: Message, importance: Optional[float] = None) -> None:
        """Add a message to conversation history and memory systems.
        
        Args:
            message: The message to add
            importance: Optional importance score (if None, will be calculated)
        """
        # Add to local message history
        self._messages.append(message)
        
        # Determine message importance if not provided
        if importance is None:
            importance = self._calculate_importance(message)
            
        # Create key and metadata
        key = f"message_{len(self._messages)}"
        metadata = {
            "role": message.role,
            "index": len(self._messages) - 1,
            "timestamp": time.time(),
            **message.additional_kwargs
        }
        
        # Store in appropriate memory systems
        memory_types = ["working"]
        if importance > 0.7:
            memory_types.append("long_term")
            
        # Very important messages also go to knowledge graph if available
        if importance > 0.8 and "kg" in self.memories:
            memory_types.append("kg")
            
        # For long-term memory, we need to store content and metadata
        if "long_term" in memory_types and "long_term" in self.memories:
            long_term = self.memories["long_term"]
            
            # Add directly to vector memory with metadata
            entry = {
                "content": message.content,
                "metadata": metadata
            }
            await long_term.store(key, entry)
            
        # For knowledge graph memory, use specialized conversation methods if available
        if "kg" in memory_types and "kg" in self.memories:
            kg = self.memories["kg"]
            
            # Use add_message method if available (for conversation-specific KG memory)
            if hasattr(kg, "add_message"):
                await kg.add_message(message)
            # Otherwise just store the message content
            else:
                await kg.store(key, message.content)
            
        # For working memory, just store the message
        if "working" in memory_types and "working" in self.memories:
            working = self.memories["working"]
            await working.store(key, message)
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get conversation history, optionally limited to the last N messages."""
        if limit is not None:
            return self._messages[-limit:]
        return self._messages
    
    async def search_conversation(
        self, 
        query: str, 
        limit: Optional[int] = None,
        memory_types: Optional[List[str]] = None
    ) -> List[Message]:
        """Search conversation history for messages related to the query.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            memory_types: Which memory systems to search (if None, uses all available)
            
        Returns:
            List of messages that match the query
        """
        # Determine which memory systems to use
        if memory_types is None:
            memory_types = []
            
            # Use knowledge graph for most accurate semantic search if available
            if "kg" in self.memories and hasattr(self.memories["kg"], "search_conversation"):
                memory_types.append("kg")
                
            # Also use vector memory if available
            if "long_term" in self.memories:
                memory_types.append("long_term")
                
            # If no semantic memory systems are available, fall back to string matching
            if not memory_types:
                memory_types = ["fallback"]
        
        all_messages = []
        
        # Try searching in knowledge graph memory first (most comprehensive)
        if "kg" in memory_types and "kg" in self.memories:
            kg = self.memories["kg"]
            
            # Use specialized conversation search if available
            if hasattr(kg, "search_conversation"):
                kg_results = await kg.search_conversation(query, limit=limit)
                
                # Format might vary depending on KG implementation, handle different result formats
                for result in kg_results:
                    if isinstance(result, Message):
                        all_messages.append(result)
                    elif isinstance(result, dict) and "message" in result:
                        all_messages.append(result["message"])
                    elif isinstance(result, tuple) and len(result) >= 2:
                        # Might be (message, score) tuple
                        msg = result[0]
                        if isinstance(msg, Message):
                            all_messages.append(msg)
        
        # Then try vector memory
        if "long_term" in memory_types and "long_term" in self.memories:
            long_term = self.memories["long_term"]
            results = long_term.search(query, limit=limit, include_metadata=True)
            
            # Convert results to Message objects
            for content, metadata in results:
                if isinstance(metadata, dict):
                    role = metadata.get("role", "unknown")
                    # Remove known metadata fields, keep additional_kwargs
                    additional_kwargs = {
                        k: v for k, v in metadata.items()
                        if k not in ("role", "index", "timestamp")
                    }
                    
                    all_messages.append(Message(
                        role=role,
                        content=content,
                        additional_kwargs=additional_kwargs
                    ))
        
        # Fallback: Basic string matching on recent messages
        if ("fallback" in memory_types or not all_messages) and self._messages:
            matching_messages = []
            for msg in self._messages:
                if query.lower() in msg.content.lower():
                    matching_messages.append(msg)
                    
            all_messages.extend(matching_messages)
        
        # Remove duplicates (might have found same message in multiple memory systems)
        unique_messages = []
        seen_contents = set()
        
        for msg in all_messages:
            # Use content as uniqueness key (could be enhanced with role and timestamp)
            if msg.content not in seen_contents:
                seen_contents.add(msg.content)
                unique_messages.append(msg)
        
        # Apply limit
        if limit is not None:
            unique_messages = unique_messages[:limit]
            
        return unique_messages
    
    def _calculate_importance(self, message: Message) -> float:
        """Calculate importance of a message based on content and context.
        
        This is a simple implementation that will be enhanced over time.
        """
        importance = 0.5
        
        # Simple heuristics for importance
        # Messages with questions are usually important
        if "?" in message.content:
            importance += 0.2
            
        # Messages with action items or decisions
        action_keywords = ["must", "should", "need to", "important", "critical", "decide"]
        if any(keyword in message.content.lower() for keyword in action_keywords):
            importance += 0.3
            
        # User messages might be more important than system or assistant
        if message.role == "user":
            importance += 0.1
            
        # Cap importance at 1.0
        return min(importance, 1.0)
        
    async def clear(self) -> None:
        """Clear conversation history and memories."""
        self._messages = []
        
        # Clear each memory system
        for memory in self.memories.values():
            if hasattr(memory, "clear"):
                memory.clear()