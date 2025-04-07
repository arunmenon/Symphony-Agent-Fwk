"""Core module for Symphony framework.

This module provides the core components of the Symphony framework,
including configuration, dependency injection, event handling, and
service registration.
"""

# Module version
__version__ = "0.1.0"

# Explicit exports
__all__ = [
    # Configuration
    "ConfigLoader", "SymphonyConfig",
    
    # Dependency injection
    "Container", "default_container",
    
    # Event handling
    "Event", "EventBus", "EventType", "default_event_bus",
    
    # Registry
    "ServiceRegistry",
    
    # Core model classes
    "Task", "TaskStatus", "TaskPriority",
    "AgentConfig", "AgentCapabilities",
    
    # Factories
    "AgentFactory", "CoreAgentFactory", "LLMClientFactory", 
    "MCPManagerFactory", "MemoryFactory",
    
    # Plugin system
    "Plugin", "PluginManager", "PluginType",
    "AgentPlugin", "LLMPlugin", "MemoryPlugin", 
    "OrchestratorPlugin", "PatternPlugin", "ToolPlugin",
    
    # Task management
    "TaskManager",
    
    # Exceptions
    "SymphonyError", "AgentCreationError", "ConfigurationError",
    "LLMClientError", "MCPError", "PromptNotFoundError",
    "ServiceNotFoundError", "ToolNotFoundError",
]

# Configuration
from symphony.core.config import ConfigLoader, SymphonyConfig

# Dependency injection
from symphony.core.container import Container, default_container

# Event handling
from symphony.core.events import Event, EventBus, EventType, default_event_bus

# Exceptions
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

# Factories
from symphony.core.factory import (
    AgentFactory as CoreAgentFactory,
    LLMClientFactory,
    MCPManagerFactory,
    MemoryFactory,
)

# Plugin system
from symphony.core.plugin import (
    AgentPlugin,
    LLMPlugin,
    MemoryPlugin,
    OrchestratorPlugin,
    PatternPlugin,
    Plugin,
    PluginManager,
    PluginType,
    ToolPlugin,
)

# Core models
from symphony.core.task import Task, TaskStatus, TaskPriority
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.core.agent_factory import AgentFactory
from symphony.core.task_manager import TaskManager
from symphony.core.registry import ServiceRegistry