# Symphony Plugin System

## Overview

The Symphony plugin system allows you to extend Symphony's functionality with custom components, patterns, integrations, and more. It provides a framework for registering, discovering, and managing plugins in a Symphony application.

## Plugin Types

Symphony supports several plugin types, each designed for a specific extension point:

- **AgentPlugin**: Custom agent implementations
- **ToolPlugin**: Custom tools and tool integrations
- **MemoryPlugin**: Custom memory implementations
- **LLMPlugin**: LLM provider integrations
- **OrchestratorPlugin**: Custom orchestration strategies
- **PatternPlugin**: Custom interaction patterns
- **Extension**: General extensions and utilities

## Creating a Plugin

To create a Symphony plugin, you need to:

1. Subclass one of the plugin base classes
2. Implement the required methods
3. Register your plugin with Symphony

Here's a simple example of a custom pattern plugin:

```python
from symphony.core.plugin import PatternPlugin
from symphony.patterns.base import Pattern, PatternContext, PatternConfig

class MyCustomPattern(Pattern):
    """A custom pattern that does something special."""
    
    def __init__(self, config: PatternConfig = None):
        """Initialize the pattern."""
        super().__init__(config)
    
    @property
    def name(self) -> str:
        """Get the name of the pattern."""
        return "my_custom_pattern"
    
    @property
    def description(self) -> str:
        """Get the description of the pattern."""
        return "A custom pattern that does something special"
    
    async def execute(self, context: PatternContext) -> Any:
        """Execute the pattern."""
        # Get input from context
        query = context.get_input("query", "")
        
        # Do something special
        result = f"Processed: {query}"
        
        # Return result
        return {
            "result": result
        }

class MyPatternPlugin(PatternPlugin):
    """My pattern plugin."""
    
    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my_pattern_plugin"
    
    @property
    def version(self) -> str:
        """Get the version of the plugin."""
        return "0.1.0"
    
    @property
    def description(self) -> str:
        """Get the description of the plugin."""
        return "A custom pattern plugin for Symphony"
    
    def setup(self) -> None:
        """Set up the plugin."""
        # Get pattern registry from service registry
        pattern_registry = self._registry.get_service("pattern_registry")
        
        # Register our custom pattern
        pattern_registry.register_pattern(MyCustomPattern())
```

## Distributing Plugins

Plugins can be distributed as Python packages with entry points. To make your plugin available to Symphony, add an entry point in your `pyproject.toml`:

```toml
[project.entry-points."symphony.plugins"]
my_pattern_plugin = "mypackage.plugins:MyPatternPlugin"
```

This allows Symphony to automatically discover your plugin when your package is installed.

## Plugin Discovery

Symphony can discover plugins in several ways:

1. **Entry Points**: Plugins defined with entry points in installed packages
2. **Plugin Directories**: Plugins in user-defined directories
3. **Explicit Registration**: Plugins directly registered in code
4. **Package Scanning**: Plugins discovered by scanning Python packages

## Using Plugins

To use plugins with Symphony:

```python
import asyncio
from symphony import Symphony

async def main():
    # Initialize Symphony with plugins enabled
    symphony = Symphony()
    await symphony.setup(with_plugins=True)
    
    # Register a plugin manually (alternative to entry points)
    from mypackage.plugins import MyPatternPlugin
    symphony.register_plugin(MyPatternPlugin())
    
    # Find a plugin by name
    plugin = symphony.get_plugin("my_pattern_plugin")
    if plugin:
        print(f"Found plugin: {plugin.name} v{plugin.version}")
    
    # Use a pattern provided by a plugin
    result = await symphony.patterns.execute_pattern(
        "my_custom_pattern", 
        {"query": "Hello, world!"}
    )
    print(result)

asyncio.run(main())
```

## Plugin Dependencies

Plugins can depend on other plugins. To define dependencies, override the `dependencies` property:

```python
class DependentPlugin(Plugin):
    @property
    def name(self) -> str:
        return "dependent_plugin"
        
    @property
    def dependencies(self) -> List[str]:
        return ["base_plugin", "utility_plugin"]
        
    def setup(self) -> None:
        # This will only be called if all dependencies are available
        pass
```

Symphony ensures that plugins are loaded in the correct order based on their dependencies.

## Plugin Configuration

Plugins can be configured through the Symphony configuration system. Configuration is available through the `_registry` property during setup:

```python
def setup(self) -> None:
    # Get configuration
    config = self._registry.get_service("config")
    
    # Get plugin-specific configuration
    my_config = getattr(config, "my_plugin", {})
    
    # Use configuration
    logging_enabled = my_config.get("logging_enabled", False)
```

## Plugin Lifecycle

The plugin lifecycle consists of these main stages:

1. **Discovery**: Symphony discovers the plugin
2. **Registration**: The plugin is registered with the plugin manager
3. **Initialization**: The plugin is initialized with required services
4. **Setup**: The plugin's `setup()` method is called
5. **Usage**: The plugin's functionality is used by the application
6. **Cleanup**: The plugin's `cleanup()` method is called when Symphony shuts down

## Best Practices

- Keep plugins focused on a single responsibility
- Document plugin requirements and interfaces
- Provide sensible defaults for plugin configuration
- Handle errors gracefully
- Clean up resources in the `cleanup()` method
- Follow Symphony's API design patterns