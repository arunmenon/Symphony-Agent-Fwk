"""Search Tracing Plugin for Taxonomy Planner.

This module provides a plugin for tracing search tool calls,
capturing search requests, responses, and performance metrics.
"""

import os
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable

from symphony.core.plugin import Plugin
from symphony.core.container import Container
from symphony.core.events import EventBus, Event

# Configure logging
logger = logging.getLogger(__name__)

class SearchTracingPlugin(Plugin):
    """Plugin for tracing search API calls."""
    
    @property
    def name(self) -> str:
        return "search_tracing_plugin"
    
    @property
    def version(self) -> str:
        return "0.1.0"
    
    @property
    def description(self) -> str:
        return "Adds tracing for search API calls in Taxonomy Planner"
    
    def __init__(self, trace_dir: str = "traces/taxonomy_generation"):
        """Initialize search tracing plugin.
        
        Args:
            trace_dir: Directory to store trace files
        """
        super().__init__()
        self.trace_dir = trace_dir
        self.session_id = str(uuid.uuid4())
        self.session_start = datetime.now()
        
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
        
        logger.info(f"Search Tracing enabled. Session ID: {self.session_id}")
        logger.info(f"Trace file: {self.trace_file}")
    
    def initialize(self, container: Container, event_bus: EventBus) -> None:
        """Initialize the plugin.
        
        Args:
            container: The service container
            event_bus: The event bus
        """
        self.container = container
        self.event_bus = event_bus
    
    def log_search_request(self, query: str, num_results: int, search_id: str) -> None:
        """Log a search request to the trace file.
        
        Args:
            query: Search query
            num_results: Number of requested results
            search_id: Unique ID for the search request
        """
        event = {
            "type": "search_request",
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "data": {
                "search_id": search_id,
                "query": query,
                "num_results": num_results
            }
        }
        
        with open(self.trace_file, 'a') as f:
            f.write(json.dumps(event) + "\n")
    
    def log_search_response(self, 
                           search_id: str, 
                           duration: float, 
                           results_count: int,
                           success: bool,
                           error: Optional[str] = None) -> None:
        """Log a search response to the trace file.
        
        Args:
            search_id: Unique ID for the search request
            duration: Time taken for the search in seconds
            results_count: Number of results returned
            success: Whether the search was successful
            error: Error message if unsuccessful
        """
        event = {
            "type": "search_response",
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "data": {
                "search_id": search_id,
                "duration_seconds": duration,
                "results_count": results_count,
                "success": success
            }
        }
        
        if error:
            event["data"]["error"] = error
        
        with open(self.trace_file, 'a') as f:
            f.write(json.dumps(event) + "\n")
    
    def trace_search_call(self, func: Callable) -> Callable:
        """Decorator for tracing search API calls.
        
        Args:
            func: Function to trace (serapi_search)
            
        Returns:
            Wrapped function that logs trace data
        """
        def wrapper(query: str, config: Any, num_results: int = 5):
            # Generate search ID
            search_id = f"search_{int(time.time())}"
            start_time = time.time()
            
            # Log the search request
            self.log_search_request(query, num_results, search_id)
            
            try:
                # Call the original function
                response = func(query, config, num_results)
                
                # Calculate time taken
                end_time = time.time()
                duration = end_time - start_time
                
                # Get result count
                results_count = len(response.get("organic_results", []))
                
                # Log the search response
                self.log_search_response(
                    search_id=search_id,
                    duration=duration,
                    results_count=results_count,
                    success=True
                )
                
                return response
                
            except Exception as e:
                # Log the search error
                end_time = time.time()
                duration = end_time - start_time
                
                self.log_search_response(
                    search_id=search_id,
                    duration=duration,
                    results_count=0,
                    success=False,
                    error=str(e)
                )
                
                # Re-raise the exception
                raise
        
        return wrapper
    
    def cleanup(self) -> None:
        """Clean up resources used by the plugin."""
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
        
        logger.info(f"Search Tracing session {self.session_id} ended")

# Function to get a decorated search function
def get_traced_search_function(original_search_fn, plugin):
    """Get a search function that's traced by the plugin.
    
    Args:
        original_search_fn: Original search function
        plugin: Search tracing plugin
        
    Returns:
        Traced search function
    """
    return plugin.trace_search_call(original_search_fn)