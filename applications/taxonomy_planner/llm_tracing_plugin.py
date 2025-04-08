"""LLM Tracing Plugin for Symphony.

This plugin adds tracing capabilities to model calls in Symphony,
capturing requests, responses, and performance metrics.
"""

import os
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable

from symphony.core.plugin import LLMPlugin
from symphony.core.container import Container
from symphony.core.events import EventBus, Event, EventType

logger = logging.getLogger(__name__)

class LLMTracingPlugin(LLMPlugin):
    """Plugin for tracing LLM calls in Symphony."""
    
    @property
    def name(self) -> str:
        return "llm_tracing_plugin"
    
    @property
    def version(self) -> str:
        return "0.1.0"
    
    @property
    def description(self) -> str:
        return "Adds tracing for LLM calls in Symphony"
    
    def __init__(self, trace_dir: str = "traces/llm_calls"):
        """Initialize LLM tracing plugin.
        
        Args:
            trace_dir: Directory to store trace files
        """
        super().__init__()
        self.trace_dir = trace_dir
        self.session_id = str(uuid.uuid4())
        self.session_start = datetime.now()
        self.event_subscribers = []
        
        # Create trace directory if it doesn't exist
        os.makedirs(trace_dir, exist_ok=True)
        
        # Create session file
        self.trace_file = os.path.join(trace_dir, f"trace_{self.session_id}.jsonl")
        with open(self.trace_file, 'w') as f:
            # Initialize with session info
            session_info = {
                "type": "session_start",
                "timestamp": self.session_start.isoformat(),
                "session_id": self.session_id
            }
            f.write(json.dumps(session_info) + "\n")
        
        logger.info(f"LLM Tracing enabled. Session ID: {self.session_id}")
        logger.info(f"Trace file: {self.trace_file}")
    
    def initialize(self, container: Container, event_bus: EventBus) -> None:
        """Initialize the plugin.
        
        Args:
            container: The service container
            event_bus: The event bus
        """
        self.container = container
        self.event_bus = event_bus
        
        # Subscribe to LLM-related events
        self._subscribe_to_llm_events(event_bus)
        
        # Register ourselves as an LLM middleware
        # This part depends on Symphony's internal architecture
        # In a real implementation, we would register with Symphony's LLM client factory
        logger.info("LLM Tracing middleware registered")
    
    def _subscribe_to_llm_events(self, event_bus: EventBus) -> None:
        """Subscribe to LLM-related events in the event bus."""
        
        # Subscribe to model request event
        request_subscriber = event_bus.subscribe(
            "llm.request", 
            lambda event: self._handle_llm_request(event)
        )
        self.event_subscribers.append(request_subscriber)
        
        # Subscribe to model response event
        response_subscriber = event_bus.subscribe(
            "llm.response", 
            lambda event: self._handle_llm_response(event)
        )
        self.event_subscribers.append(response_subscriber)
        
        # Subscribe to model error event
        error_subscriber = event_bus.subscribe(
            "llm.error", 
            lambda event: self._handle_llm_error(event)
        )
        self.event_subscribers.append(error_subscriber)
    
    def _handle_llm_request(self, event: Event) -> None:
        """Handle LLM request event."""
        data = event.data
        self.log_event("llm_request", data)
    
    def _handle_llm_response(self, event: Event) -> None:
        """Handle LLM response event."""
        data = event.data
        self.log_event("llm_response", data)
    
    def _handle_llm_error(self, event: Event) -> None:
        """Handle LLM error event."""
        data = event.data
        self.log_event("llm_error", data)
    
    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log an event to the trace file.
        
        Args:
            event_type: Type of event (llm_request, llm_response, etc.)
            data: Event data
        """
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "data": data
        }
        
        with open(self.trace_file, 'a') as f:
            f.write(json.dumps(event) + "\n")
    
    def trace_model_call(self, func: Callable) -> Callable:
        """Decorator for tracing model API calls.
        
        Args:
            func: Function to trace
            
        Returns:
            Wrapped function that logs trace data
        """
        async def wrapper(*args, **kwargs):
            # Trace request
            request_id = str(uuid.uuid4())
            start_time = time.time()
            
            # Log the request
            request_data = {
                "request_id": request_id,
                "model": kwargs.get("model", "unknown"),
                "params": {k: v for k, v in kwargs.items() if k != "messages"},
                "messages": kwargs.get("messages", [])
            }
            self.log_event("llm_request", request_data)
            
            try:
                # Call the original function
                response = await func(*args, **kwargs)
                
                # Calculate time taken
                end_time = time.time()
                duration = end_time - start_time
                
                # Log the response
                response_data = {
                    "request_id": request_id,
                    "duration_seconds": duration,
                    "success": True,
                    "model": kwargs.get("model", "unknown"),
                    "output": response.choices[0].message.content if hasattr(response, "choices") else str(response)
                }
                self.log_event("llm_response", response_data)
                
                return response
                
            except Exception as e:
                # Log the error
                end_time = time.time()
                duration = end_time - start_time
                
                error_data = {
                    "request_id": request_id,
                    "duration_seconds": duration,
                    "success": False,
                    "error": str(e)
                }
                self.log_event("llm_error", error_data)
                
                # Re-raise the exception
                raise
        
        return wrapper
    
    def get_trace_file_path(self) -> str:
        """Get the path to the trace file.
        
        Returns:
            Path to the trace file
        """
        return self.trace_file
    
    def cleanup(self) -> None:
        """Clean up resources used by the plugin."""
        # Unsubscribe from events
        for subscriber in self.event_subscribers:
            self.event_bus.unsubscribe(subscriber)
        
        # End the session
        end_time = datetime.now()
        duration = (end_time - self.session_start).total_seconds()
        
        session_end = {
            "type": "session_end",
            "timestamp": end_time.isoformat(),
            "session_id": self.session_id,
            "duration_seconds": duration
        }
        
        with open(self.trace_file, 'a') as f:
            f.write(json.dumps(session_end) + "\n")
        
        logger.info(f"LLM Tracing session {self.session_id} ended")