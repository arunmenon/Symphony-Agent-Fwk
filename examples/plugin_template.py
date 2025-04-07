"""Symphony Plugin Template.

This example demonstrates how to create a Symphony plugin.
"""

from typing import List, Any, Callable

from symphony.core.plugin import PatternPlugin
from symphony.patterns.base import Pattern, PatternContext, PatternConfig


class MyCustomPattern(Pattern):
    """A custom pattern that does something special."""
    
    def __init__(self, config: PatternConfig = None):
        """Initialize the pattern.
        
        Args:
            config: Pattern configuration
        """
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
        """Execute the pattern.
        
        Args:
            context: Pattern execution context
            
        Returns:
            Pattern result
        """
        # Get input from context
        query = context.get_input("query", "")
        
        # Log the execution
        self.logger.info(f"Executing {self.name} with query: {query}")
        
        # Do something special
        result = f"Processed: {query}"
        
        # Return result
        return {
            "result": result
        }


class MyPatternPlugin(PatternPlugin):
    """My pattern plugin.
    
    This plugin provides a custom pattern for Symphony.
    """
    
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
        """Set up the plugin.
        
        Registers patterns with the pattern registry.
        """
        # Get pattern registry from service registry
        pattern_registry = self._registry.get_service("pattern_registry")
        
        # Register our custom pattern
        pattern_registry.register_pattern(MyCustomPattern())
        
        self.logger.info(f"Registered pattern: {MyCustomPattern().name}")


# This is how you would define an entry point in pyproject.toml:
"""
[project.entry-points."symphony.plugins"]
my_pattern_plugin = "mymodule.plugin_template:MyPatternPlugin"
"""

# To use the plugin programmatically:
"""
from symphony.api import Symphony

# Initialize Symphony
symphony = Symphony()
await symphony.setup()

# Register the plugin manually
from mymodule.plugin_template import MyPatternPlugin
plugin = MyPatternPlugin()
symphony.registry.get_service("plugin_manager").register_plugin(plugin)

# Use the pattern
result = await symphony.patterns.execute_pattern(
    "my_custom_pattern", 
    {"query": "Hello, world!"}
)
print(result)
"""