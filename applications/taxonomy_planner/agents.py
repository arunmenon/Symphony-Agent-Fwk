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
    agents["planner"] = symphony.create_agent(
        name="TaxonomyPlanner",
        description=(
            "Plans taxonomy structure and coordinates expansion. "
            "Uses search tools to find authoritative classification systems and validate structure."
        ),
        **config.agent_configs["planner"]
    )
    
    # Create explorer agent with search capabilities
    agents["explorer"] = symphony.create_agent(
        name="CategoryExplorer",
        description=(
            "Explores subcategories using depth-first search. "
            "Uses search tools to discover new subcategories and validate existing ones."
        ),
        **config.agent_configs["explorer"]
    )
    
    # Create compliance agent with search capabilities
    agents["compliance"] = symphony.create_agent(
        name="ComplianceMapper",
        description=(
            "Maps compliance requirements to taxonomy nodes. "
            "Uses search tools to find regulatory requirements from authoritative sources."
        ),
        **config.agent_configs["compliance"]
    )
    
    # Create legal agent with search capabilities
    agents["legal"] = symphony.create_agent(
        name="LegalMapper",
        description=(
            "Maps applicable laws to taxonomy nodes. "
            "Uses search tools to find relevant laws and regulations across jurisdictions."
        ),
        **config.agent_configs["legal"]
    )
    
    return agents