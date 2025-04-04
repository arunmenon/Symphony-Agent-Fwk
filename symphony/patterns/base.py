"""Base classes for Symphony patterns.

This module defines the core abstractions for the Symphony Patterns Library.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Union, TypeVar, Generic
from pydantic import BaseModel, Field
import uuid
import json
import asyncio
from datetime import datetime

from symphony.core.registry import ServiceRegistry


class PatternConfig(BaseModel):
    """Configuration for a pattern.
    
    This class represents the configuration for a pattern, including
    parameters that control the pattern's behavior.
    """
    
    name: str
    description: str = ""
    max_iterations: int = 1
    timeout_seconds: Optional[int] = None
    threshold: float = 0.0
    agent_roles: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatternConfig":
        """Create a PatternConfig from a dictionary."""
        return cls(**data)


class PatternContext:
    """Context for pattern execution.
    
    This class provides a shared state for pattern execution, including
    input data, intermediate results, and services from the registry.
    """
    
    def __init__(
        self,
        inputs: Dict[str, Any] = None,
        service_registry: Optional[ServiceRegistry] = None,
        parent_context: Optional["PatternContext"] = None
    ):
        """Initialize pattern context.
        
        Args:
            inputs: Input data for the pattern
            service_registry: Service registry to use
            parent_context: Parent context for nested patterns
        """
        self.id = str(uuid.uuid4())
        self.inputs = inputs or {}
        self.outputs = {}
        self.metadata = {}
        self.start_time = datetime.now()
        self.end_time = None
        self.error = None
        self.service_registry = service_registry or ServiceRegistry.get_instance()
        self.parent_context = parent_context
        self.child_contexts = []
        
        # Add some metadata
        self.metadata["start_time"] = self.start_time.isoformat()
        self.metadata["context_id"] = self.id
        
    def get_input(self, key: str, default: Any = None) -> Any:
        """Get input by key with optional default."""
        return self.inputs.get(key, default)
    
    def set_output(self, key: str, value: Any) -> None:
        """Set output by key."""
        self.outputs[key] = value
    
    def get_output(self, key: str, default: Any = None) -> Any:
        """Get output by key with optional default."""
        return self.outputs.get(key, default)
    
    def get_service(self, name: str) -> Any:
        """Get service from registry."""
        return self.service_registry.get_service(name)
    
    def get_repository(self, name: str) -> Any:
        """Get repository from registry."""
        return self.service_registry.get_repository(name)
    
    def mark_complete(self, error: Optional[str] = None) -> None:
        """Mark context as complete with optional error."""
        self.end_time = datetime.now()
        self.metadata["end_time"] = self.end_time.isoformat()
        self.metadata["duration_seconds"] = (self.end_time - self.start_time).total_seconds()
        
        if error:
            self.error = error
            self.metadata["error"] = error
    
    def create_child_context(self, inputs: Dict[str, Any] = None) -> "PatternContext":
        """Create a child context for nested pattern execution.
        
        Args:
            inputs: Input data for the child context
            
        Returns:
            Child context
        """
        child = PatternContext(
            inputs=inputs or self.inputs.copy(),
            service_registry=self.service_registry,
            parent_context=self
        )
        self.child_contexts.append(child)
        return child
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        result = {
            "id": self.id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metadata": self.metadata,
            "child_contexts": [c.to_dict() for c in self.child_contexts]
        }
        
        if self.error:
            result["error"] = self.error
            
        return result


class Pattern(ABC):
    """Abstract base class for patterns.
    
    This class defines the interface for all patterns in the Symphony
    Patterns Library. Patterns are reusable components that encapsulate
    common workflows and best practices for agent interactions.
    """
    
    def __init__(self, config: Union[Dict[str, Any], PatternConfig]):
        """Initialize pattern.
        
        Args:
            config: Pattern configuration
        """
        if isinstance(config, dict):
            self.config = PatternConfig.from_dict(config)
        else:
            self.config = config
    
    @abstractmethod
    async def execute(self, context: PatternContext) -> None:
        """Execute the pattern.
        
        This method should be implemented by all pattern classes to
        define the pattern's behavior.
        
        Args:
            context: Execution context
            
        Returns:
            None
        """
        pass
    
    async def run(self, inputs: Dict[str, Any] = None, service_registry: ServiceRegistry = None) -> Dict[str, Any]:
        """Run the pattern with new context.
        
        This method creates a new context, executes the pattern, and
        returns the outputs.
        
        Args:
            inputs: Input data for the pattern
            service_registry: Service registry to use
            
        Returns:
            Pattern outputs
        """
        context = PatternContext(inputs=inputs, service_registry=service_registry)
        
        try:
            # Execute pattern with timeout if specified
            if self.config.timeout_seconds:
                await asyncio.wait_for(
                    self.execute(context),
                    timeout=self.config.timeout_seconds
                )
            else:
                await self.execute(context)
                
            # Mark context as complete
            context.mark_complete()
        except asyncio.TimeoutError:
            context.mark_complete(f"Pattern execution timed out after {self.config.timeout_seconds} seconds")
        except Exception as e:
            context.mark_complete(f"Pattern execution failed: {str(e)}")
        
        return context.outputs
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about the pattern.
        
        Returns:
            Pattern information
        """
        return {
            "name": self.config.name,
            "description": self.config.description,
            "config": self.config.dict(exclude={"name", "description"})
        }


class SequentialPattern(Pattern):
    """Pattern that executes a sequence of sub-patterns.
    
    This pattern executes multiple sub-patterns in sequence, passing
    the outputs of each pattern to the next pattern in the sequence.
    """
    
    def __init__(self, config: Union[Dict[str, Any], PatternConfig], patterns: List[Pattern]):
        """Initialize sequential pattern.
        
        Args:
            config: Pattern configuration
            patterns: List of patterns to execute in sequence
        """
        super().__init__(config)
        self.patterns = patterns
    
    async def execute(self, context: PatternContext) -> None:
        """Execute patterns in sequence.
        
        Args:
            context: Execution context
            
        Returns:
            None
        """
        # Track results for each pattern
        results = []
        
        # Execute each pattern in sequence
        for i, pattern in enumerate(self.patterns):
            # Create child context
            child_context = context.create_child_context()
            child_context.metadata["step_index"] = i
            child_context.metadata["pattern_name"] = pattern.config.name
            
            # Execute pattern
            await pattern.execute(child_context)
            
            # Store results
            results.append(child_context.outputs)
            
            # Pass outputs to next pattern's inputs
            # (for the next iteration of the loop)
            context.inputs.update(child_context.outputs)
        
        # Store all results in context
        context.set_output("results", results)


class ParallelPattern(Pattern):
    """Pattern that executes sub-patterns in parallel.
    
    This pattern executes multiple sub-patterns concurrently and
    collects their outputs.
    """
    
    def __init__(self, config: Union[Dict[str, Any], PatternConfig], patterns: List[Pattern]):
        """Initialize parallel pattern.
        
        Args:
            config: Pattern configuration
            patterns: List of patterns to execute in parallel
        """
        super().__init__(config)
        self.patterns = patterns
    
    async def execute(self, context: PatternContext) -> None:
        """Execute patterns in parallel.
        
        Args:
            context: Execution context
            
        Returns:
            None
        """
        # Create child contexts for each pattern
        child_contexts = []
        for i, pattern in enumerate(self.patterns):
            child_context = context.create_child_context()
            child_context.metadata["parallel_index"] = i
            child_context.metadata["pattern_name"] = pattern.config.name
            child_contexts.append((pattern, child_context))
        
        # Execute patterns in parallel
        await asyncio.gather(
            *[pattern.execute(child_context) for pattern, child_context in child_contexts]
        )
        
        # Collect results
        results = [child_context.outputs for _, child_context in child_contexts]
        context.set_output("results", results)


class ConditionalPattern(Pattern):
    """Pattern that executes one of two sub-patterns based on a condition.
    
    This pattern evaluates a condition and executes either the if_pattern
    or the else_pattern based on the result.
    """
    
    def __init__(
        self,
        config: Union[Dict[str, Any], PatternConfig],
        condition: Callable[[Dict[str, Any]], bool],
        if_pattern: Pattern,
        else_pattern: Optional[Pattern] = None
    ):
        """Initialize conditional pattern.
        
        Args:
            config: Pattern configuration
            condition: Function that evaluates the condition
            if_pattern: Pattern to execute if condition is True
            else_pattern: Pattern to execute if condition is False (optional)
        """
        super().__init__(config)
        self.condition = condition
        self.if_pattern = if_pattern
        self.else_pattern = else_pattern
    
    async def execute(self, context: PatternContext) -> None:
        """Execute pattern based on condition.
        
        Args:
            context: Execution context
            
        Returns:
            None
        """
        # Evaluate condition
        condition_result = self.condition(context.inputs)
        context.metadata["condition_result"] = condition_result
        
        # Create child context
        child_context = context.create_child_context()
        
        # Execute appropriate pattern
        if condition_result:
            child_context.metadata["branch"] = "if"
            child_context.metadata["pattern_name"] = self.if_pattern.config.name
            await self.if_pattern.execute(child_context)
        elif self.else_pattern:
            child_context.metadata["branch"] = "else"
            child_context.metadata["pattern_name"] = self.else_pattern.config.name
            await self.else_pattern.execute(child_context)
        
        # Pass outputs to parent context
        context.outputs.update(child_context.outputs)