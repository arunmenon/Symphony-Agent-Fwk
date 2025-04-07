"""Symphony Packaging Test.

This example demonstrates how to use Symphony with the new packaging structure,
including the plugin system and feature detection.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("symphony_test")

# Import Symphony
from symphony import Symphony
from symphony import has_feature
from symphony.core.plugin import Plugin, PatternPlugin


class TestPlugin(Plugin):
    """A test plugin for Symphony."""
    
    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "test_plugin"
    
    @property
    def version(self) -> str:
        """Get the version of the plugin."""
        return "0.1.0"
    
    @property
    def description(self) -> str:
        """Get the description of the plugin."""
        return "A test plugin for Symphony"
    
    def setup(self) -> None:
        """Set up the plugin."""
        logger.info(f"Plugin {self.name} is being set up")
        self._registry.register_service("test_service", {"test": True})


async def test_symphony_packaging():
    """Test Symphony packaging."""
    logger.info("Starting Symphony packaging test")
    
    # Check feature detection
    logger.info(f"Feature 'openai' available: {has_feature('openai')}")
    logger.info(f"Feature 'anthropic' available: {has_feature('anthropic')}")
    logger.info(f"Feature 'qdrant' available: {has_feature('qdrant')}")
    
    # Initialize Symphony
    symphony = Symphony()
    await symphony.setup(with_plugins=True)
    
    # Register test plugin
    test_plugin = TestPlugin()
    symphony.register_plugin(test_plugin)
    
    # Create a simple agent using the builder pattern
    agent = (symphony.build_agent()
            .create("TestAgent", "Test Agent", 
                   "You are a test agent for Symphony packaging.")
            .with_capabilities(["testing", "examples"])
            .build())
    
    # Save the agent
    agent_id = await symphony.agents.save_agent(agent)
    logger.info(f"Created agent with ID: {agent_id}")
    
    # Create a task
    task = (symphony.build_task()
           .create("Test Task", "A test task for Symphony packaging")
           .with_query("Echo back: Symphony packaging test")
           .for_agent(agent_id)
           .build())
    
    # Execute task
    logger.info("Executing task...")
    result = await symphony.tasks.execute_task(task)
    logger.info(f"Task result: {result.result}")
    
    # Get plugin
    plugin = symphony.get_plugin("test_plugin")
    if plugin:
        logger.info(f"Found plugin: {plugin.name} v{plugin.version}")
    
    logger.info("Symphony packaging test completed successfully")
    return True


if __name__ == "__main__":
    try:
        asyncio.run(test_symphony_packaging())
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)