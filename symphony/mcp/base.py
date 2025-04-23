"""Model Context Protocol (MCP) integration for dynamic context assembly.

This module integrates Symphony with the official Model Context Protocol (MCP),
allowing agents to leverage standardized context management.
"""

import asyncio
from typing import Any, Dict, List, Optional, Protocol, Union

try:
    from mcp.server.fastmcp import FastMCP, Context
except ImportError:
    # Define minimal MCP classes for when MCP is not installed
    class Context:
        """Minimal Context implementation when MCP is not available."""
        def __init__(self, state=None):
            self.state = state or {}
    
    class FastMCP:
        """Minimal FastMCP implementation when MCP is not available."""
        def __init__(self, app_name):
            self.app_name = app_name
            
        def resource(self, path):
            """Stub decorator for resource registration."""
            def decorator(func):
                return func
            return decorator
            
        def tool(self, name=None, description=None):
            """Stub decorator for tool registration."""
            def decorator(func):
                return func
            return decorator
from pydantic import BaseModel, Field

from symphony.utils.types import Message


class MCPConfig(BaseModel):
    """Configuration for MCP integration."""
    
    app_name: str = "Symphony Framework"
    resource_prefix: str = "symphony"


class MCPManager:
    """Manager for MCP resources and tools integration."""
    
    def __init__(self, config: Optional[MCPConfig] = None):
        """Initialize the MCP manager with configuration."""
        self.config = config or MCPConfig()
        self.mcp = FastMCP(self.config.app_name)
        self._resource_prefix = self.config.resource_prefix
        self._setup_resources()
    
    def _setup_resources(self) -> None:
        """Set up standard MCP resources for Symphony."""
        
        @self.mcp.resource(f"{self._resource_prefix}://system-prompt")
        def get_system_prompt(ctx: Context) -> str:
            """Return the current system prompt."""
            # This will be populated by the agent when running
            return ctx.state.get("system_prompt", "You are a helpful assistant.")
        
        @self.mcp.resource(f"{self._resource_prefix}://conversation-history")
        def get_conversation_history(ctx: Context) -> List[Dict[str, Any]]:
            """Return the conversation history."""
            # This will be populated by the agent when running
            return ctx.state.get("conversation_history", [])
        
        @self.mcp.resource(f"{self._resource_prefix}://agent-state/{id}")
        def get_agent_state(id: str, ctx: Context) -> Dict[str, Any]:
            """Return state for a specific agent."""
            agent_states = ctx.state.get("agent_states", {})
            return agent_states.get(id, {})
    
    def register_resource(self, resource_path: str, handler: Any) -> None:
        """Register a custom resource with MCP."""
        self.mcp.resource(resource_path)(handler)
    
    def register_tool(self, name: Optional[str] = None, description: Optional[str] = None):
        """Register a Symphony tool as an MCP tool."""
        return self.mcp.tool(name=name, description=description)
    
    def get_context(self) -> Context:
        """Get a new MCP context object."""
        return Context(state={})
    
    def update_context_state(self, ctx: Context, key: str, value: Any) -> None:
        """Update a value in the context state."""
        ctx.state[key] = value
    
    def prepare_agent_context(
        self, 
        ctx: Context, 
        system_prompt: str,
        messages: List[Message],
        agent_id: str,
        agent_state: Dict[str, Any]
    ) -> Context:
        """Prepare context for an agent run."""
        # Convert Symphony messages to MCP-compatible format
        conversation_history = [
            {"role": msg.role, "content": msg.content, **msg.additional_kwargs}
            for msg in messages
        ]
        
        # Update context state
        ctx.state["system_prompt"] = system_prompt
        ctx.state["conversation_history"] = conversation_history
        
        # Update agent state
        agent_states = ctx.state.get("agent_states", {})
        agent_states[agent_id] = agent_state
        ctx.state["agent_states"] = agent_states
        
        return ctx
    
    def get_mcp_server(self) -> FastMCP:
        """Get the underlying MCP server instance."""
        return self.mcp