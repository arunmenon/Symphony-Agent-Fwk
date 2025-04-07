# Symphony Plugin Developer Guide

This guide provides detailed instructions for developing plugins for the Symphony framework. Plugins allow you to extend Symphony with custom components, patterns, integrations, and more.

## Plugin Architecture

Symphony's plugin system is designed to be both flexible and powerful. The architecture consists of:

1. **Plugin Base Classes**: Abstract base classes defining the plugin interface
2. **Plugin Manager**: Manages plugin discovery, loading, and lifecycle
3. **Plugin Registry**: Registers and provides access to plugins
4. **Extension Points**: Well-defined hooks for extending functionality

## Plugin Types

Symphony supports several plugin types, each designed for specific extension points:

| Plugin Type | Purpose | Base Class |
|-------------|---------|------------|
| **AgentPlugin** | Custom agent implementations | `AgentPlugin` |
| **ToolPlugin** | Custom tools and tool integrations | `ToolPlugin` |
| **MemoryPlugin** | Custom memory implementations | `MemoryPlugin` |
| **LLMPlugin** | LLM provider integrations | `LLMPlugin` |
| **OrchestratorPlugin** | Custom orchestration strategies | `OrchestratorPlugin` |
| **PatternPlugin** | Custom interaction patterns | `PatternPlugin` |
| **Extension** | General extensions and utilities | `Plugin` |

## Developing a Plugin Step-by-Step

### 1. Set Up Your Environment

First, set up your development environment:

```bash
# Install Symphony with development dependencies
pip install symphony[dev]

# Create a plugin project
mkdir my-symphony-plugin
cd my-symphony-plugin
```

### 2. Create a Plugin Package

Create a basic package structure:

```
my-symphony-plugin/
├── pyproject.toml
├── README.md
└── my_plugin/
    ├── __init__.py
    └── plugin.py
```

Set up `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=61.0.0", "wheel>=0.37.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-symphony-plugin"
version = "0.1.0"
description = "A custom plugin for Symphony"
authors = [{name = "Your Name", email = "your.email@example.com"}]
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "symphony>=0.1.0",
]

[project.entry-points."symphony.plugins"]
my_plugin = "my_plugin.plugin:MyPlugin"
```

### 3. Implement the Plugin

Create the plugin implementation in `my_plugin/plugin.py`:

```python
from typing import Any, List
from symphony.core.plugin import Plugin

class MyPlugin(Plugin):
    """A custom plugin for Symphony."""
    
    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my_plugin"
    
    @property
    def version(self) -> str:
        """Get the version of the plugin."""
        return "0.1.0"
    
    @property
    def description(self) -> str:
        """Get the description of the plugin."""
        return "A custom plugin for Symphony"
    
    def setup(self) -> None:
        """Set up the plugin.
        
        This method is called when the plugin is loaded. It should register
        any components with the registry and perform any necessary setup.
        """
        # Access registry, container, and event bus
        registry = self._registry
        container = self._container
        event_bus = self._event_bus
        
        # Register a custom service
        registry.register_service("my_service", MyService())
        
        # Log successful setup
        self.logger.info(f"Plugin {self.name} v{self.version} has been set up")
    
    def cleanup(self) -> None:
        """Clean up the plugin.
        
        This method is called when the plugin is unloaded. It should clean up
        any resources used by the plugin.
        """
        # Perform cleanup
        self.logger.info(f"Plugin {self.name} is being cleaned up")


class MyService:
    """A custom service provided by the plugin."""
    
    def do_something(self) -> str:
        """Do something useful."""
        return "Something useful"
```

### 4. Testing Your Plugin

Create a test script to verify your plugin works correctly:

```python
import asyncio
from symphony import Symphony

async def test_plugin():
    # Initialize Symphony
    symphony = Symphony()
    await symphony.setup(with_plugins=True)
    
    # Check if the plugin was loaded
    plugin = symphony.get_plugin("my_plugin")
    if plugin:
        print(f"Plugin loaded: {plugin.name} v{plugin.version}")
        print(f"Description: {plugin.description}")
    else:
        print("Plugin was not loaded")
    
    # Try using the plugin's service
    try:
        service = symphony.registry.get_service("my_service")
        result = service.do_something()
        print(f"Service result: {result}")
    except ValueError:
        print("Could not access the plugin's service")

if __name__ == "__main__":
    asyncio.run(test_plugin())
```

### 5. Install and Test

Install your plugin in development mode:

```bash
pip install -e .
```

Run your test script:

```bash
python test_plugin.py
```

### 6. Distributing Your Plugin

Once your plugin is ready:

1. Update the version in `pyproject.toml`
2. Build your package:
   ```bash
   python -m build
   ```
3. Upload to PyPI:
   ```bash
   python -m twine upload dist/*
   ```

Users can now install your plugin with:

```bash
pip install my-symphony-plugin
```

## Advanced Plugin Development

### Creating a Pattern Plugin

Pattern plugins allow you to add custom interaction patterns to Symphony:

```python
from symphony.core.plugin import PatternPlugin
from symphony.patterns.base import Pattern, PatternContext, PatternConfig

class MyCustomPattern(Pattern):
    """A custom pattern that does something special."""
    
    @property
    def name(self) -> str:
        return "my_custom_pattern"
    
    async def execute(self, context: PatternContext) -> Any:
        # Implementation here
        return {"result": "Pattern executed"}

class MyPatternPlugin(PatternPlugin):
    """A custom pattern plugin."""
    
    @property
    def name(self) -> str:
        return "my_pattern_plugin"
    
    def setup(self) -> None:
        # Get pattern registry
        pattern_registry = self._registry.get_service("pattern_registry")
        
        # Register pattern
        pattern_registry.register_pattern(MyCustomPattern())
```

### Creating a Tool Plugin

Tool plugins add custom tools to Symphony agents:

```python
from typing import List, Callable, Any
from symphony.core.plugin import ToolPlugin

def my_tool(arg1: str, arg2: int = 0) -> str:
    """A custom tool for Symphony agents.
    
    Args:
        arg1: First argument
        arg2: Second argument (default: 0)
        
    Returns:
        Tool result
    """
    return f"Tool result: {arg1}, {arg2}"

class MyToolPlugin(ToolPlugin):
    """A custom tool plugin."""
    
    @property
    def name(self) -> str:
        return "my_tool_plugin"
    
    def get_tools(self) -> List[Callable[..., Any]]:
        """Get the tools provided by this plugin."""
        return [my_tool]
    
    def setup(self) -> None:
        # Register tools with tool registry
        tool_registry = self._registry.get_service("tool_registry")
        
        for tool in self.get_tools():
            tool_registry.register_tool(tool)
```

### Plugin Dependencies

Plugins can depend on other plugins:

```python
class DependentPlugin(Plugin):
    @property
    def name(self) -> str:
        return "dependent_plugin"
    
    @property
    def dependencies(self) -> List[str]:
        return ["base_plugin", "utility_plugin"]
```

### Plugin Configuration

Plugins can use the Symphony configuration system:

```python
def setup(self) -> None:
    # Get configuration from registry
    config = self._registry.get_service("config")
    
    # Get plugin-specific configuration
    plugin_config = getattr(config, self.name, {})
    
    # Use configuration values
    api_key = plugin_config.get("api_key", None)
    endpoint = plugin_config.get("endpoint", "https://default-api.example.com")
    
    # Configure the plugin
    self.client = APIClient(api_key=api_key, endpoint=endpoint)
```

### Event Handling

Plugins can listen for and emit events:

```python
def setup(self) -> None:
    # Subscribe to events
    self._event_bus.subscribe("agent.created", self._on_agent_created)
    self._event_bus.subscribe("task.completed", self._on_task_completed)

def _on_agent_created(self, event: Event) -> None:
    agent_id = event.data.get("agent_id")
    self.logger.info(f"Agent created: {agent_id}")

def _on_task_completed(self, event: Event) -> None:
    task_id = event.data.get("task_id")
    self.logger.info(f"Task completed: {task_id}")
    
    # Emit a custom event
    self._event_bus.emit(Event(
        type="my_plugin.task_processed",
        data={"task_id": task_id}
    ))
```

## Best Practices

1. **Follow Single Responsibility Principle**: Each plugin should have a clear focus
2. **Handle Errors Gracefully**: Catch and log exceptions to prevent failures
3. **Clean Up Resources**: Implement proper cleanup for all resources
4. **Document Your Plugin**: Provide clear documentation on usage and configuration
5. **Follow Symphony API Design**: Match Symphony's API style and conventions
6. **Version Compatibility**: Document Symphony version compatibility requirements
7. **Provide Sensible Defaults**: Make your plugin work well without extensive configuration
8. **Test Thoroughly**: Write tests for your plugin functionality

## Troubleshooting

- **Plugin Not Discovered**: Verify entry point configuration and package installation
- **Plugin Dependencies Missing**: Ensure all dependencies are installed and available
- **Plugin Initialization Errors**: Check logs for detailed error messages
- **Plugin Not Working As Expected**: Enable debug logging to trace execution

## Plugin Development Resources

- [Symphony API Reference](https://symphony.example.com/api)
- [Symphony GitHub Repository](https://github.com/example/symphony)
- [Plugin Examples](https://github.com/example/symphony-plugin-examples)
- [Community Plugins Directory](https://symphony.example.com/plugins)