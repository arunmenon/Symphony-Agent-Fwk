"""Tools for Taxonomy Planner."""

from typing import List, Dict, Any

from symphony import Symphony
from .knowledge_base import search_knowledge_base, domain_knowledge_lookup
from .compliance_tools import get_compliance_requirements
from .legal_tools import get_applicable_laws
from .search_tools import (
    search_category_info,
    search_subcategories,
    search_compliance_requirements,
    search_legal_requirements
)

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TaxonomyConfig

def register_tools(symphony: Symphony, config: TaxonomyConfig) -> None:
    """Register custom tools with Symphony.
    
    Args:
        symphony: Symphony instance
        config: Taxonomy configuration
    """
    # Register tools by adding functions to Symphony's tool registry
    # Since Symphony doesn't have a direct register_tool method, we'll add tools 
    # to Symphony's tool registry via the agents that need them
    
    # Create a dictionary of tools
    tools = {
        "search_knowledge_base": search_knowledge_base,
        "domain_knowledge_lookup": domain_knowledge_lookup,
        "get_compliance_requirements": get_compliance_requirements,
        "get_applicable_laws": get_applicable_laws,
        "search_category_info": lambda category, domain="": search_category_info(
            category, domain, config=config),
        "search_subcategories": lambda category: search_subcategories(
            category, config=config),
        "search_compliance_requirements": lambda category, jurisdiction="": search_compliance_requirements(
            category, jurisdiction, config=config),
        "search_legal_requirements": lambda category, jurisdiction: search_legal_requirements(
            category, jurisdiction, config=config)
    }
    
    # Store tools in the Symphony instance for later use by agents
    if not hasattr(symphony, "_custom_tools"):
        symphony._custom_tools = {}
    
    symphony._custom_tools.update(tools)