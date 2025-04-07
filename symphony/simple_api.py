"""Simplified Symphony API.

This module provides a low cognitive load API for the Symphony framework,
focusing on immediate value with minimal configuration.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, Set

from symphony.api import Symphony as CoreSymphony
from symphony.core.registry import ServiceRegistry
from symphony.core.config import SymphonyConfig
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.core.task import Task, TaskStatus, TaskPriority
from symphony.memory.base import BaseMemory
from symphony.memory.memory_manager import MemoryManager
from symphony.orchestration.workflow_definition import WorkflowDefinition

# Type variables
T = TypeVar('T')
AgentType = TypeVar('AgentType', bound='Agent')
WorkflowType = TypeVar('WorkflowType', bound='Workflow')

class Agent:
    """Simplified Agent interface with progressive complexity."""
    
    def __init__(
        self, 
        symphony: 'Symphony',
        name: str,
        description: str,
        agent_id: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        preset: Optional[str] = None,
    ):
        """Initialize a Symphony agent.
        
        Args:
            symphony: Symphony instance
            name: Agent name
            description: Agent description
            agent_id: Agent ID (optional)
            capabilities: Agent capabilities (optional)
            preset: Domain preset to use (optional)
        """
        self.symphony = symphony
        self.name = name
        self.description = description
        self.agent_id = agent_id
        self.capabilities = capabilities or []
        self.preset = preset
        self.logger = logging.getLogger(f"symphony.agent.{name}")
        
        # Internal properties
        self._core_agent = None
        self._tools: Set[str] = set()
        self._memories: List[BaseMemory] = []
        self._initialized = False
        
        # Apply preset if provided
        if preset:
            self._apply_preset(preset)
    
    def _apply_preset(self, preset: str) -> None:
        """Apply a domain preset to this agent.
        
        Args:
            preset: Preset name
        """
        # Apply preset capabilities and tools
        preset_config = self.symphony._get_preset_config(preset)
        if preset_config:
            # Add preset capabilities
            preset_capabilities = preset_config.get("capabilities", [])
            self.capabilities.extend(preset_capabilities)
            
            # Add preset tools
            preset_tools = preset_config.get("tools", [])
            self._tools.update(preset_tools)
            
            self.logger.info(f"Applied preset '{preset}' to agent '{self.name}'")
        else:
            self.logger.warning(f"Preset '{preset}' not found")
    
    async def _ensure_initialized(self) -> None:
        """Ensure the agent is initialized."""
        if not self._initialized:
            # Create agent config
            config = AgentConfig(
                name=self.name,
                description=self.description,
                capabilities=AgentCapabilities(capabilities=self.capabilities)
            )
            
            # Save agent config
            self.agent_id = await self.symphony._core_symphony.agents.save_agent(config)
            
            self._initialized = True
            self.logger.debug(f"Agent '{self.name}' initialized with ID {self.agent_id}")
    
    def add_memory(self, memory_type: str, **kwargs) -> 'Agent':
        """Add memory to the agent.
        
        Args:
            memory_type: Type of memory to add
            **kwargs: Additional memory configuration
            
        Returns:
            Self for method chaining
        """
        # Create memory based on type
        if memory_type == "conversation":
            from symphony.memory import ConversationMemory
            memory = ConversationMemory(**kwargs)
        elif memory_type == "vector":
            from symphony.memory import VectorMemory
            memory = VectorMemory(**kwargs)
        elif memory_type == "knowledge_graph":
            from symphony.memory import KnowledgeGraphMemory
            memory = KnowledgeGraphMemory(**kwargs)
        else:
            self.logger.warning(f"Unknown memory type: {memory_type}")
            return self
        
        # Add memory
        self._memories.append(memory)
        self.logger.info(f"Added {memory_type} memory to agent '{self.name}'")
        return self
    
    def add_tool(self, tool_name: str) -> 'Agent':
        """Add a tool to the agent.
        
        Args:
            tool_name: Name of the tool to add
            
        Returns:
            Self for method chaining
        """
        self._tools.add(tool_name)
        self.logger.info(f"Added tool '{tool_name}' to agent '{self.name}'")
        return self
    
    async def execute(self, query: str, use_tools: Optional[List[str]] = None) -> Any:
        """Execute a task with this agent.
        
        Args:
            query: Query to execute
            use_tools: Tools to use for this execution (optional)
            
        Returns:
            Execution result
        """
        await self._ensure_initialized()
        
        # Create task
        task = Task(
            name=f"Task for {self.name}",
            description=f"Execute query: {query[:50]}...",
            agent_id=self.agent_id,
            query=query,
            priority=TaskPriority.NORMAL
        )
        
        # Add tools for this execution
        tools_to_use = set(self._tools)
        if use_tools:
            tools_to_use.update(use_tools)
        
        if tools_to_use:
            # Attach tools to task
            task.metadata = task.metadata or {}
            task.metadata["tools"] = list(tools_to_use)
        
        # Execute task
        task_result = await self.symphony._core_symphony.tasks.execute_task(task)
        return task_result.result


class Workflow:
    """Simplified workflow interface with progressive complexity."""
    
    def __init__(
        self,
        symphony: 'Symphony',
        name: str,
        description: str,
    ):
        """Initialize a Symphony workflow.
        
        Args:
            symphony: Symphony instance
            name: Workflow name
            description: Workflow description
        """
        self.symphony = symphony
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"symphony.workflow.{name}")
        
        # Internal properties
        self._steps = []
        self._workflow_def = None
    
    def add_step(
        self,
        name: str,
        agent: Agent,
        input: Optional[str] = None,
        input_from: Optional[str] = None,
        tools: Optional[List[str]] = None,
    ) -> 'Workflow':
        """Add a step to the workflow.
        
        Args:
            name: Step name
            agent: Agent to execute the step
            input: Direct input for the step (optional)
            input_from: Name of the previous step to get input from (optional)
            tools: Tools to use for this step (optional)
            
        Returns:
            Self for method chaining
        """
        self._steps.append({
            "name": name,
            "agent": agent,
            "input": input,
            "input_from": input_from,
            "tools": tools or []
        })
        self.logger.info(f"Added step '{name}' to workflow '{self.name}'")
        return self
    
    async def _build_workflow_definition(self) -> WorkflowDefinition:
        """Build the workflow definition.
        
        Returns:
            WorkflowDefinition instance
        """
        # First ensure all agents are initialized
        for step in self._steps:
            await step["agent"]._ensure_initialized()
        
        # Create workflow definition
        workflow_def = WorkflowDefinition(
            name=self.name,
            description=self.description
        )
        
        # Add steps
        for step in self._steps:
            step_config = {
                "name": step["name"],
                "description": f"Step {step['name']} in workflow {self.name}",
                "agent_id": step["agent"].agent_id,
                "input_data": {}
            }
            
            # Add input
            if step["input"]:
                step_config["input_data"]["query"] = step["input"]
            
            # Add input from previous step
            if step["input_from"]:
                step_config["input_from"] = step["input_from"]
            
            # Add tools
            if step["tools"]:
                step_config["input_data"]["tools"] = step["tools"]
            
            workflow_def.add_step(**step_config)
        
        return workflow_def


class Symphony:
    """Simplified Symphony API with progressive complexity."""
    
    def __init__(self, config: Optional[SymphonyConfig] = None):
        """Initialize Symphony with minimal configuration.
        
        Args:
            config: Symphony configuration (optional)
        """
        self.logger = logging.getLogger("symphony")
        
        # Initialize core Symphony
        self._core_symphony = CoreSymphony(config)
        
        # Store registered tools
        self._tools: Dict[str, Callable] = {}
        
        # Store domain presets
        self._presets: Dict[str, Dict[str, Any]] = {
            "default": {
                "capabilities": ["general", "conversation"],
                "tools": []
            },
            "legal": {
                "capabilities": ["legal", "documents", "analysis"],
                "tools": ["document_analyzer"]
            },
            "medical": {
                "capabilities": ["medical", "healthcare", "diagnosis"],
                "tools": ["medical_lookup"]
            },
            "technical": {
                "capabilities": ["technical", "programming", "troubleshooting"],
                "tools": ["code_analyzer", "web_search"]
            }
        }
        
        self.logger.info("Symphony initialized with simplified API")
    
    async def setup(self, persistence_type: str = "memory", base_dir: str = "./data"):
        """Set up Symphony with basic components.
        
        Args:
            persistence_type: Type of persistence ("memory" or "file")
            base_dir: Base directory for file storage
            
        Returns:
            Self for method chaining
        """
        # Set up core Symphony
        await self._core_symphony.setup(
            persistence_type=persistence_type,
            base_dir=base_dir,
            with_patterns=True,
            with_plugins=True
        )
        
        # Register built-in tools with core Symphony
        self._register_builtin_tools()
        
        self.logger.info("Symphony setup completed")
        return self
    
    def _register_builtin_tools(self):
        """Register built-in tools."""
        # Add any built-in tools here
        pass
    
    def create_agent(
        self,
        name: str,
        description: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        preset: Optional[str] = None
    ) -> Agent:
        """Create a Symphony agent with minimal configuration.
        
        Args:
            name: Agent name
            description: Agent description (optional)
            capabilities: Agent capabilities (optional)
            preset: Domain preset to use (optional)
            
        Returns:
            Configured agent
        """
        # Use name as description if not provided
        if description is None:
            description = f"{name} created with Symphony"
        
        # Create agent
        agent = Agent(
            symphony=self,
            name=name,
            description=description,
            capabilities=capabilities,
            preset=preset
        )
        
        self.logger.info(f"Created agent '{name}' with {'preset ' + preset if preset else 'no preset'}")
        return agent
    
    def create_workflow(self, name: str, description: Optional[str] = None) -> Workflow:
        """Create a Symphony workflow.
        
        Args:
            name: Workflow name
            description: Workflow description (optional)
            
        Returns:
            Configured workflow
        """
        # Use name as description if not provided
        if description is None:
            description = f"Workflow {name} created with Symphony"
        
        # Create workflow
        workflow = Workflow(
            symphony=self,
            name=name,
            description=description
        )
        
        self.logger.info(f"Created workflow '{name}'")
        return workflow
    
    def register_tool(self, name: str, tool_function: Callable) -> None:
        """Register a tool with Symphony.
        
        Args:
            name: Tool name
            tool_function: Tool implementation function
        """
        # Store tool
        self._tools[name] = tool_function
        
        # Register with core Symphony
        # This needs to integrate with the core tool system
        # Implementation depends on the core Symphony tool system
        
        self.logger.info(f"Registered tool '{name}'")
    
    def _get_preset_config(self, preset: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a domain preset.
        
        Args:
            preset: Preset name
            
        Returns:
            Preset configuration or None if not found
        """
        return self._presets.get(preset)
    
    def register_preset(self, name: str, capabilities: List[str], tools: List[str]) -> None:
        """Register a new domain preset.
        
        Args:
            name: Preset name
            capabilities: Capabilities for the preset
            tools: Tools for the preset
        """
        self._presets[name] = {
            "capabilities": capabilities,
            "tools": tools
        }
        self.logger.info(f"Registered preset '{name}'")
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if a particular optional feature is available.
        
        Args:
            feature_name: Name of the feature to check for
            
        Returns:
            True if the feature is available, False otherwise
        """
        # Delegate to core Symphony
        from symphony import has_feature as core_has_feature
        return core_has_feature(feature_name)
    
    async def execute_workflow(self, workflow: Workflow) -> Any:
        """Execute a workflow.
        
        Args:
            workflow: Workflow to execute
            
        Returns:
            Workflow execution result
        """
        # Build workflow definition
        workflow_def = await workflow._build_workflow_definition()
        
        # Save workflow definition
        workflow_def_id = await self._core_symphony.workflows.save_workflow_definition(workflow_def)
        
        # Execute workflow
        result = await self._core_symphony.workflows.execute_workflow_by_definition_id(workflow_def_id)
        
        # Return the result of the last step
        if result and result.steps:
            last_step = result.steps[-1]
            return last_step.result
        
        return None