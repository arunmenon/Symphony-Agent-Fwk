"""Factory classes for creating Symphony components."""

from typing import Any, Dict, Optional, Type, Union

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
        model_name: str = None,  # Default will be set based on provider
        api_key: Optional[str] = None,
        **kwargs: Any
    ) -> LiteLLMClient:
        """Create an LLM client for a specific provider and model.
        
        Args:
            provider: The provider name (e.g., "openai", "anthropic")
            model_name: The model name (if not provided, will use provider's recommended model)
            api_key: Optional API key (will use env var if not provided)
            **kwargs: Additional configuration parameters
            
        Returns:
            Configured LLM client
            
        Note:
            For memory importance assessment and other reasoning tasks, advanced language
            models with strong reasoning capabilities are recommended for optimal results.
        """
        # Set default model per provider if not specified
        if model_name is None:
            if provider.lower() == "openai":
                model_name = "gpt-4"
            elif provider.lower() == "anthropic":
                model_name = "claude-3-opus"
            else:
                # Generic default for other providers
                model_name = "default"
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
    """Factory for creating memory system instances.
    
    This factory supports creating various types of memory systems:
    
    Basic Memory Types:
    - "in_memory": Simple key-value storage (InMemoryMemory)
    - "conversation": Basic conversation history storage (ConversationMemory)
    
    Advanced Memory Types:
    - "working_memory": Short-term memory with automatic expiration (WorkingMemory)
    - "memory_manager": Centralized manager for multiple memory tiers (MemoryManager) 
    - "conversation_manager": Advanced conversation memory with importance assessment (ConversationMemoryManager)
    
    The factory integrates with domain-specific importance strategies to customize 
    how different types of information are prioritized for memory storage.
    """
    
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
        # Check for advanced memory manager types
        if memory_type == "memory_manager" or memory_type == "working_memory":
            # Import here to avoid circular imports
            from symphony.memory.memory_manager import MemoryManager, WorkingMemory
            
            if memory_type == "memory_manager":
                return MemoryManager(**kwargs)
            else:
                return WorkingMemory(**kwargs)
                
        elif memory_type == "conversation_manager":
            # Import here to avoid circular imports
            from symphony.memory.memory_manager import ConversationMemoryManager
            
            # Check if an importance strategy was specified
            if "importance_strategy_type" in kwargs:
                from symphony.memory.strategy_factory import ImportanceStrategyFactory
                
                strategy_type = kwargs.pop("importance_strategy_type")
                strategy_params = kwargs.pop("strategy_params", {})
                
                # Create the strategy using the factory
                importance_strategy = ImportanceStrategyFactory.create_strategy(
                    strategy_type, **strategy_params
                )
                
                # Add to kwargs
                kwargs["importance_strategy"] = importance_strategy
                
            return ConversationMemoryManager(**kwargs)
            
        # Fall back to basic memory types
        if memory_type not in cls._memory_types:
            raise ValueError(
                f"Unknown memory type: {memory_type}. "
                f"Available types: memory_manager, working_memory, conversation_manager, "
                f"{', '.join(cls._memory_types.keys())}"
            )
            
        memory_cls = cls._memory_types[memory_type]
        return memory_cls(**kwargs)
    
    @classmethod
    def create_conversation_memory(cls) -> ConversationMemory:
        """Create a conversation memory instance."""
        return ConversationMemory()
        
    @classmethod
    def create_conversation_manager(
        cls, 
        importance_strategy_type: Optional[str] = "rule", 
        **kwargs: Any
    ) -> BaseMemory:
        """Create a conversation memory manager with the specified importance strategy.
        
        This convenience method makes it easy to create a ConversationMemoryManager
        with a specific importance assessment strategy.
        
        Args:
            importance_strategy_type: Type of importance strategy to use:
                - Basic types: "rule", "llm", "hybrid"
                - Domain-specific: "customer_support", "product_research", 
                  "personal_assistant", "educational", "medical"
                - Hybrid domain: "hybrid_customer_support", "hybrid_educational", etc.
            **kwargs: Additional parameters including:
                - strategy_params: Dict of parameters for the strategy (e.g., 
                  llm_client, action_keywords, subjects, etc.)
                - memory_thresholds: Dict of thresholds for memory tiers (e.g.,
                  {"long_term": 0.7, "kg": 0.8})
                
        Returns:
            Configured ConversationMemoryManager with specified importance strategy
            
        Example:
            ```python
            # Create memory manager with educational strategy
            memory = MemoryFactory.create_conversation_manager(
                importance_strategy_type="educational",
                strategy_params={
                    "subjects": ["physics", "math"],
                    "learning_level": "advanced"
                },
                memory_thresholds={"long_term": 0.6, "kg": 0.8}
            )
            ```
        """
        return cls.create(
            "conversation_manager", 
            importance_strategy_type=importance_strategy_type,
            strategy_params=kwargs.get("strategy_params", {}),
            **{k: v for k, v in kwargs.items() if k != "strategy_params"}
        )


class MCPManagerFactory:
    """Factory for creating MCP manager instances."""
    
    @classmethod
    def create(cls, config: Optional[MCPConfig] = None) -> MCPManager:
        """Create an MCP manager with the given configuration."""
        return MCPManager(config=config)