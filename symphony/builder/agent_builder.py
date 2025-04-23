"""Agent builder for Symphony.

This module provides a fluent interface for building Symphony agents.
"""

from typing import Dict, List, Any, Optional, Set, Union
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.memory.importance import ImportanceStrategy, RuleBasedStrategy
from symphony.memory.memory_manager import MemoryManager, ConversationMemoryManager, WorkingMemory
from symphony.memory.vector_memory import VectorMemory
from symphony.memory.local_kg_memory import LocalKnowledgeGraphMemory
from symphony.memory.strategy_factory import ImportanceStrategyFactory

class AgentBuilder:
    """Builder for Symphony agents.
    
    This class provides a fluent interface for building agents, making it
    easier to create complex agent configurations with a clean, readable syntax.
    """
    
    def __init__(self, registry: ServiceRegistry = None):
        """Initialize agent builder.
        
        Args:
            registry: Service registry instance (optional)
        """
        self.registry = registry or ServiceRegistry.get_instance()
        self.agent_config: Optional[AgentConfig] = None
        self.capabilities_list: List[str] = []
        self.model_name: Optional[str] = None
        self.metadata_dict: Dict[str, Any] = {}
        
        # Memory configuration
        self.memory_manager: Optional[MemoryManager] = None
        self.memory_type: str = "conversation"  # Default memory type
        self.importance_strategy: Optional[ImportanceStrategy] = None
        self.memory_thresholds: Dict[str, float] = {}
        self.use_kg_memory: bool = False
        
    def create(self, name: str, role: str, instruction_template: str) -> 'AgentBuilder':
        """Create a new agent configuration.
        
        Args:
            name: Agent name
            role: Agent role description
            instruction_template: Base instruction template
            
        Returns:
            Self for chaining
        """
        # Initialize with basic info, will add capabilities later
        self.agent_config = AgentConfig(
            name=name,
            role=role,
            instruction_template=instruction_template,
            capabilities=AgentCapabilities(expertise=[]),
            metadata={}
        )
        return self
    
    # Compatibility methods matching the test API
    def name(self, name: str) -> 'AgentBuilder':
        """Set the agent name.
        
        Args:
            name: Agent name
            
        Returns:
            Self for chaining
        """
        if self.agent_config is None:
            # Initialize with minimal defaults
            self.agent_config = AgentConfig(
                name=name,
                role="",
                instruction_template="You are a helpful assistant.",
                capabilities=AgentCapabilities(expertise=[]),
                metadata={}
            )
        else:
            # Update existing config
            self.agent_config.name = name
        return self
        
    def description(self, description: str) -> 'AgentBuilder':
        """Set the agent description/role.
        
        Args:
            description: Agent description or role
            
        Returns:
            Self for chaining
        """
        if self.agent_config is None:
            # Initialize with minimal defaults
            self.agent_config = AgentConfig(
                name="Assistant",
                role=description,
                instruction_template="You are a helpful assistant.",
                capabilities=AgentCapabilities(expertise=[]),
                metadata={}
            )
        else:
            # Update existing config
            self.agent_config.role = description
        return self
    
    def with_capability(self, capability: str) -> 'AgentBuilder':
        """Add a capability to the agent.
        
        Args:
            capability: Capability to add
            
        Returns:
            Self for chaining
        """
        if capability not in self.capabilities_list:
            self.capabilities_list.append(capability)
        
        # Update agent config if it exists
        if self.agent_config:
            self.agent_config.capabilities.expertise = self.capabilities_list
        
        return self
    
    def with_capabilities(self, capabilities: List[str]) -> 'AgentBuilder':
        """Add multiple capabilities to the agent.
        
        Args:
            capabilities: List of capabilities to add
            
        Returns:
            Self for chaining
        """
        for capability in capabilities:
            if capability not in self.capabilities_list:
                self.capabilities_list.append(capability)
        
        # Update agent config if it exists
        if self.agent_config:
            self.agent_config.capabilities.expertise = self.capabilities_list
        
        return self
    
    def with_model(self, model_name: str) -> 'AgentBuilder':
        """Set the model to use for this agent.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Self for chaining
        """
        self.model_name = model_name
        
        # Update agent config if it exists
        if self.agent_config:
            self.agent_config.model = model_name
        
        return self
    
    def with_metadata(self, key: str, value: Any) -> 'AgentBuilder':
        """Add metadata to the agent.
        
        Args:
            key: Metadata key
            value: Metadata value
            
        Returns:
            Self for chaining
        """
        self.metadata_dict[key] = value
        
        # Update agent config if it exists
        if self.agent_config:
            self.agent_config.metadata[key] = value
            
    def with_tools(self, tool_names: List[str]) -> 'AgentBuilder':
        """Add tools to the agent.
        
        Args:
            tool_names: List of tool names to add
            
        Returns:
            Self for chaining
        """
        # Store tools in metadata
        if 'tools' not in self.metadata_dict:
            self.metadata_dict['tools'] = []
            
        self.metadata_dict['tools'].extend(tool_names)
        
        # Update agent config if it exists
        if self.agent_config:
            if 'tools' not in self.agent_config.metadata:
                self.agent_config.metadata['tools'] = []
            self.agent_config.metadata['tools'].extend(tool_names)
        
        return self
    
    def with_memory_type(self, memory_type: str) -> 'AgentBuilder':
        """Set the type of memory system to use.
        
        Args:
            memory_type: Type of memory ("basic", "conversation", "custom")
            
        Returns:
            Self for chaining
        """
        self.memory_type = memory_type
        return self
        
    def with_memory_importance_strategy(self, strategy_type: str, **kwargs) -> 'AgentBuilder':
        """Set the importance calculation strategy for memory.
        
        Args:
            strategy_type: Type of strategy
                Basic types: "rule", "llm", "hybrid"
                Domain-specific: "customer_support", "product_research", 
                "personal_assistant", "educational", "medical"
                Hybrid domain: "hybrid_customer_support", "hybrid_product_research", etc.
            **kwargs: Additional parameters for the strategy
            
        Returns:
            Self for chaining
        """
        try:
            # Use the factory to create the appropriate strategy
            self.importance_strategy = ImportanceStrategyFactory.create_strategy(
                strategy_type, **kwargs
            )
        except ValueError as e:
            # Re-raise with additional context
            raise ValueError(f"Failed to create importance strategy: {str(e)}")
            
        return self
        
    def with_memory_thresholds(self, long_term: float = 0.7, kg: float = 0.8) -> 'AgentBuilder':
        """Set the memory importance thresholds.
        
        Args:
            long_term: Threshold for long-term memory storage (0.0-1.0)
            kg: Threshold for knowledge graph storage (0.0-1.0)
            
        Returns:
            Self for chaining
        """
        self.memory_thresholds = {"long_term": long_term, "kg": kg}
        return self
        
    def with_knowledge_graph(self, enabled: bool = True) -> 'AgentBuilder':
        """Enable or disable knowledge graph memory.
        
        Args:
            enabled: Whether to use knowledge graph memory
            
        Returns:
            Self for chaining
        """
        self.use_kg_memory = enabled
        return self
        
    def with_custom_memory(self, memory_manager: MemoryManager) -> 'AgentBuilder':
        """Set a custom memory manager.
        
        Args:
            memory_manager: Custom memory manager instance
            
        Returns:
            Self for chaining
        """
        self.memory_manager = memory_manager
        return self
        
    def _create_memory_manager(self, llm_client=None) -> MemoryManager:
        """Create a memory manager based on configuration.
        
        Args:
            llm_client: Optional LLM client for KG memory
            
        Returns:
            Configured memory manager
        """
        # Use custom memory manager if provided
        if self.memory_manager:
            return self.memory_manager
            
        # Create base memory components
        working_memory = WorkingMemory()
        long_term_memory = VectorMemory()
        
        # Create knowledge graph memory if enabled
        kg_memory = None
        if self.use_kg_memory and llm_client:
            kg_memory = LocalKnowledgeGraphMemory(
                llm_client=llm_client,
                auto_extract=True
            )
            
        # Create appropriate memory manager type
        if self.memory_type == "conversation":
            return ConversationMemoryManager(
                working_memory=working_memory,
                long_term_memory=long_term_memory,
                kg_memory=kg_memory,
                importance_strategy=self.importance_strategy,
                memory_thresholds=self.memory_thresholds
            )
        else:
            return MemoryManager(
                working_memory=working_memory,
                long_term_memory=long_term_memory,
                kg_memory=kg_memory,
                importance_strategy=self.importance_strategy,
                memory_thresholds=self.memory_thresholds
            )
    
    def build(self) -> AgentConfig:
        """Build the agent configuration.
        
        Returns:
            Agent configuration
        """
        if not self.agent_config:
            raise ValueError("Agent not created. Call create() first.")
        
        # Apply all accumulated settings to ensure they're all set
        self.agent_config.capabilities.expertise = self.capabilities_list
        self.agent_config.model = self.model_name
        self.agent_config.metadata = self.metadata_dict
        
        # Add memory configuration to metadata
        self.agent_config.metadata["memory_type"] = self.memory_type
        self.agent_config.metadata["use_kg_memory"] = self.use_kg_memory
        if self.memory_thresholds:
            self.agent_config.metadata["memory_thresholds"] = self.memory_thresholds
        
        return self.agent_config
    
    async def save(self) -> str:
        """Save the agent configuration.
        
        Returns:
            Agent configuration ID
        """
        if not self.agent_config:
            raise ValueError("Agent not created. Call create() first.")
        
        try:
            agent_config_repo = self.registry.get_repository("agent_config")
            return await agent_config_repo.save(self.agent_config)
        except ValueError:
            # Repository might not be registered yet
            from symphony.persistence.memory_repository import InMemoryRepository
            agent_config_repo = InMemoryRepository(AgentConfig)
            self.registry.register_repository("agent_config", agent_config_repo)
            return await agent_config_repo.save(self.agent_config)