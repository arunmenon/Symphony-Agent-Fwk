# Plugin System Integration

## 1. Update Symphony API for Plugin System

The first step is to integrate the plugin system with the main Symphony API:

```python
# symphony/api.py - update setup method

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
    # ... existing setup code ...
    
    # Set up plugin system if requested
    if with_plugins:
        from symphony.core.plugin import register_plugin_system
        plugin_manager = register_plugin_system(self.registry)
        
        # Register additional plugin directories
        if plugin_directories:
            for directory in plugin_directories:
                plugin_manager.register_plugin_dir(directory)
        
        # Discover plugins
        plugin_manager.discover_plugins()
        
    return self
```

## 2. Add Plugin System API to Symphony Class

Add methods to interact with the plugin system:

```python
# symphony/api.py - add to Symphony class

def register_plugin(self, plugin: "Plugin") -> None:
    """Register a plugin with Symphony.
    
    Args:
        plugin: Plugin instance to register
    """
    plugin_manager = self.registry.get_service("plugin_manager")
    plugin_manager.register_plugin(plugin)

def get_plugin(self, name: str) -> Optional["Plugin"]:
    """Get a plugin by name.
    
    Args:
        name: Plugin name
        
    Returns:
        Plugin instance or None if not found
    """
    plugin_manager = self.registry.get_service("plugin_manager")
    return plugin_manager.get_plugin(name)

def discover_plugins_in_package(self, package_name: str) -> None:
    """Discover plugins in a Python package.
    
    Args:
        package_name: Name of the package to search
    """
    plugin_manager = self.registry.get_service("plugin_manager")
    plugin_manager.discover_plugins_in_package(package_name)
```

## 3. Plugin Registration at Framework Initialization

Update the Symphony initialization to register core features as plugins:

```python
# symphony/__init__.py - add to setup_plugins function

def setup_plugins(registry):
    """Set up core plugins."""
    # Register core feature plugins
    register_memory_plugins(registry)
    register_llm_plugins(registry)
    register_orchestration_plugins(registry)
    register_tool_plugins(registry)
```

## 4. Plugin Development Documentation

Create comprehensive documentation for plugin development:

1. Plugin types and responsibilities
2. Plugin lifecycle
3. Examples for each plugin type
4. Entry point configuration
5. Testing plugins
6. Distribution guidelines

## 5. Update CLI for Plugin Management

Add CLI commands for plugin management:

```python
# symphony/cli.py - add plugin commands

# Plugin command
plugin_parser = subparsers.add_parser("plugin", help="Plugin management")
plugin_subparsers = plugin_parser.add_subparsers(dest="plugin_command")

# List plugins
plugin_list = plugin_subparsers.add_parser("list", help="List installed plugins")
plugin_list.add_argument("--type", help="Filter by plugin type")

# Install plugin
plugin_install = plugin_subparsers.add_parser("install", help="Install a plugin")
plugin_install.add_argument("plugin", help="Plugin name or path")

# Info about a plugin
plugin_info = plugin_subparsers.add_parser("info", help="Show plugin information")
plugin_info.add_argument("plugin", help="Plugin name")
```

## 6. Plugin Testing Framework

Create a testing framework for plugins:

```python
# symphony/testing/plugin.py

class PluginTestCase:
    """Base class for plugin tests."""
    
    async def setup_plugin(self, plugin_class):
        """Set up a plugin for testing."""
        # Create test registry, container, and event bus
        registry = ServiceRegistry()
        container = Container()
        event_bus = EventBus()
        
        # Register services
        registry.register_service("container", container)
        registry.register_service("event_bus", event_bus)
        
        # Create and initialize plugin
        plugin = plugin_class()
        plugin.initialize(container, event_bus, registry)
        
        return plugin, registry, container, event_bus
```

## 7. Plugin Configuration System

Implement a configuration system for plugins:

```python
# symphony/core/plugin_config.py

class PluginConfig:
    """Configuration for a Symphony plugin."""
    
    def __init__(self, plugin_name: str):
        """Initialize plugin configuration.
        
        Args:
            plugin_name: Name of the plugin
        """
        self.plugin_name = plugin_name
        self.settings = {}
        
    def load(self):
        """Load configuration from file."""
        # Load from standard locations (global, user, project)
        pass
        
    def save(self):
        """Save configuration to file."""
        pass
```

## 8. Plugin Versioning and Compatibility

Implement plugin versioning and compatibility checking:

```python
# symphony/core/plugin.py - add to Plugin class

@property
def symphony_version_required(self) -> str:
    """Get the minimum Symphony version required for this plugin.
    
    Returns:
        Minimum version string (semver)
    """
    return "0.1.0"

def check_compatibility(self, symphony_version: str) -> bool:
    """Check if plugin is compatible with a Symphony version.
    
    Args:
        symphony_version: Symphony version to check against
        
    Returns:
        True if compatible, False otherwise
    """
    # Use semver to compare versions
    return parse_version(symphony_version) >= parse_version(self.symphony_version_required)
```