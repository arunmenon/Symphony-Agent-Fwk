"""Agent definitions for Taxonomy Planner."""

from typing import Dict, Any

from symphony import Symphony
from .config import TaxonomyConfig

def create_agents(symphony: Symphony, config: TaxonomyConfig) -> Dict[str, Any]:
    """Create specialized agents for taxonomy generation.
    
    Args:
        symphony: Symphony instance
        config: Taxonomy configuration
        
    Returns:
        Dictionary of created agents
    """
    agents = {}
    
    # Create planner agent with search capabilities
    planner_config = config.agent_configs["planner"].copy()
    # Apply model override if specified
    planner_config["model"] = config.get_model_for_agent("planner")
    agents["planner"] = symphony.create_agent(
        name="TaxonomyPlanner",
        description=(
            "Plans taxonomy structure and coordinates expansion. "
            "Uses search tools to find authoritative classification systems and validate structure."
        ),
        **planner_config
    )
    
    # Create explorer agent with search capabilities
    explorer_config = config.agent_configs["explorer"].copy()
    # Apply model override if specified
    explorer_config["model"] = config.get_model_for_agent("explorer")
    agents["explorer"] = symphony.create_agent(
        name="CategoryExplorer",
        description=(
            "Explores subcategories using depth-first search. "
            "Uses search tools to discover new subcategories and validate existing ones."
        ),
        **explorer_config
    )
    
    # Create compliance agent with search capabilities
    compliance_config = config.agent_configs["compliance"].copy()
    # Apply model override if specified
    compliance_config["model"] = config.get_model_for_agent("compliance")
    agents["compliance"] = symphony.create_agent(
        name="ComplianceMapper",
        description=(
            "Maps compliance requirements to taxonomy nodes. "
            "Uses search tools to find regulatory requirements from authoritative sources."
        ),
        **compliance_config
    )
    
    # Create legal agent with search capabilities
    legal_config = config.agent_configs["legal"].copy()
    # Apply model override if specified
    legal_config["model"] = config.get_model_for_agent("legal")
    agents["legal"] = symphony.create_agent(
        name="LegalMapper",
        description=(
            "Maps applicable laws to taxonomy nodes. "
            "Uses search tools to find relevant laws and regulations across jurisdictions."
        ),
        **legal_config
    )
    
    return agents