"""Verification patterns for Symphony.

This module provides patterns for verifying outputs, such as
self-consistency checking, critic-review-revise, and hallucination detection.
"""

from symphony.patterns.verification.critic_review import CriticReviewPattern
from symphony.patterns.verification.self_consistency import SelfConsistencyPattern
from symphony.patterns.registry import PatternRegistry


def register_patterns(registry: PatternRegistry) -> None:
    """Register verification patterns with the pattern registry.
    
    Args:
        registry: Pattern registry
    """
    # Register Critic Review pattern
    registry.register_pattern(
        name="critic_review_revise",
        factory=lambda config: CriticReviewPattern(config),
        category="verification",
        description="Multi-agent approach with specialized critic and reviser roles",
        schema={
            "type": "object",
            "properties": {
                "agent_roles": {
                    "type": "object",
                    "properties": {
                        "creator": {"type": "string", "description": "Agent ID for content creation"},
                        "critic": {"type": "string", "description": "Agent ID for criticism"},
                        "reviser": {"type": "string", "description": "Agent ID for revision"}
                    }
                }
            }
        },
        metadata={
            "tags": ["verification", "review", "multi-agent", "quality"],
            "example_content": "Bitcoin was invented in 2004 by Microsoft."
        }
    )
    
    # Register Self Consistency pattern
    registry.register_pattern(
        name="self_consistency",
        factory=lambda config: SelfConsistencyPattern(config),
        category="verification",
        description="Verifying outputs against constraints or known facts",
        schema={
            "type": "object",
            "properties": {
                "num_samples": {
                    "type": "integer",
                    "description": "Number of samples to generate",
                    "default": 3
                },
                "threshold": {
                    "type": "number",
                    "description": "Threshold for consistency (0.0 to 1.0)",
                    "default": 0.7
                },
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to use for verification (optional)"
                }
            }
        },
        metadata={
            "tags": ["verification", "consistency", "reliability"],
            "example_query": "What is the capital of France?"
        }
    )