"""Base classes and interfaces for tools."""

import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, get_type_hints

from pydantic import BaseModel, create_model


class ToolRegistry:
    """Registry of tools available to agents."""
    
    _tools: Dict[str, "Tool"] = {}
    
    @classmethod
    def register(cls, tool: "Tool") -> None:
        """Register a tool in the registry."""
        cls._tools[tool.name] = tool
    
    @classmethod
    def get(cls, name: str) -> Optional["Tool"]:
        """Get a tool from the registry."""
        return cls._tools.get(name)
    
    @classmethod
    def list_tools(cls) -> List[str]:
        """List all registered tools."""
        return list(cls._tools.keys())


class Tool:
    """Interface for a tool that can be used by an agent."""
    
    def __init__(
        self,
        name: str,
        description: str,
        function: Callable,
        schema: Optional[Type[BaseModel]] = None,
    ):
        self.name = name
        self.description = description
        self.function = function
        self.schema = schema or self._infer_schema(function)
    
    def __call__(self, **kwargs: Any) -> Any:
        """Execute the tool function."""
        return self.function(**kwargs)
    
    def _infer_schema(self, function: Callable) -> Type[BaseModel]:
        """Infer a pydantic schema from function signature."""
        sig = inspect.signature(function)
        type_hints = get_type_hints(function)
        fields = {}
        
        for name, param in sig.parameters.items():
            if name == "self":
                continue
                
            annotation = type_hints.get(name, Any)
            default = ... if param.default is param.empty else param.default
            fields[name] = (annotation, default)
        
        return create_model(f"{function.__name__.title()}Schema", **fields)


def tool(name: Optional[str] = None, description: Optional[str] = None):
    """Decorator to register a function as a tool."""
    
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or ""
        
        tool_instance = Tool(
            name=tool_name,
            description=tool_description,
            function=func,
        )
        
        ToolRegistry.register(tool_instance)
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        
        wrapper.tool = tool_instance
        return wrapper
    
    return decorator