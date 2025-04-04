"""Agent facade module for Symphony.

This module provides a clean, domain-specific interface for working with
Symphony agents, abstracting away the details of the registry pattern
and other implementation details.
"""

from typing import Dict, List, Any, Optional, Set
from symphony.core.registry import ServiceRegistry
from symphony.core.agent_config import AgentConfig, AgentCapabilities

class AgentFacade:
    """Facade for working with Symphony agents.
    
    This class provides a clean interface for creating and managing agents,
    abstracting away the details of the registry pattern.
    """
    
    def __init__(self, registry: ServiceRegistry = None):
        """Initialize agent facade.
        
        Args:
            registry: Service registry instance (optional)
        """
        self.registry = registry or ServiceRegistry.get_instance()
    
    async def create_agent(self, 
                          name: str, 
                          role: str, 
                          instruction_template: str, 
                          capabilities: Dict[str, Any] = None,
                          model: str = None,
                          metadata: Dict[str, Any] = None) -> AgentConfig:
        """Create a new agent configuration.
        
        Args:
            name: Agent name
            role: Agent role description
            instruction_template: Base instruction template
            capabilities: Agent capabilities
            model: LLM model to use
            metadata: Additional metadata
            
        Returns:
            New agent configuration
        """
        # Convert dict capabilities to AgentCapabilities if needed
        agent_capabilities = None
        if capabilities:
            if isinstance(capabilities, dict):
                expertise = capabilities.get("expertise", [])
                agent_capabilities = AgentCapabilities(expertise=expertise)
            elif isinstance(capabilities, AgentCapabilities):
                agent_capabilities = capabilities
        else:
            agent_capabilities = AgentCapabilities()
        
        # Create agent config
        agent_config = AgentConfig(
            name=name,
            role=role,
            instruction_template=instruction_template,
            capabilities=agent_capabilities,
            model=model,
            metadata=metadata or {}
        )
        
        return agent_config
    
    async def save_agent(self, agent_config: AgentConfig) -> str:
        """Save an agent configuration.
        
        Args:
            agent_config: Agent configuration
            
        Returns:
            Agent configuration ID
        """
        try:
            agent_config_repo = self.registry.get_repository("agent_config")
            return await agent_config_repo.save(agent_config)
        except ValueError:
            # Repository might not be registered yet
            from symphony.persistence.memory_repository import InMemoryRepository
            agent_config_repo = InMemoryRepository(AgentConfig)
            self.registry.register_repository("agent_config", agent_config_repo)
            return await agent_config_repo.save(agent_config)
    
    async def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get an agent configuration by ID.
        
        Args:
            agent_id: Agent configuration ID
            
        Returns:
            Agent configuration or None if not found
        """
        try:
            agent_config_repo = self.registry.get_repository("agent_config")
            return await agent_config_repo.find_by_id(agent_id)
        except ValueError:
            return None
    
    async def get_agents_by_capability(self, capability: str) -> List[AgentConfig]:
        """Get agent configurations by capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of matching agent configurations
        """
        try:
            agent_config_repo = self.registry.get_repository("agent_config")
            all_agents = await agent_config_repo.find_all()
            return [
                agent for agent in all_agents
                if capability in agent.capabilities.expertise
            ]
        except ValueError:
            return []
    
    async def get_all_agents(self) -> List[AgentConfig]:
        """Get all agent configurations.
        
        Returns:
            List of all agent configurations
        """
        try:
            agent_config_repo = self.registry.get_repository("agent_config")
            return await agent_config_repo.find_all()
        except ValueError:
            return []
    
    async def update_agent(self, agent_config: AgentConfig) -> bool:
        """Update an agent configuration.
        
        Args:
            agent_config: Updated agent configuration
            
        Returns:
            True if the update was successful
        """
        try:
            agent_config_repo = self.registry.get_repository("agent_config")
            await agent_config_repo.update(agent_config)
            return True
        except ValueError:
            return False
    
    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent configuration.
        
        Args:
            agent_id: Agent configuration ID
            
        Returns:
            True if the deletion was successful
        """
        try:
            agent_config_repo = self.registry.get_repository("agent_config")
            await agent_config_repo.delete(agent_id)
            return True
        except ValueError:
            return False