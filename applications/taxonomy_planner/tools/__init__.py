"""Tools for Taxonomy Planner."""

from typing import List, Dict, Any

# Use stable API imports
from symphony.api import Symphony
# Need to import Tool class from internal modules since not in stable API
from symphony.tools.base import Tool
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
# Use direct import instead of absolute import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TaxonomyConfig

def register_tools(symphony: Symphony, config: TaxonomyConfig) -> None:
    """Register custom tools with Symphony.
    
    Args:
        symphony: Symphony instance
        config: Taxonomy configuration
    """
    # Create tools to register
    tools_to_register = [
        Tool(
            name="search_knowledge_base",
            description="Search internal knowledge base for information",
            function=search_knowledge_base
        ),
        Tool(
            name="domain_knowledge_lookup",
            description="Look up domain-specific knowledge",
            function=domain_knowledge_lookup
        ),
        Tool(
            name="get_compliance_requirements",
            description="Get compliance requirements for a category",
            function=get_compliance_requirements
        ),
        Tool(
            name="get_applicable_laws",
            description="Get applicable laws for a category",
            function=get_applicable_laws
        ),
        Tool(
            name="search_category_info",
            description="Search for information about a category",
            function=lambda category, domain="": search_category_info(
                category, domain, config=config)
        ),
        Tool(
            name="search_subcategories",
            description="Search for subcategories of a category",
            function=lambda category: search_subcategories(
                category, config=config)
        ),
        Tool(
            name="search_compliance_requirements",
            description="Search for compliance requirements",
            function=lambda category, jurisdiction="": search_compliance_requirements(
                category, jurisdiction, config=config)
        ),
        Tool(
            name="search_legal_requirements",
            description="Search for legal requirements",
            function=lambda category, jurisdiction: search_legal_requirements(
                category, jurisdiction, config=config)
        )
    ]
    
    # Register tools using Symphony
    # In Symphony 0.1.0a3, tools are registered directly with the Symphony instance
    for tool in tools_to_register:
        symphony.registry.register_service(f"tool_{tool.name}", tool)
    
    # For backward compatibility, also store tools in Symphony instance
    if not hasattr(symphony, "_custom_tools"):
        symphony._custom_tools = {}
    
    symphony._custom_tools.update({
        tool.name: tool.function for tool in tools_to_register
    })