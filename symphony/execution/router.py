"""Task routing system for Symphony.

This module provides a routing system for directing tasks to appropriate agents
based on task content, agent capabilities, and routing strategies.
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set, Tuple, Union

from symphony.agents.base import Agent
from symphony.core.agent_config import AgentConfig
from symphony.core.task import Task
from symphony.persistence.repository import Repository


class RoutingStrategy(str, Enum):
    """Strategies for routing tasks to agents."""
    ROUND_ROBIN = "round_robin"  # Distribute tasks evenly among agents
    CAPABILITY_MATCH = "capability_match"  # Match based on agent capabilities
    CONTENT_MATCH = "content_match"  # Match based on task content
    LOAD_BALANCED = "load_balanced"  # Route to least busy agent
    CUSTOM = "custom"  # Custom routing logic


class TaskRouter:
    """Routes tasks to appropriate agents.
    
    The task router is responsible for determining which agent should handle
    a specific task based on various routing strategies.
    """
    
    def __init__(self, 
                 agent_config_repository: Repository[AgentConfig],
                 strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_MATCH):
        """Initialize task router with repository and strategy.
        
        Args:
            agent_config_repository: Repository for agent configurations
            strategy: Routing strategy to use
        """
        self.agent_config_repository = agent_config_repository
        self.strategy = strategy
        self.current_agent_index = 0
        self.custom_router = None
        self.agent_load: Dict[str, int] = {}  # agent_id -> current load
    
    def set_strategy(self, strategy: RoutingStrategy) -> None:
        """Set the routing strategy.
        
        Args:
            strategy: New routing strategy
        """
        self.strategy = strategy
    
    def set_custom_router(self, router_func: Callable[[Task, List[AgentConfig]], Optional[str]]) -> None:
        """Set a custom router function.
        
        Args:
            router_func: Function that takes a task and list of agent configs,
                         and returns an agent ID or None
        """
        self.custom_router = router_func
        self.strategy = RoutingStrategy.CUSTOM
    
    async def route_task(self, task: Task) -> Optional[str]:
        """Route a task to an appropriate agent.
        
        Args:
            task: Task to route
            
        Returns:
            ID of the agent config to use, or None if no match
        """
        # Get all agent configs
        agent_configs = await self.agent_config_repository.find_all()
        
        if not agent_configs:
            return None
        
        # Route based on strategy
        if self.strategy == RoutingStrategy.ROUND_ROBIN:
            agent_config = agent_configs[self.current_agent_index % len(agent_configs)]
            self.current_agent_index += 1
            return agent_config.id
            
        elif self.strategy == RoutingStrategy.CAPABILITY_MATCH:
            return await self._route_by_capability(task, agent_configs)
            
        elif self.strategy == RoutingStrategy.CONTENT_MATCH:
            return await self._route_by_content(task, agent_configs)
            
        elif self.strategy == RoutingStrategy.LOAD_BALANCED:
            return await self._route_by_load(agent_configs)
            
        elif self.strategy == RoutingStrategy.CUSTOM and self.custom_router:
            return self.custom_router(task, agent_configs)
            
        # Default to first agent if no match
        return agent_configs[0].id if agent_configs else None
    
    async def _route_by_capability(self, task: Task, agent_configs: List[AgentConfig]) -> Optional[str]:
        """Route task based on agent capabilities.
        
        Args:
            task: Task to route
            agent_configs: List of agent configurations
            
        Returns:
            ID of the best matching agent config, or None if no match
        """
        # Extract task tags and requirements
        task_tags = task.tags
        query = task.get_input("query", "")
        
        # Calculate match score for each agent
        best_score = -1
        best_agent_id = None
        
        for config in agent_configs:
            score = 0
            
            # Check for tag matches
            for tag in task_tags:
                if tag in config.capabilities.expertise:
                    score += 2
            
            # Check for expertise matches in query
            for expertise in config.capabilities.expertise:
                if expertise.lower() in query.lower():
                    score += 1
            
            # Update best match
            if score > best_score:
                best_score = score
                best_agent_id = config.id
        
        return best_agent_id
    
    async def _route_by_content(self, task: Task, agent_configs: List[AgentConfig]) -> Optional[str]:
        """Route task based on content matching.
        
        Args:
            task: Task to route
            agent_configs: List of agent configurations
            
        Returns:
            ID of the best matching agent config, or None if no match
        """
        query = task.get_input("query", "")
        
        # Check for keyword matches in agent roles/descriptions
        best_score = -1
        best_agent_id = None
        
        for config in agent_configs:
            score = 0
            
            # Check if query matches agent role or name
            if config.role.lower() in query.lower():
                score += 3
            if config.name.lower() in query.lower():
                score += 2
                
            # Check for expertise matches
            for expertise in config.capabilities.expertise:
                if expertise.lower() in query.lower():
                    score += 1
            
            # Update best match
            if score > best_score:
                best_score = score
                best_agent_id = config.id
        
        # If no content match, fall back to round-robin
        if best_score <= 0:
            agent_config = agent_configs[self.current_agent_index % len(agent_configs)]
            self.current_agent_index += 1
            return agent_config.id
            
        return best_agent_id
    
    async def _route_by_load(self, agent_configs: List[AgentConfig]) -> str:
        """Route task based on agent load.
        
        Args:
            agent_configs: List of agent configurations
            
        Returns:
            ID of the least loaded agent config
        """
        # Find agent with lowest load
        min_load = float('inf')
        min_load_agent_id = None
        
        for config in agent_configs:
            load = self.agent_load.get(config.id, 0)
            if load < min_load:
                min_load = load
                min_load_agent_id = config.id
        
        # If found, increment its load
        if min_load_agent_id:
            self.agent_load[min_load_agent_id] = min_load + 1
            return min_load_agent_id
        
        # If no agents, return None
        return None
    
    def mark_task_complete(self, agent_id: str) -> None:
        """Mark a task as complete for load balancing.
        
        Args:
            agent_id: ID of the agent that completed the task
        """
        if agent_id in self.agent_load and self.agent_load[agent_id] > 0:
            self.agent_load[agent_id] -= 1