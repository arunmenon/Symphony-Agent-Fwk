"""Learning patterns for Symphony.

This module provides patterns for learning,
such as few-shot learning and reflection-based improvement.
"""

from symphony.patterns.registry import PatternRegistry
from symphony.patterns.learning.few_shot import FewShotPattern
from symphony.patterns.learning.reflection import ReflectionPattern, IterativeReflectionPattern


def register_patterns(registry: PatternRegistry) -> None:
    """Register learning patterns with the pattern registry.
    
    Args:
        registry: Pattern registry
    """
    # Few-shot learning pattern
    registry.register_pattern(
        name="few_shot",
        factory=lambda config: FewShotPattern(config),
        category="learning",
        description="Use examples to guide agent behavior",
        schema={
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "description": "Type of task (summarization, classification, etc.)"
                },
                "format_instructions": {
                    "type": "string",
                    "description": "Optional formatting instructions"
                }
            }
        }
    )
    
    # Reflection pattern
    registry.register_pattern(
        name="reflection",
        factory=lambda config: ReflectionPattern(config),
        category="learning",
        description="Enable agent to reflect on and improve its responses",
        schema={
            "type": "object",
            "properties": {
                "criteria": {
                    "type": "array",
                    "description": "Evaluation criteria for reflection"
                }
            }
        }
    )
    
    # Iterative reflection pattern
    registry.register_pattern(
        name="iterative_reflection",
        factory=lambda config: IterativeReflectionPattern(config),
        category="learning",
        description="Multiple iterations of reflection and improvement",
        schema={
            "type": "object",
            "properties": {
                "iterations": {
                    "type": "integer",
                    "description": "Number of reflection iterations"
                },
                "criteria": {
                    "type": "array",
                    "description": "Evaluation criteria for reflection"
                }
            }
        }
    )