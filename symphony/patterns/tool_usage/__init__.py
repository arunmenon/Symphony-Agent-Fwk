"""Tool usage patterns for Symphony.

This module provides patterns for tool usage,
such as multi-tool chains, verify-and-execute, and recursive tool use.
"""

from symphony.patterns.registry import PatternRegistry
from symphony.patterns.tool_usage.multi_tool_chain import MultiToolChainPattern
from symphony.patterns.tool_usage.verify_execute import VerifyExecutePattern
from symphony.patterns.tool_usage.recursive_tool_use import RecursiveToolUsePattern


def register_patterns(registry: PatternRegistry) -> None:
    """Register tool usage patterns with the pattern registry.
    
    Args:
        registry: Pattern registry
    """
    # Multi-tool chain pattern
    registry.register_pattern(
        name="multi_tool_chain",
        factory=lambda config: MultiToolChainPattern(config),
        category="tool_usage",
        description="Chain together multiple tool calls in a sequence",
        schema={
            "type": "object",
            "properties": {
                "tools": {
                    "type": "array",
                    "description": "List of tool configurations to execute in sequence"
                }
            }
        }
    )
    
    # Verify-and-execute pattern
    registry.register_pattern(
        name="verify_execute",
        factory=lambda config: VerifyExecutePattern(config),
        category="tool_usage",
        description="Verify a tool usage plan before execution",
        schema={
            "type": "object",
            "properties": {
                "verification_criteria": {
                    "type": "array",
                    "description": "Criteria for verifying tool usage plan"
                }
            }
        }
    )
    
    # Recursive tool use pattern
    registry.register_pattern(
        name="recursive_tool_use",
        factory=lambda config: RecursiveToolUsePattern(config),
        category="tool_usage",
        description="Recursively decompose problems into tool-solvable sub-problems",
        schema={
            "type": "object",
            "properties": {
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum recursion depth"
                }
            }
        }
    )