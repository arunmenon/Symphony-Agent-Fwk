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

from ..config import TaxonomyConfig

def register_tools(symphony: Symphony, config: TaxonomyConfig) -> None:
    """Register custom tools with Symphony.
    
    Args:
        symphony: Symphony instance
        config: Taxonomy configuration
    """
    # Register knowledge base tools
    symphony.register_tool("search_knowledge_base", search_knowledge_base)
    symphony.register_tool("domain_knowledge_lookup", domain_knowledge_lookup)
    
    # Register compliance tools
    symphony.register_tool("get_compliance_requirements", get_compliance_requirements)
    
    # Register legal tools
    symphony.register_tool("get_applicable_laws", get_applicable_laws)
    
    # Register search tools
    symphony.register_tool("search_category_info", 
                          lambda category, domain="": search_category_info(
                              category, domain, config=config))
    
    symphony.register_tool("search_subcategories", 
                          lambda category: search_subcategories(
                              category, config=config))
    
    symphony.register_tool("search_compliance_requirements", 
                          lambda category, jurisdiction="": search_compliance_requirements(
                              category, jurisdiction, config=config))
    
    symphony.register_tool("search_legal_requirements", 
                          lambda category, jurisdiction: search_legal_requirements(
                              category, jurisdiction, config=config))