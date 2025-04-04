"""Reasoning patterns for Symphony.

This module provides patterns for different reasoning approaches,
such as chain-of-thought, tree-of-thought, and step-back reasoning.
"""

from symphony.patterns.reasoning.chain_of_thought import ChainOfThoughtPattern
from symphony.patterns.reasoning.step_back import StepBackPattern
from symphony.patterns.registry import PatternRegistry


def register_patterns(registry: PatternRegistry) -> None:
    """Register reasoning patterns with the pattern registry.
    
    Args:
        registry: Pattern registry
    """
    # Register Chain of Thought pattern
    registry.register_pattern(
        name="chain_of_thought",
        factory=lambda config: ChainOfThoughtPattern(config),
        category="reasoning",
        description="Sequential reasoning with explicit intermediate steps",
        schema={
            "type": "object",
            "properties": {
                "max_iterations": {
                    "type": "integer",
                    "description": "Maximum number of reasoning steps",
                    "default": 5
                },
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to use for reasoning (optional)"
                }
            }
        },
        metadata={
            "tags": ["reasoning", "step-by-step", "logical"],
            "example_query": "Solve the following problem step by step: If a triangle has sides of length 3, 4, and 5, what is its area?"
        }
    )
    
    # Register Step Back pattern
    registry.register_pattern(
        name="step_back",
        factory=lambda config: StepBackPattern(config),
        category="reasoning",
        description="Meta-level analysis before diving into details",
        schema={
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to use for reasoning (optional)"
                }
            }
        },
        metadata={
            "tags": ["reasoning", "meta-analysis", "strategy"],
            "example_query": "How should we approach designing a new social media platform that prioritizes user well-being?"
        }
    )