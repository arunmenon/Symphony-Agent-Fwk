"""Event system for Symphony framework."""

import asyncio
import inspect
import logging
import time
import uuid
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Standard event types in Symphony."""
    
    # Agent lifecycle events
    AGENT_CREATED = "agent:created"
    AGENT_STARTED = "agent:started"
    AGENT_FINISHED = "agent:finished"
    AGENT_ERROR = "agent:error"
    
    # Message events
    MESSAGE_RECEIVED = "message:received"
    MESSAGE_SENT = "message:sent"
    
    # Tool events
    TOOL_CALLED = "tool:called"
    TOOL_SUCCEEDED = "tool:succeeded"
    TOOL_FAILED = "tool:failed"
    
    # LLM events
    LLM_REQUEST_SENT = "llm:request_sent"
    LLM_RESPONSE_RECEIVED = "llm:response_received"
    LLM_ERROR = "llm:error"
    
    # Orchestration events
    ORCHESTRATION_STARTED = "orchestration:started"
    ORCHESTRATION_FINISHED = "orchestration:finished"
    ORCHESTRATION_ERROR = "orchestration:error"
    
    # MCP events
    MCP_RESOURCE_ACCESSED = "mcp:resource_accessed"
    MCP_TOOL_CALLED = "mcp:tool_called"
    
    # Custom event
    CUSTOM = "custom"


class Event(BaseModel):
    """Base event class for all events in Symphony."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Union[EventType, str]
    timestamp: float = Field(default_factory=time.time)
    source: str
    data: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def create(
        cls, 
        type: Union[EventType, str], 
        source: str, 
        **kwargs: Any
    ) -> 'Event':
        """Create a new event."""
        return cls(type=type, source=source, data=kwargs)


class EventCallback(BaseModel):
    """Callback registration for events."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: Optional[Union[EventType, str]] = None
    callback: Any  # Can't type properly due to pydantic limitations
    is_async: bool = False


class EventBus:
    """Event bus for publishing and subscribing to events."""
    
    def __init__(self):
        self._callbacks: List[EventCallback] = []
        self._logger = logging.getLogger("symphony.events")
    
    def subscribe(
        self, 
        callback: Callable[[Event], Any], 
        event_type: Optional[Union[EventType, str]] = None
    ) -> str:
        """Subscribe to events.
        
        Args:
            callback: Function to call when an event occurs
            event_type: Optional event type to filter on
            
        Returns:
            Callback ID for unsubscribing
        """
        is_async = asyncio.iscoroutinefunction(callback)
        
        callback_obj = EventCallback(
            event_type=event_type,
            callback=callback,
            is_async=is_async
        )
        
        self._callbacks.append(callback_obj)
        return callback_obj.id
    
    def unsubscribe(self, callback_id: str) -> bool:
        """Unsubscribe from events.
        
        Args:
            callback_id: ID returned from subscribe
            
        Returns:
            True if unsubscribed, False if not found
        """
        for i, callback in enumerate(self._callbacks):
            if callback.id == callback_id:
                self._callbacks.pop(i)
                return True
                
        return False
    
    def publish(self, event: Event) -> None:
        """Publish an event (synchronously).
        
        Args:
            event: Event to publish
        """
        self._logger.debug(f"Event published: {event.type} from {event.source}")
        
        for callback in self._callbacks:
            # Skip if event type doesn't match
            if callback.event_type is not None and callback.event_type != event.type:
                continue
                
            try:
                if callback.is_async:
                    # For async callbacks in a sync context, just fire and forget
                    asyncio.create_task(callback.callback(event))
                else:
                    callback.callback(event)
            except Exception as e:
                self._logger.error(f"Error in event callback: {str(e)}")
    
    async def publish_async(self, event: Event) -> None:
        """Publish an event asynchronously.
        
        Args:
            event: Event to publish
        """
        self._logger.debug(f"Event published async: {event.type} from {event.source}")
        
        for callback in self._callbacks:
            # Skip if event type doesn't match
            if callback.event_type is not None and callback.event_type != event.type:
                continue
                
            try:
                if callback.is_async:
                    await callback.callback(event)
                else:
                    # Run sync callbacks in the executor
                    await asyncio.to_thread(callback.callback, event)
            except Exception as e:
                self._logger.error(f"Error in async event callback: {str(e)}")


# Global event bus instance
default_event_bus = EventBus()