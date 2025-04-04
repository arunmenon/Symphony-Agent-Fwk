"""Multi-agent patterns for Symphony.

This module provides patterns for multi-agent interactions,
such as expert panels, debates, and cooperative problem-solving.
"""

from symphony.patterns.multi_agent.expert_panel import ExpertPanelPattern
from symphony.patterns.registry import PatternRegistry


def register_patterns(registry: PatternRegistry) -> None:
    """Register multi-agent patterns with the pattern registry.
    
    Args:
        registry: Pattern registry
    """
    # Register Expert Panel pattern
    registry.register_pattern(
        name="expert_panel",
        factory=lambda config: ExpertPanelPattern(config),
        category="multi_agent",
        description="Multiple specialized agents addressing different aspects of a problem",
        schema={
            "type": "object",
            "properties": {
                "perspectives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of expert perspectives to include"
                },
                "agent_roles": {
                    "type": "object",
                    "properties": {
                        "moderator": {"type": "string", "description": "Agent ID for moderation"},
                        "synthesizer": {"type": "string", "description": "Agent ID for synthesis"}
                    }
                }
            },
            "required": ["perspectives"]
        },
        metadata={
            "tags": ["multi-agent", "panel", "expertise", "diversity"],
            "example_query": "What are the most promising approaches to mitigate climate change in the next decade?",
            "example_perspectives": ["economic", "technological", "political", "social"]
        }
    )