"""Annotation utilities for Symphony.

This module contains decorators and annotations for describing Symphony APIs.
"""

import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Union, cast

F = TypeVar('F', bound=Callable[..., Any])


def api_stable(obj=None, *, since_version: str = "0.1.0", description: Optional[str] = None):
    """Mark a function, class, or method as part of the stable API.
    
    This decorator is used to mark functions, classes, or methods that are part
    of the Symphony stable API. These APIs are guaranteed to be maintained
    across minor versions, with deprecations occurring only at major version
    boundaries.
    
    This decorator does not change the behavior of the decorated object, it
    merely adds metadata that can be used for documentation and introspection.
    
    This decorator can be used in two ways:
    1. As a simple decorator: @api_stable
    2. With arguments: @api_stable(since_version="0.2.0", description="...")
    
    Args:
        obj: The function, class, or method to mark as stable
        since_version: The version when this API was stabilized
        description: Optional description of the API's purpose
    
    Returns:
        The original object, unchanged or a decorator function
    
    Example:
        ```python
        @api_stable
        def my_stable_function():
            pass
            
        @api_stable(since_version="0.2.0", description="Core agent builder")
        class AgentBuilder:
            pass
        ```
    """
    def _mark_as_stable(obj):
        # Store stability information in the object's __dict__ if possible
        # or as an attribute otherwise
        stability_info = {
            "stable": True,
            "since_version": since_version,
            "description": description
        }
        
        if inspect.isclass(obj) or inspect.isfunction(obj) or inspect.ismethod(obj):
            if hasattr(obj, "__dict__") and isinstance(obj.__dict__, dict):
                obj.__dict__["_api_info"] = stability_info
            else:
                setattr(obj, "_api_info", stability_info)
                
        return obj
    
    # If used as @api_stable without parentheses
    if obj is not None:
        return _mark_as_stable(obj)
    
    # If used as @api_stable(since_version=...) with parentheses
    return _mark_as_stable


# Remove the problematic overload, we'll use a different approach
# @overload
# def api_stable(
#     since_version: str = "0.1.0",
#     description: Optional[str] = None
# ) -> Callable[[F], F]:
#     ...


def is_stable_api(obj: Any) -> bool:
    """Check if an object is marked as a stable API.
    
    Args:
        obj: The object to check
        
    Returns:
        True if the object is marked as stable, False otherwise
    """
    if hasattr(obj, "_api_info"):
        info = getattr(obj, "_api_info")
        return isinstance(info, dict) and info.get("stable", False)
    return False


def get_api_info(obj: Any) -> Dict[str, Any]:
    """Get API stability information for an object.
    
    Args:
        obj: The object to get information for
        
    Returns:
        Dictionary with API stability information, or an empty dict if not a stable API
    """
    if hasattr(obj, "_api_info"):
        info = getattr(obj, "_api_info")
        if isinstance(info, dict):
            return info
    return {}