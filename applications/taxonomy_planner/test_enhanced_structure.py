#!/usr/bin/env python
"""Test script to demonstrate the enhanced taxonomy structure.

This script generates and saves a sample enhanced taxonomy that shows the enhanced structure
with the new fields. It's for testing and demonstration purposes only.
"""

import os
import json
import logging
import asyncio
import argparse
from datetime import datetime

from persistence import TaxonomyStore

logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def main():
    """Create and save a sample enhanced taxonomy structure."""
    parser = argparse.ArgumentParser(description="Generate a sample enhanced taxonomy")
    
    parser.add_argument(
        "--category",
        help="Root category for the taxonomy",
        default="Alcoholic Beverages"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Directory to save the taxonomy output",
        default="output/test"
    )
    
    args = parser.parse_args()
    root_category = args.category
    output_dir = args.output_dir
    
    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize the storage
    store_path = os.path.join(output_dir, f"{root_category.lower().replace(' ', '_')}_store.json")
    output_path = os.path.join(output_dir, f"{root_category.lower().replace(' ', '_')}_enhanced.json")
    
    logger.info(f"Creating enhanced taxonomy for '{root_category}'")
    
    # Initialize the store
    store = TaxonomyStore(store_path)
    store.clear()  # Start with a clean slate
    
    # Add root node
    store.add_node(root_category, metadata={
        "description": f"Comprehensive taxonomy of {root_category}",
        "enforcement_examples": ["Age verification", "Sales restrictions"],
        "social_media_trends": ["Responsible consumption campaigns"],
        "risk_level": "Medium to High",
        "detection_methods": ["ID verification", "License monitoring"]
    })
    
    # Add subcategories with the enhanced metadata fields
    if root_category.lower() == "alcoholic beverages":
        # Beer category
        store.add_node("Beer", parent=root_category, metadata={
            "description": "Fermented alcoholic beverage made from grains",
            "enforcement_examples": [
                "Age verification at point of sale", 
                "License checks for vendors",
                "Limitations on alcohol content"
            ],
            "social_media_trends": [
                "Craft beer movement", 
                "Beer tasting events",
                "Home brewing communities"
            ],
            "risk_level": "Medium",
            "detection_methods": [
                "ID verification", 
                "License verification",
                "Alcohol content testing"
            ]
        })
        
        # Add subcategories to Beer
        store.add_node("Craft Beer", parent="Beer", metadata={
            "description": "Beer produced by small independent breweries",
            "enforcement_examples": ["Small business license enforcement", "Craft designation requirements"],
            "social_media_trends": ["Local brewery tourism", "Limited releases"],
            "risk_level": "Low",
            "detection_methods": ["Production volume tracking", "Brewery licensing"]
        })
        
        store.add_node("Import Beer", parent="Beer", metadata={
            "description": "Beer imported from foreign countries",
            "enforcement_examples": ["Import duties enforcement", "Foreign regulatory compliance"],
            "social_media_trends": ["International beer clubs", "Beer tourism"],
            "risk_level": "Medium",
            "detection_methods": ["Customs verification", "Import documentation"]
        })
        
        # Wine category
        store.add_node("Wine", parent=root_category, metadata={
            "description": "Fermented beverage made from grapes or other fruits",
            "enforcement_examples": [
                "Import regulations", 
                "Labeling requirements",
                "Appellation of origin enforcement"
            ],
            "social_media_trends": [
                "Wine tasting clubs", 
                "Vineyard tourism",
                "Natural and organic wine trends"
            ],
            "risk_level": "Medium",
            "detection_methods": [
                "Age verification", 
                "Authenticity verification",
                "Chemical analysis for adulterations"
            ]
        })
        
        # Spirits category
        store.add_node("Spirits", parent=root_category, metadata={
            "description": "Distilled alcoholic beverages with higher alcohol content",
            "enforcement_examples": [
                "Proof labeling requirements", 
                "Distribution limitations",
                "Distillery licensing enforcement"
            ],
            "social_media_trends": [
                "Craft cocktail culture", 
                "Home mixology",
                "Premium and limited editions"
            ],
            "risk_level": "High",
            "detection_methods": [
                "Age verification", 
                "Sales tracking",
                "Alcohol content monitoring"
            ]
        })
        
        # Add compliance and legal mappings
        store.add_compliance_mapping("Beer", "USA", {
            "regulations": [
                "TTB Federal regulations",
                "State-specific alcohol regulations",
                "FDA food safety requirements"
            ],
            "agencies": [
                "Alcohol and Tobacco Tax and Trade Bureau (TTB)",
                "State Alcohol Beverage Control (ABC)",
                "Food and Drug Administration (FDA)"
            ]
        })
        
        store.add_legal_mapping("Beer", "USA", {
            "laws": [
                "Federal Alcohol Administration Act",
                "State liquor laws",
                "Local ordinances on sales and consumption"
            ],
            "requirements": [
                "Minimum drinking age enforcement",
                "Licensing for production and sales",
                "Marketing restrictions"
            ]
        })
    
    else:
        # Generic categories for any other domain
        store.add_node("Category 1", parent=root_category, metadata={
            "description": f"Primary subcategory of {root_category}",
            "enforcement_examples": ["Regulatory example 1", "Compliance check example"],
            "social_media_trends": ["Current trend 1", "Emerging trend 2"],
            "risk_level": "Medium",
            "detection_methods": ["Monitoring method 1", "Enforcement approach 2"]
        })
        
        store.add_node("Category 2", parent=root_category, metadata={
            "description": f"Secondary subcategory of {root_category}",
            "enforcement_examples": ["Regulatory example 3", "Compliance check example 4"],
            "social_media_trends": ["Current trend 3", "Emerging trend 4"],
            "risk_level": "Low",
            "detection_methods": ["Monitoring method 3", "Enforcement approach 4"]
        })
    
    # Save the store for future use
    store.save()
    logger.info(f"Saved taxonomy store to {store_path}")
    
    # Generate the full taxonomy
    taxonomy = store.get_taxonomy_tree(root_category)
    
    # Add metadata
    if "metadata" not in taxonomy:
        taxonomy["metadata"] = {}
        
    taxonomy["metadata"].update({
        "generated_at": datetime.now().isoformat(),
        "generated_by": "test_enhanced_structure.py",
        "note": "This is a demonstration of the enhanced taxonomy structure",
        "domain": root_category,
        "compliance_areas": [
            {
                "name": "Age Verification",
                "description": "Ensuring products are only sold to individuals of legal age",
                "importance": "Critical for preventing underage consumption and regulatory compliance"
            },
            {
                "name": "Licensing Requirements",
                "description": "Ensuring all vendors and producers have proper licensing",
                "importance": "Important for tracking and regulating the industry"
            },
            {
                "name": "Content Regulations",
                "description": "Ensuring products meet safety and content standards",
                "importance": "Important for consumer protection and health safety"
            }
        ]
    })
    
    # Save the taxonomy
    with open(output_path, "w") as f:
        json.dump(taxonomy, f, indent=2)
    
    logger.info(f"Enhanced taxonomy saved to {output_path}")
    logger.info(f"The taxonomy contains {len(taxonomy.get('subcategories', []))} top-level categories")
    logger.info("Enhanced fields demonstrated in the output:")
    logger.info("- description")
    logger.info("- enforcement_examples")
    logger.info("- social_media_trends")
    logger.info("- risk_level")
    logger.info("- detection_methods")
    logger.info("- compliance_areas (dynamic generation in metadata)")
    
if __name__ == "__main__":
    asyncio.run(main())