"""Symphony API module.

This module provides the main entry point for the Symphony framework,
offering a clean, user-friendly API with fluent interfaces.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union, Type
import asyncio

from symphony.core.registry import ServiceRegistry
from symphony.core.config import SymphonyConfig, ConfigLoader
from symphony.core.plugin import Plugin, PluginManager
from symphony.persistence.memory_repository import InMemoryRepository
from symphony.persistence.file_repository import FileSystemRepository
from symphony.core.task import Task
from symphony.core.agent_config import AgentConfig
from symphony.execution.workflow_tracker import Workflow
from symphony.orchestration.workflow_definition import WorkflowDefinition

from symphony.facade.agents import AgentFacade
from symphony.facade.tasks import TaskFacade
from symphony.facade.workflows import WorkflowFacade
from symphony.patterns.facade import PatternsFacade

from symphony.builder.agent_builder import AgentBuilder
from symphony.builder.task_builder import TaskBuilder
from symphony.builder.workflow_builder import WorkflowBuilder
from symphony.patterns.builder import PatternBuilder


class Symphony:
    """Main Symphony API class.
    
    This class provides a clean, user-friendly API for working with Symphony,
    hiding implementation details like the registry pattern and providing
    fluent interfaces for building complex objects.
    """
    
    def __init__(self, config: SymphonyConfig = None):
        """Initialize Symphony API.
        
        Args:
            config: Symphony configuration (optional)
        """
        # Use default config if none provided
        if config is None:
            config = ConfigLoader.load() if hasattr(ConfigLoader, 'load') else SymphonyConfig()
        
        self.config = config
        self.registry = ServiceRegistry.get_instance()
        self.logger = logging.getLogger("symphony")
        
        # Lazily initialized facades and builders
        self._agent_facade = None
        self._task_facade = None
        self._workflow_facade = None
        self._patterns_facade = None
        self._plugin_manager = None
    
    async def setup(
        self, 
        persistence_type: str = "memory", 
        base_dir: str = "./data", 
        with_patterns: bool = True,
        with_plugins: bool = True,
        plugin_directories: List[str] = None,
    ):
        """Set up Symphony API with basic components.
        
        Args:
            persistence_type: Type of persistence ("memory" or "file")
            base_dir: Base directory for file storage (only used with "file" persistence)
            with_patterns: Whether to register patterns library (default: True)
            with_plugins: Whether to discover and load plugins (default: True)
            plugin_directories: Additional plugin directories to search
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
        register_orchestration_components(self.registry)
        
        # Register patterns if requested
        if with_patterns:
            from symphony.patterns import register_patterns
            register_patterns(self.registry)
        
        # Set up plugin system if requested
        if with_plugins:
            # Make sure container and event bus are registered
            if not self.registry.has_service("container"):
                from symphony.core.container import Container
                self.registry.register_service("container", Container())
                
            if not self.registry.has_service("event_bus"):
                from symphony.core.events import EventBus
                self.registry.register_service("event_bus", EventBus())
            
            # Register plugin system
            from symphony.core.plugin import register_plugin_system
            self._plugin_manager = register_plugin_system(self.registry)
            
            # Register additional plugin directories
            if plugin_directories:
                for directory in plugin_directories:
                    self._plugin_manager.register_plugin_dir(directory)
            
            # Discover and load plugins
            self._plugin_manager.discover_plugins()
            self.logger.info("Plugin system initialized")
        
        return self
    
    @property
    def agents(self) -> AgentFacade:
        """Get agent facade.
        
        Returns:
            Agent facade
        """
        if self._agent_facade is None:
            self._agent_facade = AgentFacade(self.registry)
        return self._agent_facade
    
    @property
    def tasks(self) -> TaskFacade:
        """Get task facade.
        
        Returns:
            Task facade
        """
        if self._task_facade is None:
            self._task_facade = TaskFacade(self.registry)
        return self._task_facade
    
    @property
    def workflows(self) -> WorkflowFacade:
        """Get workflow facade.
        
        Returns:
            Workflow facade
        """
        if self._workflow_facade is None:
            self._workflow_facade = WorkflowFacade(self.registry)
        return self._workflow_facade
    
    def build_agent(self) -> AgentBuilder:
        """Create an agent builder.
        
        Returns:
            Agent builder
        """
        return AgentBuilder(self.registry)
    
    def build_task(self) -> TaskBuilder:
        """Create a task builder.
        
        Returns:
            Task builder
        """
        return TaskBuilder(self.registry)
    
    def build_workflow(self) -> WorkflowBuilder:
        """Create a workflow builder.
        
        Returns:
            Workflow builder
        """
        return WorkflowBuilder(self.registry)
    
    @property
    def patterns(self) -> PatternsFacade:
        """Get patterns facade.
        
        Returns:
            Patterns facade
        """
        if self._patterns_facade is None:
            self._patterns_facade = PatternsFacade(self.registry)
        return self._patterns_facade
    
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
        
    @property
    def plugins(self) -> Optional[PluginManager]:
        """Get plugin manager.
        
        Returns:
            Plugin manager or None if plugins are not enabled
        """
        return self._plugin_manager
        
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin with Symphony.
        
        Args:
            plugin: Plugin instance to register
            
        Raises:
            RuntimeError: If plugin system is not initialized
        """
        if self._plugin_manager is None:
            raise RuntimeError("Plugin system not initialized. Call setup() with with_plugins=True first.")
        
        self._plugin_manager.register_plugin(plugin)
        
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance or None if not found or plugin system not initialized
        """
        if self._plugin_manager is None:
            return None
            
        return self._plugin_manager.get_plugin(name)
        
    def discover_plugins_in_package(self, package_name: str) -> None:
        """Discover plugins in a Python package.
        
        Args:
            package_name: Name of the package to search
            
        Raises:
            RuntimeError: If plugin system is not initialized
        """
        if self._plugin_manager is None:
            raise RuntimeError("Plugin system not initialized. Call setup() with with_plugins=True first.")
            
        self._plugin_manager.discover_plugins_in_package(package_name)
        
    def has_feature(self, feature_name: str) -> bool:
        """Check if a particular optional feature is available.
        
        This method delegates to the feature detection utility in the top-level
        Symphony module.
        
        Args:
            feature_name: Name of the feature to check for
            
        Returns:
            True if the feature is available, False otherwise
        """
        from symphony import has_feature
        return has_feature(feature_name)