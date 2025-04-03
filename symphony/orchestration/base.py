"""Base orchestration engine for managing agent execution flows."""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Union

from pydantic import BaseModel, Field

from symphony.agents.base import AgentBase, AgentConfig, ReactiveAgent
from symphony.environment.base import BaseEnvironment
from symphony.llm.base import LLMClient
from symphony.prompts.registry import PromptRegistry


class OrchestratorConfig(BaseModel):
    """Configuration for an orchestrator."""
    
    agent_configs: List[AgentConfig] = Field(default_factory=list)
    max_steps: int = 10
    max_time_seconds: Optional[int] = None  # None means no time limit


class Orchestrator(ABC):
    """Base class for orchestration engines."""
    
    def __init__(
        self,
        config: OrchestratorConfig,
        llm_client: LLMClient,
        prompt_registry: PromptRegistry,
        environment: Optional[BaseEnvironment] = None,
    ):
        self.config = config
        self.llm_client = llm_client
        self.prompt_registry = prompt_registry
        self.environment = environment
        
        # Initialize agents
        self.agents: Dict[str, AgentBase] = {}
        
    @abstractmethod
    async def run(self, input_message: str) -> str:
        """Run the orchestration flow with an input message."""
        pass


class BasicOrchestrator(Orchestrator):
    """A simple orchestrator that runs a single agent."""
    
    def __init__(
        self,
        config: OrchestratorConfig,
        llm_client: LLMClient,
        prompt_registry: PromptRegistry,
        agent_cls: Type[AgentBase] = ReactiveAgent,
        environment: Optional[BaseEnvironment] = None,
    ):
        super().__init__(config, llm_client, prompt_registry, environment)
        
        # Create the agent
        if config.agent_configs:
            agent_config = config.agent_configs[0]
            self.agent = agent_cls(
                config=agent_config,
                llm_client=llm_client,
                prompt_registry=prompt_registry,
            )
            self.agents[agent_config.name] = self.agent
    
    async def run(self, input_message: str) -> str:
        """Run the orchestration flow with an input message."""
        if not self.agents:
            return "No agents configured"
            
        # Just run the first agent
        agent = next(iter(self.agents.values()))
        return await agent.run(input_message)


class TurnType(str, Enum):
    """Types of turns in sequential multi-agent orchestration."""
    
    SEQUENTIAL = "sequential"  # One agent after another in order
    ROUND_ROBIN = "round_robin"  # One agent after another, cycling
    OUTPUT_BASED = "output_based"  # Next agent chosen based on output pattern


class MultiAgentOrchestrator(Orchestrator):
    """Orchestrator that manages multiple agents in a sequence or parallel."""
    
    def __init__(
        self,
        config: OrchestratorConfig,
        llm_client: LLMClient,
        prompt_registry: PromptRegistry,
        agent_classes: Optional[Dict[str, Type[AgentBase]]] = None,
        environment: Optional[BaseEnvironment] = None,
        turn_type: TurnType = TurnType.SEQUENTIAL,
    ):
        super().__init__(config, llm_client, prompt_registry, environment)
        
        self.turn_type = turn_type
        self.current_agent_idx = 0
        
        # Create all agents
        for agent_config in config.agent_configs:
            agent_cls = agent_classes.get(agent_config.agent_type, ReactiveAgent) if agent_classes else ReactiveAgent
            
            agent = agent_cls(
                config=agent_config,
                llm_client=llm_client,
                prompt_registry=prompt_registry,
            )
            self.agents[agent_config.name] = agent
    
    async def run(self, input_message: str) -> str:
        """Run the orchestration flow with an input message."""
        if not self.agents:
            return "No agents configured"
            
        agent_names = list(self.agents.keys())
        current_message = input_message
        step_count = 0
        final_result = ""
        
        while step_count < self.config.max_steps:
            # Determine which agent to run
            if self.turn_type == TurnType.SEQUENTIAL:
                if self.current_agent_idx >= len(agent_names):
                    break  # All agents have had their turn
                agent_name = agent_names[self.current_agent_idx]
                self.current_agent_idx += 1
            elif self.turn_type == TurnType.ROUND_ROBIN:
                agent_name = agent_names[self.current_agent_idx % len(agent_names)]
                self.current_agent_idx += 1
            else:  # OUTPUT_BASED
                # In a real implementation, would determine next agent based on output pattern
                agent_name = agent_names[self.current_agent_idx % len(agent_names)]
                self.current_agent_idx += 1
                
            # Run the selected agent
            agent = self.agents[agent_name]
            agent_result = await agent.run(current_message)
            
            # Update for the next iteration
            current_message = agent_result
            final_result = agent_result
            step_count += 1
            
            # For sequential, we're done after one pass
            if self.turn_type == TurnType.SEQUENTIAL and self.current_agent_idx >= len(agent_names):
                break
                
            # For OUTPUT_BASED, could add logic here to check for completion
            
        return final_result