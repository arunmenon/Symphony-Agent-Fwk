"""Base agent interfaces and implementations."""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Type, Union

from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field

from symphony.llm.base import LLMClient
from symphony.mcp.base import MCPManager
from symphony.memory.base import BaseMemory, ConversationMemory
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import Tool, ToolRegistry
from symphony.utils.types import Message


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    
    name: str
    agent_type: str
    description: Optional[str] = None
    system_prompt_type: str = "system"
    max_tokens: int = 4000
    memory_cls: Optional[Type[BaseMemory]] = None
    tools: List[str] = Field(default_factory=list)
    mcp_enabled: bool = True


class AgentBase(ABC):
    """Base class for all agents."""
    
    def __init__(
        self,
        config: AgentConfig,
        llm_client: LLMClient,
        prompt_registry: PromptRegistry,
        memory: Optional[BaseMemory] = None,
        mcp_manager: Optional[MCPManager] = None,
    ):
        self.id = str(uuid.uuid4())
        self.config = config
        self.llm_client = llm_client
        self.prompt_registry = prompt_registry
        
        # Initialize memory
        memory_cls = config.memory_cls or ConversationMemory
        self.memory = memory or memory_cls()
        
        # Load tools
        self.tools: Dict[str, Tool] = {}
        for tool_name in config.tools:
            tool = ToolRegistry.get(tool_name)
            if tool:
                self.tools[tool_name] = tool
        
        # Initialize MCP
        self.mcp_manager = mcp_manager or MCPManager()
        
        # Register tools with MCP if enabled
        if self.config.mcp_enabled:
            self._register_tools_with_mcp()
        
        # Load system prompt
        self._load_system_prompt()
    
    def _register_tools_with_mcp(self) -> None:
        """Register Symphony tools with MCP."""
        for name, tool in self.tools.items():
            @self.mcp_manager.register_tool(name=name, description=tool.description)
            def tool_handler(ctx: Context, **kwargs: Any) -> Any:
                return tool(**kwargs)
    
    def _load_system_prompt(self) -> None:
        """Load the system prompt from the registry."""
        prompt_template = self.prompt_registry.get_prompt(
            prompt_type=self.config.system_prompt_type,
            agent_type=self.config.agent_type,
            agent_instance=self.config.name
        )
        
        if prompt_template:
            self.system_prompt = prompt_template.content
        else:
            # Default system prompt if none found
            self.system_prompt = (
                f"You are {self.config.name}, a helpful AI assistant. "
                f"{self.config.description or ''}"
            )
    
    async def run(self, input_message: str) -> str:
        """Run the agent on an input message and return a response."""
        # Create message and add to memory
        message = Message(role="user", content=input_message)
        if isinstance(self.memory, ConversationMemory):
            self.memory.add_message(message)
        
        # Get messages from memory
        messages = (
            self.memory.get_messages() 
            if isinstance(self.memory, ConversationMemory) 
            else [message]
        )
        
        # If using MCP, prepare context
        mcp_context = None
        if self.config.mcp_enabled:
            mcp_context = self.mcp_manager.get_context()
            agent_state = self._get_agent_state()
            mcp_context = self.mcp_manager.prepare_agent_context(
                ctx=mcp_context,
                system_prompt=self.system_prompt,
                messages=messages,
                agent_id=self.id,
                agent_state=agent_state
            )
        
        # Call decide_action with or without MCP context
        response = await self.decide_action(messages, mcp_context)
        
        # Add response to memory
        if isinstance(self.memory, ConversationMemory):
            self.memory.add_message(response)
            
        return response.content
    
    def _get_agent_state(self) -> Dict[str, Any]:
        """Get the current agent state for MCP context."""
        state = {
            "id": self.id,
            "name": self.config.name,
            "agent_type": self.config.agent_type
        }
        
        # Add tools info
        if self.tools:
            state["tools"] = [
                {"name": name, "description": tool.description}
                for name, tool in self.tools.items()
            ]
            
        return state
    
    @abstractmethod
    async def decide_action(
        self, 
        messages: List[Message], 
        mcp_context: Optional[Context] = None
    ) -> Message:
        """Decide what action to take given the current context."""
        pass
    
    async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Call a tool by name with the given arguments."""
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        return await asyncio.to_thread(tool, **kwargs)


class ReactiveAgent(AgentBase):
    """A simple reactive agent that responds to messages directly."""
    
    async def decide_action(
        self, 
        messages: List[Message], 
        mcp_context: Optional[Context] = None
    ) -> Message:
        """Decide what action to take given the current context."""
        # For a reactive agent, just call the LLM directly
        # If using MCP, we'd provide the context to the LLM client
        if mcp_context is not None and self.config.mcp_enabled:
            # In a real implementation, the LLM client would use the MCP context
            return await self.llm_client.chat_with_mcp(messages, mcp_context)
        else:
            return await self.llm_client.chat(messages)


class Agent:
    """Simplified Agent class for testing."""
    
    def __init__(self, name="TestAgent", description="", system_prompt="You are a helpful assistant.", model="gpt-4", **kwargs):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.model = model
        
        # Store any additional attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    async def run(self, query: str) -> str:
        """Run the agent on a query and return a response."""
        return f"Response to: {query}"