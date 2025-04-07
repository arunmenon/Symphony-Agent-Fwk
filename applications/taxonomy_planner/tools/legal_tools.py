"""Legal tools for Taxonomy Planner."""

from typing import List, Dict, Any, Optional

# Mock legal database
LEGAL_DB = {
    ("USA", "Firearms"): [
        {"jurisdiction": "USA", "title": "Gun Control Act of 1968"},
        {"jurisdiction": "USA", "title": "National Firearms Act"}
    ],
    ("EU", "Firearms"): [
        {"jurisdiction": "EU", "title": "European Firearms Directive"}
    ],
    ("USA", "Explosives"): [
        {"jurisdiction": "USA", "title": "Federal Explosives Law"}
    ],
}

def get_applicable_laws(category: str, jurisdiction: str) -> List[Dict[str, str]]:
    """Get applicable laws for a category in a jurisdiction.
    
    Args:
        category: Category name
        jurisdiction: Jurisdiction name
        
    Returns:
        List of applicable laws
    """
    return LEGAL_DB.get((jurisdiction, category), [])