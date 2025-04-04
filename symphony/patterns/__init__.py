"""Symphony Patterns Library.

This module provides a library of reusable patterns for agent interactions.
These patterns encapsulate best practices and common workflows for working
with AI agents and can be composed to create complex agent behaviors.
"""

from symphony.patterns.base import Pattern, PatternContext, PatternConfig
from symphony.patterns.registry import PatternRegistry
from symphony.patterns.facade import PatternsFacade
from symphony.patterns.builder import PatternBuilder

# Import pattern categories
from symphony.patterns import reasoning
from symphony.patterns import verification
from symphony.patterns import multi_agent
from symphony.patterns import tool_usage
from symphony.patterns import learning

# Register built-in patterns
def register_patterns(registry=None):
    """Register all built-in patterns with the registry."""
    from symphony.core.registry import ServiceRegistry
    
    if registry is None:
        registry = ServiceRegistry.get_instance()
    
    # Create pattern registry if it doesn't exist
    pattern_registry = registry.services.get("pattern_registry")
    if pattern_registry is None:
        pattern_registry = PatternRegistry()
        registry.register_service("pattern_registry", pattern_registry)
    
    # Register reasoning patterns
    reasoning.register_patterns(pattern_registry)
    
    # Register verification patterns
    verification.register_patterns(pattern_registry)
    
    # Register multi-agent patterns
    multi_agent.register_patterns(pattern_registry)
    
    # Register tool usage patterns
    tool_usage.register_patterns(pattern_registry)
    
    # Register learning patterns
    learning.register_patterns(pattern_registry)
    
    return pattern_registry