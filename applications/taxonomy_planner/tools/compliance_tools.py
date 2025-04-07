"""Compliance tools for Taxonomy Planner."""

from typing import List, Dict, Any, Optional

# Mock compliance database
COMPLIANCE_DB = {
    "Weapons": ["Arms Trade Regulations", "Safety Standards"],
    "Firearms": ["Licensing Requirements", "Background Checks", "Safe Storage"],
    "Handguns": ["Concealed Carry Permits", "Age Restrictions"],
    "Explosives": ["Storage Permits", "Transportation Permits", "Usage Certification"],
}

def get_compliance_requirements(category: str) -> List[str]:
    """Get compliance requirements for a category.
    
    Args:
        category: Category name
        
    Returns:
        List of compliance requirements
    """
    return COMPLIANCE_DB.get(category, [])