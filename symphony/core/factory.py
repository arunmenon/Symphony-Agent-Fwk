"""Factory classes for creating Symphony components."""

from typing import Any, Dict, Optional, Type

from symphony.agents.base import AgentBase, AgentConfig, ReactiveAgent
from symphony.agents.planning import PlannerAgent
from symphony.llm.base import LLMClient, MockLLMClient
from symphony.llm.litellm_client import LiteLLMClient, LiteLLMConfig
from symphony.mcp.base import MCPManager, MCPConfig
from symphony.memory.base import BaseMemory, ConversationMemory, InMemoryMemory
from symphony.prompts.registry import PromptRegistry


class AgentFactory:
    """Factory for creating agent instances."""
    
    _agent_types: Dict[str, Type[AgentBase]] = {
        "reactive": ReactiveAgent,
        "planner": PlannerAgent,
    }
    
    @classmethod
    def register_agent_type(cls, name: str, agent_cls: Type[AgentBase]) -> None:
        """Register a new agent type."""
        cls._agent_types[name] = agent_cls
    
    @classmethod
    def create(
        cls,
        config: AgentConfig,
        llm_client: LLMClient,
        prompt_registry: PromptRegistry,
        memory: Optional[BaseMemory] = None,
        mcp_manager: Optional[MCPManager] = None,
    ) -> AgentBase:
        """Create an agent instance based on the agent type in config."""
        agent_type = config.agent_type.lower()
        
        if agent_type not in cls._agent_types:
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Available types: {', '.join(cls._agent_types.keys())}"
            )
            
        agent_cls = cls._agent_types[agent_type]
        
        return agent_cls(
            config=config,
            llm_client=llm_client,
            prompt_registry=prompt_registry,
            memory=memory,
            mcp_manager=mcp_manager
        )


class LLMClientFactory:
    """Factory for creating LLM client instances."""
    
    @classmethod
    def create_mock(cls, responses: Optional[Dict[str, str]] = None) -> MockLLMClient:
        """Create a mock LLM client for testing."""
        return MockLLMClient(responses=responses)
    
    @classmethod
    def create_from_litellm_config(cls, config: LiteLLMConfig) -> LiteLLMClient:
        """Create an LLM client using LiteLLM with the given configuration."""
        return LiteLLMClient(config=config)
    
    @classmethod
    def create_from_provider(
        cls,
        provider: str,
        model_name: str,
        api_key: Optional[str] = None,
        **kwargs: Any
    ) -> LiteLLMClient:
        """Create an LLM client for a specific provider and model."""
        # Combine provider and model
        model = f"{provider}/{model_name}"
        
        # Create config with provided parameters
        config = LiteLLMConfig(
            model=model,
            api_key=api_key,
            **kwargs
        )
        
        return cls.create_from_litellm_config(config)


class MemoryFactory:
    """Factory for creating memory instances."""
    
    _memory_types: Dict[str, Type[BaseMemory]] = {
        "in_memory": InMemoryMemory,
        "conversation": ConversationMemory,
    }
    
    @classmethod
    def register_memory_type(cls, name: str, memory_cls: Type[BaseMemory]) -> None:
        """Register a new memory type."""
        cls._memory_types[name] = memory_cls
    
    @classmethod
    def create(cls, memory_type: str, **kwargs: Any) -> BaseMemory:
        """Create a memory instance of the given type."""
        if memory_type not in cls._memory_types:
            raise ValueError(
                f"Unknown memory type: {memory_type}. "
                f"Available types: {', '.join(cls._memory_types.keys())}"
            )
            
        memory_cls = cls._memory_types[memory_type]
        return memory_cls(**kwargs)
    
    @classmethod
    def create_conversation_memory(cls) -> ConversationMemory:
        """Create a conversation memory instance."""
        return ConversationMemory()


class MCPManagerFactory:
    """Factory for creating MCP manager instances."""
    
    @classmethod
    def create(cls, config: Optional[MCPConfig] = None) -> MCPManager:
        """Create an MCP manager with the given configuration."""
        return MCPManager(config=config)