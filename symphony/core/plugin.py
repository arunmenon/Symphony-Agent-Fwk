"""Plugin system for Symphony framework."""

import importlib
import inspect
import logging
import os
import pkgutil
from abc import ABC, abstractmethod
from enum import Enum
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from symphony.core.container import Container
from symphony.core.events import EventBus


class PluginType(str, Enum):
    """Types of plugins in Symphony."""
    
    AGENT = "agent"
    TOOL = "tool"
    MEMORY = "memory"
    LLM = "llm"
    ORCHESTRATOR = "orchestrator"
    OTHER = "other"


class Plugin(ABC):
    """Base class for all Symphony plugins."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"symphony.plugin.{self.name}")
    
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
    
    @abstractmethod
    def initialize(self, container: Container, event_bus: EventBus) -> None:
        """Initialize the plugin.
        
        Args:
            container: The service container
            event_bus: The event bus
        """
        pass
    
    def cleanup(self) -> None:
        """Clean up resources used by the plugin."""
        pass


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


class PluginManager:
    """Manages plugins for Symphony."""
    
    def __init__(self, container: Container, event_bus: EventBus):
        self.container = container
        self.event_bus = event_bus
        self.plugins: Dict[str, Plugin] = {}
        self.logger = logging.getLogger("symphony.plugins")
    
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin.
        
        Args:
            plugin: The plugin to register
        """
        if plugin.name in self.plugins:
            self.logger.warning(f"Plugin already registered: {plugin.name}")
            return
            
        try:
            plugin.initialize(self.container, self.event_bus)
            self.plugins[plugin.name] = plugin
            self.logger.info(f"Plugin registered: {plugin.name} (type: {plugin.plugin_type})")
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
    
    def discover_plugins(self, package_name: str) -> None:
        """Discover plugins in a package.
        
        Args:
            package_name: Name of the package to discover plugins in
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            self.logger.error(f"Could not import package: {package_name}")
            return
            
        self._discover_in_module(package)
    
    def _discover_in_module(self, module: ModuleType) -> None:
        """Discover plugins in a module and its submodules.
        
        Args:
            module: The module to search in
        """
        for _, name, is_pkg in pkgutil.iter_modules(module.__path__):
            full_name = f"{module.__name__}.{name}"
            
            try:
                submodule = importlib.import_module(full_name)
                
                # If it's a package, search its modules too
                if is_pkg:
                    self._discover_in_module(submodule)
                
                # Look for Plugin subclasses in the module
                for attr_name in dir(submodule):
                    attr = getattr(submodule, attr_name)
                    
                    if (inspect.isclass(attr) and 
                            issubclass(attr, Plugin) and 
                            attr is not Plugin and
                            not inspect.isabstract(attr)):
                        try:
                            plugin_instance = attr()
                            self.register_plugin(plugin_instance)
                        except Exception as e:
                            self.logger.error(
                                f"Error instantiating plugin {attr.__name__} from {full_name}: {str(e)}"
                            )
            except ImportError as e:
                self.logger.error(f"Error importing {full_name}: {str(e)}")
    
    def cleanup(self) -> None:
        """Clean up all plugins."""
        for name, plugin in list(self.plugins.items()):
            try:
                plugin.cleanup()
                self.logger.info(f"Plugin cleaned up: {name}")
            except Exception as e:
                self.logger.error(f"Error cleaning up plugin {name}: {str(e)}")
                
        self.plugins.clear()