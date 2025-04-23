"""Symphony API module.

This module provides the main entry point for the Symphony framework,
offering a clean, user-friendly API with fluent interfaces.

This module also re-exports all public API components for easy access.
All exported components are considered part of the stable v0.1.0 API contract.
"""

from symphony.utils.annotations import api_stable

import os
from typing import Dict, List, Any, Optional, Union
import asyncio

# Import core Symphony class
from symphony.core.registry import ServiceRegistry
from symphony.core.config import SymphonyConfig, ConfigLoader
from symphony.persistence.memory_repository import InMemoryRepository
from symphony.persistence.file_repository import FileSystemRepository
from symphony.core.task import Task
from symphony.core.agent_config import AgentConfig
from symphony.execution.workflow_tracker import Workflow
from symphony.orchestration.workflow_definition import WorkflowDefinition

# Import facades
from symphony.facade.agents import AgentFacade
from symphony.facade.tasks import TaskFacade
from symphony.facade.workflows import WorkflowFacade
from symphony.facade.patterns import PatternsFacade

# Import builders
from symphony.builder.agent_builder import AgentBuilder
from symphony.builder.task_builder import TaskBuilder
from symphony.builder.workflow_builder import WorkflowBuilder
from symphony.builder.workflow_step_builder import WorkflowStepBuilder
from symphony.patterns.builder import PatternBuilder

# Import state management components
from symphony.core.state import (
    CheckpointManager,
    FileStorageProvider,
    CheckpointError
)

# Import pattern classes
from symphony.patterns.base import Pattern
from symphony.patterns.reasoning.chain_of_thought import ChainOfThoughtPattern
from symphony.patterns.tool_usage.recursive_tool_use import RecursiveToolUsePattern
from symphony.patterns.tool_usage.verify_execute import VerifyExecutePattern
from symphony.patterns.multi_agent.expert_panel import ExpertPanelPattern
from symphony.patterns.learning.reflection import ReflectionPattern

# Import plugin system
from symphony.core.plugin import Plugin, LLMPlugin
from symphony.core.events import EventBus, Event, EventType
from symphony.core.container import Container

# Import persistence
from symphony.persistence.file_repository import FileSystemRepository


@api_stable(
    since_version="0.1.0",
    description="Main Symphony API class providing agent orchestration capabilities"
)
class Symphony:
    """Main Symphony API class.
    
    This class provides a clean, user-friendly API for working with Symphony,
    hiding implementation details like the registry pattern and providing
    fluent interfaces for building complex objects.
    """
    
    def __init__(self, config: SymphonyConfig = None, persistence_enabled: bool = False):
        """Initialize Symphony API.
        
        Args:
            config: Symphony configuration (optional)
            persistence_enabled: Enable state persistence (default: False)
        """
        # Use default config if none provided
        if config is None:
            config = ConfigLoader.load() if hasattr(ConfigLoader, 'load') else SymphonyConfig()
        
        self.config = config
        self.registry = ServiceRegistry.get_instance()
        
        # State management
        self._persistence_enabled = persistence_enabled
        self._state_storage = None
        self._checkpoint_manager = None
        
        # Lazily initialized facades and builders
        self._agent_facade = None
        self._task_facade = None
        self._workflow_facade = None
        self._patterns_facade = None
    
    @api_stable(
        since_version="0.1.0",
        description="Set up Symphony with repositories and components"
    )
    async def setup(
        self, 
        persistence_type: str = "memory", 
        base_dir: str = "./data", 
        with_patterns: bool = True,
        state_dir: Optional[str] = None
    ):
        """Set up Symphony API with basic components.
        
        Args:
            persistence_type: Type of persistence ("memory" or "file")
            base_dir: Base directory for file storage (only used with "file" persistence)
            with_patterns: Whether to register patterns library (default: True)
            state_dir: Directory for state storage (default: "{base_dir}/state")
        """
        # Get persistence type from config if not provided
        if persistence_type is None:
            persistence_type = getattr(self.config, 'persistence_type', 'memory')
        
        # Determine storage path from config
        storage_path = base_dir or getattr(self.config, 'base_dir', './data')
        if not os.path.isabs(storage_path):
            storage_path = os.path.join(os.getcwd(), storage_path)
        storage_path = os.path.join(storage_path, "data")
        os.makedirs(storage_path, exist_ok=True)
        
        # Create repositories
        if persistence_type == "memory":
            # Use in-memory repositories
            task_repo = InMemoryRepository(Task)
            workflow_repo = InMemoryRepository(Workflow)
            agent_config_repo = InMemoryRepository(AgentConfig)
            workflow_def_repo = InMemoryRepository(WorkflowDefinition)
        else:
            # Use file system repositories
            task_repo = FileSystemRepository(Task, storage_path)
            workflow_repo = FileSystemRepository(Workflow, storage_path)
            agent_config_repo = FileSystemRepository(AgentConfig, storage_path)
            workflow_def_repo = FileSystemRepository(WorkflowDefinition, storage_path)
        
        # Register repositories
        self.registry.register_repository("task", task_repo)
        self.registry.register_repository("workflow", workflow_repo)
        self.registry.register_repository("agent_config", agent_config_repo)
        self.registry.register_repository("workflow_definition", workflow_def_repo)
        
        # Register orchestration components
        from symphony.orchestration import register_orchestration_components
        register_orchestration_components(self.registry, symphony_instance=self)
        
        # Register patterns if requested
        if with_patterns:
            from symphony.patterns import register_patterns
            register_patterns(self.registry)
        
        # Initialize state management if enabled
        if self._persistence_enabled:
            # Determine state directory
            if state_dir is None:
                state_dir = os.path.join(os.path.dirname(storage_path), "state")
            
            # Create storage provider and checkpoint manager
            self._state_storage = FileStorageProvider(state_dir)
            self._checkpoint_manager = CheckpointManager(self._state_storage)
            
            # Register in registry for components to access
            self.registry.register_service("state_storage", self._state_storage)
            self.registry.register_service("checkpoint_manager", self._checkpoint_manager)
        
        return self
    
    @property
    @api_stable(
        since_version="0.1.0",
        description="Access to agent operations"
    )
    def agents(self) -> AgentFacade:
        """Get agent facade.
        
        Returns:
            Agent facade
        """
        if self._agent_facade is None:
            self._agent_facade = AgentFacade(self.registry)
        return self._agent_facade
    
    @property
    @api_stable(
        since_version="0.1.0",
        description="Access to task operations"
    )
    def tasks(self) -> TaskFacade:
        """Get task facade.
        
        Returns:
            Task facade
        """
        if self._task_facade is None:
            self._task_facade = TaskFacade(self.registry)
        return self._task_facade
    
    @property
    @api_stable(
        since_version="0.1.0",
        description="Access to workflow operations"
    )
    def workflows(self) -> WorkflowFacade:
        """Get workflow facade.
        
        Returns:
            Workflow facade
        """
        if self._workflow_facade is None:
            self._workflow_facade = WorkflowFacade(self.registry)
        return self._workflow_facade
    
    @property
    @api_stable(
        since_version="0.1.0",
        description="Access to pattern operations"
    )
    def patterns(self) -> PatternsFacade:
        """Get patterns facade.
        
        Returns:
            Patterns facade
        """
        if self._patterns_facade is None:
            self._patterns_facade = PatternsFacade(self.registry)
        return self._patterns_facade
    
    @api_stable(
        since_version="0.1.0",
        description="Create an agent builder for fluent agent construction"
    )
    def build_agent(self) -> AgentBuilder:
        """Create an agent builder.
        
        Returns:
            Agent builder
        """
        return AgentBuilder(self.registry)
    
    @api_stable(
        since_version="0.1.0",
        description="Create a task builder for fluent task construction"
    )
    def build_task(self) -> TaskBuilder:
        """Create a task builder.
        
        Returns:
            Task builder
        """
        return TaskBuilder(self.registry)
    
    @api_stable(
        since_version="0.1.0",
        description="Create a workflow builder for fluent workflow construction"
    )
    def build_workflow(self) -> WorkflowBuilder:
        """Create a workflow builder.
        
        Returns:
            Workflow builder
        """
        return WorkflowBuilder(self.registry)
    
    @api_stable(
        since_version="0.1.0",
        description="Create a pattern builder for fluent pattern construction" 
    )
    def build_pattern(self) -> PatternBuilder:
        """Create a pattern builder.
        
        Returns:
            Pattern builder
        """
        return PatternBuilder(self.registry)
    
    def get_registry(self) -> ServiceRegistry:
        """Get underlying service registry.
        
        Note: Direct registry access should be avoided when possible in favor
        of the Symphony API. This method is provided for advanced use cases.
        
        Returns:
            Service registry
        """
        return self.registry
        
    # State management methods
    
    @api_stable(
        since_version="0.1.0",
        description="Create a checkpoint of the current Symphony state"
    )
    async def create_checkpoint(self, name: Optional[str] = None) -> str:
        """Create a checkpoint of the current Symphony state.
        
        This method captures the state of all active agents, memories, workflows,
        and tasks, allowing them to be restored later. Checkpoints are identified
        by a unique ID.
        
        Args:
            name: Optional name for the checkpoint
            
        Returns:
            Checkpoint ID
            
        Raises:
            RuntimeError: If persistence is not enabled
            CheckpointError: If checkpoint creation fails
        """
        if not self._persistence_enabled or not self._checkpoint_manager:
            raise RuntimeError("State persistence not enabled. Initialize Symphony with persistence_enabled=True.")
        
        return await self._checkpoint_manager.create_checkpoint(self, name)
    
    async def resume_from_checkpoint(self, checkpoint_id: str) -> None:
        """Resume Symphony state from a checkpoint.
        
        This method restores all agents, memories, workflows, and tasks from
        the specified checkpoint. Current state will be discarded.
        
        Args:
            checkpoint_id: Checkpoint ID to restore from
            
        Raises:
            RuntimeError: If persistence is not enabled
            CheckpointError: If checkpoint not found or restoration fails
        """
        if not self._persistence_enabled or not self._checkpoint_manager:
            raise RuntimeError("State persistence not enabled. Initialize Symphony with persistence_enabled=True.")
        
        return await self._checkpoint_manager.restore_checkpoint(self, checkpoint_id)
    
    async def resume_latest_checkpoint(self) -> Optional[str]:
        """Resume Symphony state from the latest checkpoint.
        
        This method restores all agents, memories, workflows, and tasks from
        the most recent checkpoint. Current state will be discarded.
        
        Returns:
            Checkpoint ID if restored, None if no checkpoints exist
            
        Raises:
            RuntimeError: If persistence is not enabled
            CheckpointError: If restoration fails
        """
        if not self._persistence_enabled or not self._checkpoint_manager:
            raise RuntimeError("State persistence not enabled. Initialize Symphony with persistence_enabled=True.")
        
        # Get latest checkpoint
        checkpoint = await self._checkpoint_manager.get_latest_checkpoint()
        if not checkpoint:
            return None
        
        # Restore from checkpoint
        await self._checkpoint_manager.restore_checkpoint(self, checkpoint.checkpoint_id)
        return checkpoint.checkpoint_id
    
    async def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints.
        
        Returns:
            List of checkpoints with their metadata
            
        Raises:
            RuntimeError: If persistence is not enabled
        """
        if not self._persistence_enabled or not self._checkpoint_manager:
            raise RuntimeError("State persistence not enabled. Initialize Symphony with persistence_enabled=True.")
        
        checkpoints = await self._checkpoint_manager.list_checkpoints()
        return [
            {
                "id": checkpoint.checkpoint_id,
                "name": checkpoint.name,
                "created_at": checkpoint.created_at,
                "entity_count": len(checkpoint.entities)
            }
            for checkpoint in checkpoints
        ]
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint ID to delete
            
        Returns:
            True if deleted, False if checkpoint not found
            
        Raises:
            RuntimeError: If persistence is not enabled
        """
        if not self._persistence_enabled or not self._checkpoint_manager:
            raise RuntimeError("State persistence not enabled. Initialize Symphony with persistence_enabled=True.")
        
        return await self._checkpoint_manager.delete_checkpoint(checkpoint_id)


# Decorate all exported classes and functions with api_stable
# Core configuration
SymphonyConfig = api_stable(SymphonyConfig, since_version="0.1.0", description="Symphony configuration container")

# Facades
AgentFacade = api_stable(AgentFacade, since_version="0.1.0", description="Agent management and execution")
TaskFacade = api_stable(TaskFacade, since_version="0.1.0", description="Task management")
WorkflowFacade = api_stable(WorkflowFacade, since_version="0.1.0", description="Workflow execution and management")
PatternsFacade = api_stable(PatternsFacade, since_version="0.1.0", description="Pattern application")

# Builders
AgentBuilder = api_stable(AgentBuilder, since_version="0.1.0", description="Fluent builder for agents")
TaskBuilder = api_stable(TaskBuilder, since_version="0.1.0", description="Fluent builder for tasks")
WorkflowBuilder = api_stable(WorkflowBuilder, since_version="0.1.0", description="Fluent builder for workflows")
WorkflowStepBuilder = api_stable(WorkflowStepBuilder, since_version="0.1.0", description="Fluent builder for workflow steps")
PatternBuilder = api_stable(PatternBuilder, since_version="0.1.0", description="Fluent builder for patterns")

# Pattern classes
Pattern = api_stable(Pattern, since_version="0.1.0", description="Base class for all patterns")
ChainOfThoughtPattern = api_stable(ChainOfThoughtPattern, since_version="0.1.0", description="Sequential reasoning pattern")
RecursiveToolUsePattern = api_stable(RecursiveToolUsePattern, since_version="0.1.0", description="Pattern for recursive tool usage")
VerifyExecutePattern = api_stable(VerifyExecutePattern, since_version="0.1.0", description="Pattern for verification before execution")
ExpertPanelPattern = api_stable(ExpertPanelPattern, since_version="0.1.0", description="Multi-agent expert collaboration pattern")
ReflectionPattern = api_stable(ReflectionPattern, since_version="0.1.0", description="Agent reflection pattern")

# Plugin system
Plugin = api_stable(Plugin, since_version="0.1.0", description="Base class for Symphony plugins")
LLMPlugin = api_stable(LLMPlugin, since_version="0.1.0", description="Base class for LLM-related plugins")
EventBus = api_stable(EventBus, since_version="0.1.0", description="Event bus for Symphony events")
Event = api_stable(Event, since_version="0.1.0", description="Base class for Symphony events")
EventType = api_stable(EventType, since_version="0.1.0", description="Enumeration of event types")
Container = api_stable(Container, since_version="0.1.0", description="Dependency injection container")

# State management
CheckpointManager = api_stable(CheckpointManager, since_version="0.1.0", description="Symphony state checkpoint management")
FileStorageProvider = api_stable(FileStorageProvider, since_version="0.1.0", description="File-based state storage")
CheckpointError = api_stable(CheckpointError, since_version="0.1.0", description="Checkpoint operation error")

# Repository
FileSystemRepository = api_stable(FileSystemRepository, since_version="0.1.0", description="File-based entity repository")

# Re-export all public symbols
__all__ = [
    # Core classes
    'Symphony',
    'SymphonyConfig',
    
    # Facades
    'AgentFacade',
    'TaskFacade',
    'WorkflowFacade',
    'PatternsFacade',
    
    # Builders
    'AgentBuilder',
    'TaskBuilder',
    'WorkflowBuilder',
    'WorkflowStepBuilder',
    'PatternBuilder',
    
    # Pattern classes
    'Pattern',
    'ChainOfThoughtPattern',
    'RecursiveToolUsePattern',
    'VerifyExecutePattern',
    'ExpertPanelPattern',
    'ReflectionPattern',
    
    # Plugin system
    'Plugin',
    'LLMPlugin',
    'EventBus',
    'Event',
    'EventType',
    'Container',
    
    # State management
    'CheckpointManager',
    'FileStorageProvider',
    'CheckpointError',
    
    # Repository
    'FileSystemRepository'
]