"""Base agent interfaces and implementations."""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Type, Union

from pydantic import BaseModel, Field

from symphony.llm.base import LLMClient
from symphony.mcp.base import ContextComposer, ContextComposerConfig
from symphony.memory.base import BaseMemory, ConversationMemory
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import Tool, ToolRegistry
from symphony.utils.types import ContextItem, Message


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    
    name: str
    agent_type: str
    description: Optional[str] = None
    system_prompt_type: str = "system"
    max_tokens: int = 4000
    memory_cls: Optional[Type[BaseMemory]] = None
    tools: List[str] = Field(default_factory=list)
    context_composer_config: Optional[ContextComposerConfig] = None


class AgentBase(ABC):
    """Base class for all agents."""
    
    def __init__(
        self,
        config: AgentConfig,
        llm_client: LLMClient,
        prompt_registry: PromptRegistry,
        memory: Optional[BaseMemory] = None,
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
        
        # Initialize context composer
        self.context_composer = ContextComposer(config.context_composer_config)
        
        # Load system prompt
        self._load_system_prompt()
    
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
        
        # Get context from memory
        context_items = self._get_context_items()
        
        # Assemble context using MCP
        messages = self.context_composer.assemble_context(
            system_prompt=self.system_prompt,
            context_items=context_items
        )
        
        # Call LLM
        response = await self.decide_action(messages)
        
        # Add response to memory
        if isinstance(self.memory, ConversationMemory):
            self.memory.add_message(response)
            
        return response.content
    
    def _get_context_items(self) -> List[ContextItem]:
        """Get context items from memory and other sources."""
        items: List[ContextItem] = []
        
        # Get conversation history if available
        if isinstance(self.memory, ConversationMemory):
            items.extend(self.memory.to_context_items())
        
        # Add tool descriptions if any
        if self.tools:
            tool_descriptions = "\n".join([
                f"- {name}: {tool.description}" 
                for name, tool in self.tools.items()
            ])
            items.append(ContextItem(
                content=f"You have access to the following tools:\n{tool_descriptions}",
                importance=1.5,  # Higher importance for tools
                metadata={"type": "tools"}
            ))
        
        return items
    
    @abstractmethod
    async def decide_action(self, messages: List[Message]) -> Message:
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
    
    async def decide_action(self, messages: List[Message]) -> Message:
        """Decide what action to take given the current context."""
        # For a reactive agent, just call the LLM directly
        return await self.llm_client.chat(messages)