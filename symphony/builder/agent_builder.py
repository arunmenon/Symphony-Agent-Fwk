"""Agent builder for Symphony.

This module provides a fluent interface for building Symphony agents.
"""

from typing import Dict, List, Any, Optional, Set
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.core.agent_config import AgentConfig, AgentCapabilities

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
        
        return self
    
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