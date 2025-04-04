"""Agent factory for creating agents from configurations.

This module provides a factory for creating agent instances from stored
configurations. It allows agent definitions to be decoupled from their
runtime implementations.
"""

from typing import Optional, Dict, Any, List
from symphony.agents.base import Agent
from symphony.core.agent_config import AgentConfig
from symphony.persistence.repository import Repository

class AgentFactory:
    """Factory for creating agents from configuration.
    
    The agent factory creates agent instances from stored configurations.
    It provides a layer of abstraction between agent definitions and
    their runtime implementations.
    """
    
    def __init__(self, repository: Optional[Repository[AgentConfig]] = None):
        """Initialize agent factory with repository.
        
        Args:
            repository: Repository for agent configurations
        """
        self.repository = repository
    
    async def create_agent(self, config_id: str, **kwargs) -> Agent:
        """Create agent instance from stored configuration.
        
        Args:
            config_id: ID of the agent configuration to use
            **kwargs: Additional parameters to pass to the agent constructor
            
        Returns:
            Agent instance
            
        Raises:
            ValueError: If repository is not configured or config not found
        """
        if not self.repository:
            raise ValueError("Repository not configured")
            
        config = await self.repository.find_by_id(config_id)
        if not config:
            raise ValueError(f"Agent configuration {config_id} not found")
        
        # Create agent from config
        agent_kwargs = {
            "name": config.name,
            "description": config.description,
            "system_prompt": config.instruction_template,
            "model": config.config.get("model", "gpt-4"),
        }
        
        # Add any additional kwargs
        agent_kwargs.update(kwargs)
        
        # Create agent instance
        return Agent(**agent_kwargs)
    
    async def save_agent_config(self, agent: Agent) -> str:
        """Save agent configuration based on agent instance.
        
        Args:
            agent: Agent instance to save configuration for
            
        Returns:
            ID of the saved configuration
            
        Raises:
            ValueError: If repository is not configured
        """
        if not self.repository:
            raise ValueError("Repository not configured")
            
        config = AgentConfig(
            name=agent.name,
            description=getattr(agent, "description", ""),
            instruction_template=agent.system_prompt,
            config={"model": agent.model}
        )
        
        return await self.repository.save(config)