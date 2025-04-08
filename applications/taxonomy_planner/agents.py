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
    
    # Get custom tools if available
    custom_tools = getattr(symphony, "_custom_tools", {})
    
    # Create planner agent
    planner_agent = symphony.build_agent()
    planner_agent.create(
        name="TaxonomyPlanner",
        role="Plans taxonomy structure and coordinates expansion",
        instruction_template="Use search tools to find authoritative classification systems and validate structure."
    )
    planner_agent.with_model(config.get_model_for_agent("planner"))
    planner_agent.with_capability("taxonomy_planning")
    
    # Add tools as metadata
    for tool_name, tool_fn in custom_tools.items():
        if tool_name in ["search_knowledge_base", "domain_knowledge_lookup"]:
            planner_agent.with_metadata(f"tool_{tool_name}", tool_fn)
    
    agents["planner"] = planner_agent.build()
    
    # Create explorer agent
    explorer_agent = symphony.build_agent()
    explorer_agent.create(
        name="CategoryExplorer",
        role="Explores subcategories using search tools",
        instruction_template="Discover new subcategories and validate existing ones."
    )
    explorer_agent.with_model(config.get_model_for_agent("explorer"))
    explorer_agent.with_capability("taxonomy_exploration")
    
    # Add tools as metadata
    for tool_name, tool_fn in custom_tools.items():
        if tool_name in ["search_knowledge_base", "search_subcategories", "search_category_info"]:
            explorer_agent.with_metadata(f"tool_{tool_name}", tool_fn)
    
    agents["explorer"] = explorer_agent.build()
    
    # Create compliance agent
    compliance_agent = symphony.build_agent()
    compliance_agent.create(
        name="ComplianceMapper",
        role="Maps compliance requirements to taxonomy nodes",
        instruction_template="Use search tools to find regulatory requirements from authoritative sources."
    )
    compliance_agent.with_model(config.get_model_for_agent("compliance"))
    compliance_agent.with_capability("compliance_mapping")
    
    # Add tools as metadata
    for tool_name, tool_fn in custom_tools.items():
        if tool_name in ["get_compliance_requirements", "search_compliance_requirements"]:
            compliance_agent.with_metadata(f"tool_{tool_name}", tool_fn)
    
    agents["compliance"] = compliance_agent.build()
    
    # Create legal agent
    legal_agent = symphony.build_agent()
    legal_agent.create(
        name="LegalMapper",
        role="Maps applicable laws to taxonomy nodes",
        instruction_template="Use search tools to find relevant laws and regulations across jurisdictions."
    )
    legal_agent.with_model(config.get_model_for_agent("legal"))
    legal_agent.with_capability("legal_mapping")
    
    # Add tools as metadata
    for tool_name, tool_fn in custom_tools.items():
        if tool_name in ["get_applicable_laws", "search_legal_requirements"]:
            legal_agent.with_metadata(f"tool_{tool_name}", tool_fn)
    
    agents["legal"] = legal_agent.build()
    
    return agents