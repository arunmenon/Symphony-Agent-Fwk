"""Plugin system for Symphony framework.

This module provides a comprehensive plugin system for extending Symphony with
custom components, patterns, integrations, and more. It supports plugin discovery
through entry points, local directories, and explicit registration.
"""

import importlib
import importlib.metadata
import importlib.util
import inspect
import logging
import os
import pathlib
import pkgutil
import sys
from abc import ABC, abstractmethod
from enum import Enum
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from symphony.core.container import Container
from symphony.core.events import EventBus
from symphony.core.registry import ServiceRegistry


class PluginType(str, Enum):
    """Types of plugins in Symphony."""
    
    AGENT = "agent"
    TOOL = "tool"
    MEMORY = "memory"
    LLM = "llm"
    ORCHESTRATOR = "orchestrator"
    PATTERN = "pattern"
    EXTENSION = "extension"
    OTHER = "other"


class Plugin(ABC):
    """Base class for all Symphony plugins."""
    
    def __init__(self):
        """Initialize plugin.
        
        Sets up logging and initialization state.
        """
        self.logger = logging.getLogger(f"symphony.plugin.{self.name}")
        self._initialized = False
        self._container = None
        self._event_bus = None
        self._registry = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the plugin."""
        pass
    
    @property
    def version(self) -> str:
        """Get the version of the plugin."""
        return "0.1.0"
    
    @property
    def description(self) -> str:
        """Get the description of the plugin."""
        return ""
    
    @property
    def plugin_type(self) -> PluginType:
        """Get the type of the plugin."""
        return PluginType.OTHER
    
    @property
    def dependencies(self) -> List[str]:
        """Get list of plugin dependencies by name.
        
        Returns:
            List of plugin names this plugin depends on
        """
        return []
    
    @property
    def initialized(self) -> bool:
        """Check if the plugin is initialized."""
        return self._initialized
    
    def initialize(self, container: Container, event_bus: EventBus, registry: ServiceRegistry) -> None:
        """Initialize the plugin.
        
        Args:
            container: The service container
            event_bus: The event bus
            registry: The service registry
        """
        if self._initialized:
            return
            
        self._container = container
        self._event_bus = event_bus
        self._registry = registry
        
        self.setup()
        self._initialized = True
    
    @abstractmethod
    def setup(self) -> None:
        """Set up the plugin.
        
        This method should be implemented by plugin subclasses to initialize
        their components and register them with the service registry.
        """
        pass
    
    def cleanup(self) -> None:
        """Clean up resources used by the plugin."""
        self._initialized = False


class AgentPlugin(Plugin):
    """Base class for agent plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        return PluginType.AGENT


class ToolPlugin(Plugin):
    """Base class for tool plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        return PluginType.TOOL
    
    @abstractmethod
    def get_tools(self) -> List[Callable[..., Any]]:
        """Get the tools provided by this plugin."""
        pass


class MemoryPlugin(Plugin):
    """Base class for memory plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        return PluginType.MEMORY


class LLMPlugin(Plugin):
    """Base class for LLM plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        return PluginType.LLM


class OrchestratorPlugin(Plugin):
    """Base class for orchestrator plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        return PluginType.ORCHESTRATOR


class PatternPlugin(Plugin):
    """Base class for pattern plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        return PluginType.PATTERN


class PluginManager:
    """Manages plugins for Symphony.
    
    This class manages the discovery, loading, and registration of
    Symphony plugins. It supports various discovery mechanisms:
    
    1. Entry points in pyproject.toml
    2. Local plugin directories
    3. Explicitly registered plugins
    4. Python package discovery
    """
    
    def __init__(self, container: Container, event_bus: EventBus, registry: ServiceRegistry):
        """Initialize plugin manager.
        
        Args:
            container: The service container
            event_bus: The event bus
            registry: The service registry
        """
        self.container = container
        self.event_bus = event_bus
        self.registry = registry
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_dirs: List[str] = []
        self.entry_point_group = "symphony.plugins"
        self.loaded_entry_points: Set[str] = set()
        self.logger = logging.getLogger("symphony.plugins")
        
        # Register standard plugin directories
        user_plugin_dir = os.path.expanduser("~/.symphony/plugins")
        if os.path.isdir(user_plugin_dir):
            self.register_plugin_dir(user_plugin_dir)
            
        local_plugin_dir = os.path.join(os.getcwd(), "plugins")
        if os.path.isdir(local_plugin_dir):
            self.register_plugin_dir(local_plugin_dir)
        
        # Register ourselves with the registry
        self.registry.register_service("plugin_manager", self)
    
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin.
        
        Args:
            plugin: The plugin to register
        """
        if plugin.name in self.plugins:
            self.logger.warning(f"Plugin already registered: {plugin.name}")
            return
        
        # Check dependencies
        missing_deps = [dep for dep in plugin.dependencies if dep not in self.plugins]
        if missing_deps:
            self.logger.error(f"Cannot register plugin {plugin.name}: missing dependencies {missing_deps}")
            return
        
        try:
            # Initialize plugin with container, event bus, and registry
            plugin.initialize(self.container, self.event_bus, self.registry)
            self.plugins[plugin.name] = plugin
            self.logger.info(f"Plugin registered: {plugin.name} (type: {plugin.plugin_type}, version: {plugin.version})")
        except Exception as e:
            self.logger.error(f"Error initializing plugin {plugin.name}: {str(e)}")
    
    def unregister_plugin(self, name: str) -> bool:
        """Unregister a plugin.
        
        Args:
            name: The name of the plugin to unregister
            
        Returns:
            True if unregistered, False if not found
        """
        if name not in self.plugins:
            return False
        
        # Check if other plugins depend on this one
        dependents = [p.name for p in self.plugins.values() if name in p.dependencies]
        if dependents:
            self.logger.error(f"Cannot unregister plugin {name}: used by {dependents}")
            return False
        
        plugin = self.plugins[name]
        
        try:
            plugin.cleanup()
        except Exception as e:
            self.logger.error(f"Error cleaning up plugin {name}: {str(e)}")
        
        del self.plugins[name]
        self.logger.info(f"Plugin unregistered: {name}")
        return True
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name.
        
        Args:
            name: The name of the plugin
            
        Returns:
            The plugin if found, None otherwise
        """
        return self.plugins.get(name)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """Get all plugins of a specific type.
        
        Args:
            plugin_type: The type of plugins to get
            
        Returns:
            List of plugins of the specified type
        """
        return [
            plugin for plugin in self.plugins.values()
            if plugin.plugin_type == plugin_type
        ]
    
    def register_plugin_dir(self, directory: str) -> None:
        """Register a directory to search for plugins.
        
        Args:
            directory: Path to plugin directory
        """
        if os.path.isdir(directory) and directory not in self.plugin_dirs:
            self.plugin_dirs.append(directory)
            self.logger.debug(f"Registered plugin directory: {directory}")
    
    def discover_plugins(self) -> None:
        """Discover plugins from all sources."""
        # Discover plugins from entry points
        self._discover_entry_point_plugins()
        
        # Discover plugins from directories
        self._discover_directory_plugins()
        
        # Can also call discover_plugins_in_package explicitly for package discovery
    
    def _discover_entry_point_plugins(self) -> None:
        """Discover plugins from entry points."""
        try:
            discovered = 0
            for entry_point in importlib.metadata.entry_points(group=self.entry_point_group):
                if entry_point.name not in self.loaded_entry_points:
                    plugin_cls = entry_point.load()
                    if inspect.isclass(plugin_cls) and issubclass(plugin_cls, Plugin):
                        try:
                            plugin = plugin_cls()
                            self.register_plugin(plugin)
                            self.loaded_entry_points.add(entry_point.name)
                            discovered += 1
                        except Exception as e:
                            self.logger.error(f"Error loading plugin {entry_point.name}: {e}")
            
            if discovered > 0:
                self.logger.info(f"Discovered {discovered} plugins from entry points")
        except Exception as e:
            self.logger.error(f"Error discovering entry point plugins: {e}")
    
    def _discover_directory_plugins(self) -> None:
        """Discover plugins from directories."""
        for directory in self.plugin_dirs:
            try:
                plugin_files = list(pathlib.Path(directory).glob("*_plugin.py"))
                
                for plugin_file in plugin_files:
                    module_name = f"symphony_plugin_{plugin_file.stem}"
                    if module_name in sys.modules:
                        continue
                    
                    try:
                        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[module_name] = module
                            spec.loader.exec_module(module)
                            
                            # Find plugin classes
                            self._discover_plugins_in_module(module)
                    except Exception as e:
                        self.logger.error(f"Error loading plugin from {plugin_file}: {e}")
            except Exception as e:
                self.logger.error(f"Error discovering plugins in directory {directory}: {e}")
    
    def discover_plugins_in_package(self, package_name: str) -> None:
        """Discover plugins in a package.
        
        Args:
            package_name: Name of the package to discover plugins in
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            self.logger.error(f"Could not import package: {package_name}")
            return
        
        self._discover_in_package(package)
    
    def _discover_in_package(self, module: ModuleType) -> None:
        """Discover plugins in a module and its submodules.
        
        Args:
            module: The module to search in
        """
        # First discover in this module
        self._discover_plugins_in_module(module)
        
        # Then recurse into submodules
        if hasattr(module, "__path__"):
            for _, name, is_pkg in pkgutil.iter_modules(module.__path__):
                full_name = f"{module.__name__}.{name}"
                
                try:
                    submodule = importlib.import_module(full_name)
                    
                    # If it's a package, search its modules too
                    if is_pkg:
                        self._discover_in_package(submodule)
                    else:
                        self._discover_plugins_in_module(submodule)
                except ImportError as e:
                    self.logger.error(f"Error importing {full_name}: {str(e)}")
    
    def _discover_plugins_in_module(self, module: ModuleType) -> None:
        """Discover plugins in a single module.
        
        Args:
            module: The module to search in
        """
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            if (inspect.isclass(attr) and 
                    issubclass(attr, Plugin) and 
                    attr is not Plugin and
                    not inspect.isabstract(attr)):
                try:
                    plugin_instance = attr()
                    self.register_plugin(plugin_instance)
                except Exception as e:
                    self.logger.error(
                        f"Error instantiating plugin {attr.__name__} from {module.__name__}: {str(e)}"
                    )
    
    def cleanup(self) -> None:
        """Clean up all plugins."""
        for name, plugin in list(self.plugins.items()):
            try:
                plugin.cleanup()
                self.logger.info(f"Plugin cleaned up: {name}")
            except Exception as e:
                self.logger.error(f"Error cleaning up plugin {name}: {str(e)}")
        
        self.plugins.clear()


def register_plugin_system(registry: ServiceRegistry) -> PluginManager:
    """Register the plugin system with the service registry.
    
    Args:
        registry: The service registry
        
    Returns:
        The plugin manager
    """
    # Get container and event bus from registry
    container = registry.get_service("container")
    event_bus = registry.get_service("event_bus")
    
    # Create plugin manager
    plugin_manager = PluginManager(container, event_bus, registry)
    
    return plugin_manager