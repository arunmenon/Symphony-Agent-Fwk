"""Symphony Patterns Library.

This module provides a library of reusable patterns for agent interactions.
These patterns encapsulate best practices and common workflows for working
with AI agents and can be composed to create complex agent behaviors.

Categories of patterns:

1. Reasoning patterns - Enhance agent reasoning capabilities
   - ChainOfThought - Step-by-step reasoning
   - StepBack - Abstract problem before solving

2. Verification patterns - Validate and improve outputs
   - SelfConsistency - Generate multiple solutions and find consensus
   - CriticReview - Use a critic to review and improve outputs

3. Multi-agent patterns - Coordinate multiple agents
   - ExpertPanel - Distribute tasks to specialized agents

4. Tool usage patterns - Coordinate agent interactions with tools
   - VerifyExecute - Validate before using tools
   - MultiToolChain - Use multiple tools sequentially
   - RecursiveToolUse - Use tools recursively

5. Learning patterns - Improve agent performance over time
   - FewShot - Learn from examples
   - Reflection - Reflect on performance to improve
"""

# Package version
__version__ = "0.1.0"

# Explicit exports
__all__ = [
    # Base classes
    "Pattern", "PatternContext", "PatternConfig", 
    "PatternRegistry", "PatternsFacade", "PatternBuilder",
    
    # Composition patterns
    "SequentialPattern", "ParallelPattern", "ConditionalPattern",
    
    # Registration function
    "register_patterns",
    
    # Pattern categories
    "reasoning", "verification", "multi_agent", "tool_usage", "learning",
    
    # Direct pattern exports
    "ChainOfThoughtPattern", "StepBackPattern",
    "CriticReviewPattern", "SelfConsistencyPattern",
    "ExpertPanelPattern",
    "VerifyExecutePattern", "MultiToolChainPattern", "RecursiveToolUsePattern",
    "FewShotPattern", "ReflectionPattern",
]

# Base components
from symphony.patterns.base import (
    Pattern, PatternContext, PatternConfig,
    SequentialPattern, ParallelPattern, ConditionalPattern,
)
from symphony.patterns.registry import PatternRegistry
from symphony.patterns.facade import PatternsFacade
from symphony.patterns.builder import PatternBuilder

# Import pattern categories
from symphony.patterns import reasoning
from symphony.patterns import verification
from symphony.patterns import multi_agent
from symphony.patterns import tool_usage
from symphony.patterns import learning

# Direct imports for common patterns
from symphony.patterns.reasoning.chain_of_thought import ChainOfThoughtPattern
from symphony.patterns.reasoning.step_back import StepBackPattern
from symphony.patterns.verification.critic_review import CriticReviewPattern
from symphony.patterns.verification.self_consistency import SelfConsistencyPattern
from symphony.patterns.multi_agent.expert_panel import ExpertPanelPattern
from symphony.patterns.tool_usage.verify_execute import VerifyExecutePattern
from symphony.patterns.tool_usage.multi_tool_chain import MultiToolChainPattern
from symphony.patterns.tool_usage.recursive_tool_use import RecursiveToolUsePattern
from symphony.patterns.learning.few_shot import FewShotPattern
from symphony.patterns.learning.reflection import ReflectionPattern


# Register built-in patterns
def register_patterns(registry=None):
    """Register all built-in patterns with the registry.
    
    This function registers all built-in patterns with the service registry,
    making them available through the patterns facade.
    
    Args:
        registry: Service registry to register patterns with.
                 If None, the global registry is used.
                 
    Returns:
        PatternRegistry: The pattern registry with all patterns registered.
    """
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