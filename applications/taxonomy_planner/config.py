"""Configuration for Taxonomy Planner."""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class TaxonomyConfig:
    """Configuration for taxonomy generation."""
    
    # Maximum depth of taxonomy
    max_depth: int = 5
    
    # Default jurisdictions if none provided
    default_jurisdictions: List[str] = field(default_factory=lambda: ["USA", "EU", "International"])
    
    # Knowledge sources
    knowledge_sources: List[str] = field(default_factory=lambda: ["internal", "wikipedia"])
    
    # Agent configurations
    agent_configs: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "planner": {
            "preset": "planning",
            "model": "gpt-4",
        },
        "explorer": {
            "preset": "domain_expert",
            "model": "gpt-4",
        },
        "compliance": {
            "preset": "compliance",
            "model": "gpt-4",
        },
        "legal": {
            "preset": "legal",
            "model": "gpt-4",
        }
    })
    
    # Pattern configurations
    pattern_configs: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "chain_of_thought": {
            "reasoning_steps": 5
        },
        "recursive_exploration": {
            "max_depth": 5,
            "breadth_limit": 10
        },
        "search_enhanced": {
            "max_depth": 5,
            "use_search": True
        }
    })
    
    # Domain-specific presets
    domain_presets: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "weapons": {
            "top_level_categories": [
                "Firearms", "Bladed Weapons", "Explosives", 
                "Non-lethal Weapons", "Military Vehicles"
            ],
            "knowledge_sources": ["ATF Database", "Military Equipment Guides"]
        },
        "pharmaceuticals": {
            "top_level_categories": [
                "Prescription Drugs", "Over-the-Counter Drugs", 
                "Controlled Substances", "Medical Devices", "Supplements"
            ],
            "knowledge_sources": ["FDA Database", "Pharmaceutical References"]
        }
    })
    
    # Search configuration
    search_config: Dict[str, Any] = field(default_factory=lambda: {
        "enable_search": True,
        "max_requests_per_minute": 50,
        "results_per_query": 5,
        "search_depth": 3,  # How deep to use search (1=top level only, 5=all levels)
        "max_subcategories_per_search": 10,
        "search_jurisdictions": True,  # Whether to search for jurisdiction-specific info
        "api_key": os.environ.get("SERAPI_API_KEY", "")
    })
    
    def get_domain_preset(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get preset configuration for a specific domain."""
        return self.domain_presets.get(domain.lower())