"""Builder for Symphony patterns.

This module provides a builder for Symphony patterns, providing
a fluent interface for pattern creation and configuration.
"""

from typing import Dict, Any, List, Optional, Union
from symphony.core.registry import ServiceRegistry
from symphony.patterns.base import Pattern, PatternConfig


class PatternBuilder:
    """Builder for Symphony patterns.
    
    This class provides a fluent interface for creating and configuring patterns,
    making it easier to create complex pattern configurations with a clean,
    readable syntax.
    """
    
    def __init__(self, registry: ServiceRegistry = None):
        """Initialize pattern builder.
        
        Args:
            registry: Service registry instance (optional)
        """
        self.registry = registry or ServiceRegistry.get_instance()
        self.pattern_name = None
        self.pattern_config = {}
        self.pattern_inputs = {}
    
    def create(self, pattern_name: str) -> 'PatternBuilder':
        """Create a new pattern.
        
        Args:
            pattern_name: Name of the pattern to create
            
        Returns:
            Self for chaining
        """
        self.pattern_name = pattern_name
        return self
    
    def with_config(self, key: str, value: Any) -> 'PatternBuilder':
        """Add configuration to the pattern.
        
        Args:
            key: Configuration key
            value: Configuration value
            
        Returns:
            Self for chaining
        """
        self.pattern_config[key] = value
        return self
    
    def with_agent(self, role: str, agent_id: str) -> 'PatternBuilder':
        """Assign an agent to a role in the pattern.
        
        Args:
            role: Role name in the pattern
            agent_id: ID of the agent to assign
            
        Returns:
            Self for chaining
        """
        if "agent_roles" not in self.pattern_config:
            self.pattern_config["agent_roles"] = {}
            
        self.pattern_config["agent_roles"][role] = agent_id
        return self
    
    def with_iterations(self, count: int) -> 'PatternBuilder':
        """Set the number of iterations for iterative patterns.
        
        Args:
            count: Number of iterations
            
        Returns:
            Self for chaining
        """
        self.pattern_config["max_iterations"] = count
        return self
    
    def with_timeout(self, seconds: int) -> 'PatternBuilder':
        """Set timeout for pattern execution.
        
        Args:
            seconds: Timeout in seconds
            
        Returns:
            Self for chaining
        """
        self.pattern_config["timeout_seconds"] = seconds
        return self
    
    def with_threshold(self, threshold: float) -> 'PatternBuilder':
        """Set acceptance threshold for the pattern.
        
        Args:
            threshold: Threshold value (0.0 to 1.0)
            
        Returns:
            Self for chaining
        """
        self.pattern_config["threshold"] = threshold
        return self
    
    def with_input(self, key: str, value: Any) -> 'PatternBuilder':
        """Add input data to the pattern.
        
        Args:
            key: Input key
            value: Input value
            
        Returns:
            Self for chaining
        """
        self.pattern_inputs[key] = value
        return self
    
    def with_query(self, query: str) -> 'PatternBuilder':
        """Set the query input for the pattern.
        
        Args:
            query: Query string
            
        Returns:
            Self for chaining
        """
        self.pattern_inputs["query"] = query
        return self
    
    def with_content(self, content: str) -> 'PatternBuilder':
        """Set the content input for the pattern.
        
        Args:
            content: Content string
            
        Returns:
            Self for chaining
        """
        self.pattern_inputs["content"] = content
        return self
    
    def with_metadata(self, key: str, value: Any) -> 'PatternBuilder':
        """Add metadata to the pattern configuration.
        
        Args:
            key: Metadata key
            value: Metadata value
            
        Returns:
            Self for chaining
        """
        if "metadata" not in self.pattern_config:
            self.pattern_config["metadata"] = {}
            
        self.pattern_config["metadata"][key] = value
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the pattern configuration.
        
        Returns:
            Pattern configuration dictionary
            
        Raises:
            ValueError: If pattern type not specified
        """
        if not self.pattern_name:
            raise ValueError("Pattern name not specified. Call create() first.")
            
        return {
            "name": self.pattern_name,
            "config": self.pattern_config,
            "inputs": self.pattern_inputs
        }
    
    async def execute(self) -> Dict[str, Any]:
        """Build and execute the pattern.
        
        Returns:
            Pattern execution results
            
        Raises:
            ValueError: If pattern registry or pattern is not found
        """
        if not self.pattern_name:
            raise ValueError("Pattern name not specified. Call create() first.")
            
        pattern_registry = self.registry.get_service("pattern_registry")
        if not pattern_registry:
            from symphony.patterns import register_patterns
            register_patterns(self.registry)
            pattern_registry = self.registry.get_service("pattern_registry")
            
        pattern = pattern_registry.create_pattern(self.pattern_name, self.pattern_config)
        return await pattern.run(self.pattern_inputs, self.registry)