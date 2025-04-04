"""Core module for Symphony framework."""

from symphony.core.config import ConfigLoader, SymphonyConfig
from symphony.core.container import Container, default_container
from symphony.core.events import Event, EventBus, EventType, default_event_bus
from symphony.core.exceptions import (
    AgentCreationError,
    ConfigurationError,
    LLMClientError,
    MCPError,
    PromptNotFoundError,
    ServiceNotFoundError,
    SymphonyError,
    ToolNotFoundError,
)
from symphony.core.factory import (
    AgentFactory as CoreAgentFactory,
    LLMClientFactory,
    MCPManagerFactory,
    MemoryFactory,
)
from symphony.core.plugin import (
    AgentPlugin,
    LLMPlugin,
    MemoryPlugin,
    OrchestratorPlugin,
    Plugin,
    PluginManager,
    PluginType,
    ToolPlugin,
)

# Import new persistence-related modules
from symphony.core.task import Task, TaskStatus
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.core.agent_factory import AgentFactory
from symphony.core.task_manager import TaskManager
from symphony.core.registry import ServiceRegistry


class Symphony:
    """Main entry point for the Symphony framework."""
    
    def __init__(self, config: SymphonyConfig):
        self.config = config
        self.container = Container()
        self.event_bus = EventBus()
        self.plugin_manager = PluginManager(self.container, self.event_bus)
        
        # Register core services
        self._register_core_services()
    
    def _register_core_services(self) -> None:
        """Register core services in the container."""
        # Register config
        self.container.register("config", self.config)
        
        # Register event bus
        self.container.register("event_bus", self.event_bus)
        
        # Register plugin manager
        self.container.register("plugin_manager", self.plugin_manager)
        
        # Register factories
        self.container.register("agent_factory", AgentFactory)
        self.container.register("llm_client_factory", LLMClientFactory)
        self.container.register("memory_factory", MemoryFactory)
        self.container.register("mcp_manager_factory", MCPManagerFactory)
    
    def initialize(self) -> None:
        """Initialize the framework."""
        # Additional initialization if needed
        pass
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.plugin_manager.cleanup()
    
    def get_container(self) -> Container:
        """Get the service container."""
        return self.container
    
    def get_event_bus(self) -> EventBus:
        """Get the event bus."""
        return self.event_bus
    
    def get_plugin_manager(self) -> PluginManager:
        """Get the plugin manager."""
        return self.plugin_manager
    
    @classmethod
    def create(cls, config_path: str = None) -> 'Symphony':
        """Create a Symphony instance with configuration."""
        # Load configuration
        config = ConfigLoader.load(yaml_path=config_path)
        
        # Create and initialize Symphony
        symphony = cls(config)
        symphony.initialize()
        
        return symphony