"""Custom exceptions for the Symphony framework."""


class SymphonyError(Exception):
    """Base exception class for all Symphony errors."""
    pass


class ServiceNotFoundError(SymphonyError):
    """Raised when a requested service is not found in the container."""
    pass


class ToolNotFoundError(SymphonyError):
    """Raised when a requested tool is not found in the registry."""
    pass


class PromptNotFoundError(SymphonyError):
    """Raised when a requested prompt is not found in the registry."""
    pass


class ConfigurationError(SymphonyError):
    """Raised when there is an error in configuration."""
    pass


class AgentCreationError(SymphonyError):
    """Raised when there is an error creating an agent."""
    pass


class LLMClientError(SymphonyError):
    """Raised when there is an error in the LLM client."""
    pass


class MCPError(SymphonyError):
    """Raised when there is an error in the MCP integration."""
    pass