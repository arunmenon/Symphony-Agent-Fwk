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
    
    async def create_agent(self, config_id: str = None, agent_type: str = None, model: str = None, **kwargs) -> Agent:
        """Create agent instance from stored configuration, type, or specified parameters.
        
        This method supports multiple ways to create an agent:
        1. By config_id: Load configuration from repository
        2. By agent_type: Find configuration by type
        3. By parameters: Create with provided parameters
        
        Args:
            config_id: ID of the agent configuration to use
            agent_type: Type of agent to create (if config_id not provided)
            model: Model to use for the agent (overrides config)
            **kwargs: Additional parameters to pass to the agent constructor
            
        Returns:
            Agent instance
            
        Raises:
            ValueError: If insufficient information is provided to create agent
        """
        config = None
        agent_kwargs = {}
        
        # First try to get config by ID
        if config_id and self.repository:
            config = await self.repository.find_by_id(config_id)
            if not config:
                raise ValueError(f"Agent configuration {config_id} not found")
        
        # If config_id not provided but agent_type is, try to find by type
        elif agent_type and self.repository:
            # We need to implement or replace this with actual query logic
            # For now, we'll just use a direct find if repository has a find_by_type method
            if hasattr(self.repository, 'find_by_type'):
                config = await self.repository.find_by_type(agent_type)
            elif hasattr(self.repository, 'find'):
                # Try using a generic find method with a filter
                configs = await self.repository.find({"role": agent_type})
                if configs and len(configs) > 0:
                    config = configs[0]
        
        # If we have a config, use it to initialize agent_kwargs
        if config:
            agent_kwargs = {
                "name": config.name,
                "description": config.description,
                "system_prompt": config.instruction_template,
                "model": config.config.get("model", "gpt-4"),
            }
        
        # If no config but we have agent_type, use default settings
        elif agent_type:
            agent_kwargs = {
                "name": agent_type.capitalize() + " Agent",
                "description": f"A {agent_type} agent",
                "system_prompt": f"You are a {agent_type} agent. Assist the user with {agent_type} tasks.",
                "model": "gpt-4"  # Default model
            }
            
        # If we have neither config nor agent_type, raise error
        else:
            raise ValueError("Either config_id or agent_type must be provided")
            
        # Apply model override if specified
        if model:
            agent_kwargs["model"] = model
            
        # Add any additional kwargs
        agent_kwargs.update(kwargs)
        
        # Create agent instance
        return Agent(**agent_kwargs)
    
    async def create_agent_from_id(self, agent_id: str, model: str = None, **kwargs) -> Agent:
        """Create agent from stored configuration by ID.
        
        This is a convenience method that calls create_agent with the config_id.
        
        Args:
            agent_id: ID of the agent configuration
            model: Optional model override
            **kwargs: Additional parameters for agent creation
            
        Returns:
            Agent instance
        """
        return await self.create_agent(config_id=agent_id, model=model, **kwargs)
    
    async def create_typed_agent(self, agent_type: str, model: str = None, **kwargs) -> Agent:
        """Create an agent of a specific type.
        
        This is a convenience method that wraps create_agent with just the agent_type.
        
        Args:
            agent_type: Type of agent to create (e.g., "planner", "explorer")
            model: Optional model to use
            **kwargs: Additional parameters for agent creation
            
        Returns:
            Agent instance
        """
        return await self.create_agent(agent_type=agent_type, model=model, **kwargs)
    
    # Add specific agent creator methods for common types
    async def create_planner_agent(self, model: str = None, **kwargs) -> Agent:
        """Create a planner agent."""
        return await self.create_typed_agent("planner", model, **kwargs)
        
    async def create_explorer_agent(self, model: str = None, **kwargs) -> Agent:
        """Create an explorer agent."""
        return await self.create_typed_agent("explorer", model, **kwargs)
        
    async def create_compliance_agent(self, model: str = None, **kwargs) -> Agent:
        """Create a compliance agent."""
        return await self.create_typed_agent("compliance", model, **kwargs)
        
    async def create_legal_agent(self, model: str = None, **kwargs) -> Agent:
        """Create a legal agent."""
        return await self.create_typed_agent("legal", model, **kwargs)
    
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