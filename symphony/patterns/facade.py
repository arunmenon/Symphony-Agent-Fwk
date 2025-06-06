"""Facade for working with Symphony patterns.

This module provides a facade for working with Symphony patterns,
providing a clean interface for pattern execution and management.
"""

from typing import Dict, Any, List, Optional
from symphony.core.registry import ServiceRegistry
from symphony.patterns.registry import PatternRegistry
from symphony.patterns.base import Pattern, PatternContext, SequentialPattern, ParallelPattern, ConditionalPattern


class PatternsFacade:
    """Facade for working with Symphony patterns.
    
    This class provides a clean interface for discovering and executing
    patterns, abstracting away the details of the registry pattern.
    """
    
    def __init__(self, registry: ServiceRegistry = None):
        """Initialize patterns facade.
        
        Args:
            registry: Service registry instance (optional)
        """
        self.registry = registry or ServiceRegistry.get_instance()
    
    async def apply_pattern(self, pattern_name: str, inputs: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply a pattern to the given inputs with optional configuration.
        
        Args:
            pattern_name: Pattern name
            inputs: Input data for the pattern
            config: Pattern configuration overrides (optional)
            
        Returns:
            Pattern execution results
            
        Raises:
            ValueError: If pattern registry or pattern is not found
        """
        pattern_registry = self.registry.get_service("pattern_registry")
        if not pattern_registry:
            raise ValueError("Pattern registry not found. Call register_patterns() first.")
            
        pattern = pattern_registry.create_pattern(pattern_name, config)
        return await pattern.run(inputs, self.registry)
    
    def create_pattern(self, pattern_name: str, config: Dict[str, Any] = None) -> Pattern:
        """Create a pattern instance with the given configuration.
        
        Args:
            pattern_name: Pattern name
            config: Pattern configuration (optional)
            
        Returns:
            Pattern instance
            
        Raises:
            ValueError: If pattern registry or pattern is not found
        """
        pattern_registry = self.registry.get_service("pattern_registry")
        if not pattern_registry:
            raise ValueError("Pattern registry not found. Call register_patterns() first.")
            
        return pattern_registry.create_pattern(pattern_name, config)
    
    def compose_sequential(self, patterns: List[Pattern], name: str = "sequential", config: Dict[str, Any] = None) -> SequentialPattern:
        """Compose multiple patterns into a sequential pattern.
        
        Args:
            patterns: List of patterns to execute in sequence
            name: Name for the composed pattern (optional)
            config: Additional configuration (optional)
            
        Returns:
            Sequential pattern instance
        """
        pattern_config = {
            "name": name,
            "description": "Sequential composition of patterns",
            **(config or {})
        }
        
        return SequentialPattern(pattern_config, patterns)
    
    def compose_parallel(self, patterns: List[Pattern], name: str = "parallel", config: Dict[str, Any] = None) -> ParallelPattern:
        """Compose multiple patterns into a parallel pattern.
        
        Args:
            patterns: List of patterns to execute in parallel
            name: Name for the composed pattern (optional)
            config: Additional configuration (optional)
            
        Returns:
            Parallel pattern instance
        """
        pattern_config = {
            "name": name,
            "description": "Parallel composition of patterns",
            **(config or {})
        }
        
        return ParallelPattern(pattern_config, patterns)
    
    def compose_conditional(self, condition: callable, if_pattern: Pattern, else_pattern: Optional[Pattern] = None, name: str = "conditional", config: Dict[str, Any] = None) -> ConditionalPattern:
        """Compose a conditional pattern.
        
        Args:
            condition: Function that evaluates the condition
            if_pattern: Pattern to execute if condition is True
            else_pattern: Pattern to execute if condition is False (optional)
            name: Name for the composed pattern (optional)
            config: Additional configuration (optional)
            
        Returns:
            Conditional pattern instance
        """
        pattern_config = {
            "name": name,
            "description": "Conditional pattern composition",
            **(config or {})
        }
        
        return ConditionalPattern(pattern_config, condition, if_pattern, else_pattern)
    
    async def get_available_patterns(self, category: str = None) -> List[Dict[str, Any]]:
        """Get information about available patterns.
        
        Args:
            category: Filter by category (optional)
            
        Returns:
            List of pattern information
            
        Raises:
            ValueError: If pattern registry is not found
        """
        pattern_registry = self.registry.get_service("pattern_registry")
        if not pattern_registry:
            raise ValueError("Pattern registry not found. Call register_patterns() first.")
            
        return pattern_registry.list_patterns(category)
    
    async def get_pattern_categories(self) -> List[str]:
        """Get list of pattern categories.
        
        Returns:
            List of category names
            
        Raises:
            ValueError: If pattern registry is not found
        """
        pattern_registry = self.registry.get_service("pattern_registry")
        if not pattern_registry:
            raise ValueError("Pattern registry not found. Call register_patterns() first.")
            
        return pattern_registry.get_categories()
    
    async def get_pattern_info(self, pattern_name: str) -> Dict[str, Any]:
        """Get information about a specific pattern.
        
        Args:
            pattern_name: Pattern name
            
        Returns:
            Pattern information
            
        Raises:
            ValueError: If pattern registry or pattern is not found
        """
        pattern_registry = self.registry.get_service("pattern_registry")
        if not pattern_registry:
            raise ValueError("Pattern registry not found. Call register_patterns() first.")
            
        return pattern_registry.get_pattern_info(pattern_name)
    
    # Methods for specific pattern categories
    
    async def apply_reasoning_pattern(self, pattern_name: str, query: str, context: Dict[str, Any] = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply a reasoning pattern to a query.
        
        Args:
            pattern_name: Pattern name
            query: Input query
            context: Additional context information (optional)
            config: Pattern configuration overrides (optional)
            
        Returns:
            Pattern execution results
        """
        inputs = {"query": query}
        if context:
            inputs["context"] = context
            
        return await self.apply_pattern(pattern_name, inputs, config)
    
    async def apply_verification_pattern(self, pattern_name: str, content: str, criteria: List[str] = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply a verification pattern to content.
        
        Args:
            pattern_name: Pattern name
            content: Content to verify
            criteria: Verification criteria (optional)
            config: Pattern configuration overrides (optional)
            
        Returns:
            Pattern execution results
        """
        inputs = {"content": content}
        if criteria:
            inputs["criteria"] = criteria
            
        return await self.apply_pattern(pattern_name, inputs, config)
    
    async def apply_multi_agent_pattern(self, pattern_name: str, input_data: Dict[str, Any], agents: Dict[str, str] = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply a multi-agent pattern.
        
        Args:
            pattern_name: Pattern name
            input_data: Input data for the pattern
            agents: Agent ID mappings (role -> agent_id) (optional)
            config: Pattern configuration overrides (optional)
            
        Returns:
            Pattern execution results
        """
        pattern_config = config or {}
        if agents:
            pattern_config["agent_roles"] = agents
            
        return await self.apply_pattern(pattern_name, input_data, pattern_config)
    
    async def apply_tool_usage_pattern(self, pattern_name: str, query: str, tools: List[Dict[str, Any]] = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply a tool usage pattern.
        
        Args:
            pattern_name: Pattern name
            query: Input query
            tools: List of tool configurations (optional)
            config: Pattern configuration overrides (optional)
            
        Returns:
            Pattern execution results
        """
        inputs = {"query": query}
        if tools:
            inputs["tools"] = tools
            
        return await self.apply_pattern(pattern_name, inputs, config)
    
    async def apply_learning_pattern(self, pattern_name: str, task: str, examples: List[Dict[str, Any]] = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply a learning pattern.
        
        Args:
            pattern_name: Pattern name
            task: Task description
            examples: Learning examples (optional)
            config: Pattern configuration overrides (optional)
            
        Returns:
            Pattern execution results
        """
        inputs = {"task": task}
        if examples:
            inputs["examples"] = examples
            
        return await self.apply_pattern(pattern_name, inputs, config)