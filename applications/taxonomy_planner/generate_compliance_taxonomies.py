"""Generate compliance taxonomies for Nudity, Alcohol, and Weapons."""

import os
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional

from config import TaxonomyConfig
from main import generate_taxonomy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Categories to generate taxonomies for
CATEGORIES = ["Nudity", "Alcohol", "Weapons"]

# Jurisdictions to consider for compliance and legal mappings
JURISDICTIONS = ["USA", "EU", "UK", "Asia", "International"]

# Configure storage and output paths
OUTPUT_DIR = "output"
STORAGE_DIR = "storage"

# Set model assignments
MODELS = {
    "planner": "openai/gpt-4o",       # Complex reasoning needs powerful model 
    "explorer": "openai/gpt-4-turbo",  # Balanced model for exploration
    "compliance": "openai/gpt-4o",     # Compliance requires better model for regulations
    "legal": "openai/gpt-4o"           # Legal requires better model for law interpretations
}

async def generate_compliance_taxonomy(category: str):
    """Generate a compliance-focused taxonomy for the given category.
    
    Args:
        category: The root category to generate taxonomy for
    """
    logger.info(f"Generating compliance taxonomy for {category}...")
    
    # Create output directories if they don't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(STORAGE_DIR, exist_ok=True)
    
    # Set paths
    output_path = os.path.join(OUTPUT_DIR, f"{category.lower()}_taxonomy.json")
    storage_path = os.path.join(STORAGE_DIR, f"{category.lower()}_store.json")
    
    # Create custom config
    config = TaxonomyConfig()
    config.max_depth = 4  # Go deeper for compliance taxonomies
    config.default_jurisdictions = JURISDICTIONS
    
    # Adjust pattern configs
    config.pattern_configs["recursive_exploration"] = {
        "max_depth": 4,
        "breadth_limit": 10  # Allow more breadth for compliance categories
    }
    
    # Generate taxonomy
    taxonomy = await generate_taxonomy(
        root_category=category,
        jurisdictions=JURISDICTIONS,
        max_depth=4,
        breadth_limit=10,
        strategy="parallel",  # Use parallel for faster generation
        output_path=output_path,
        storage_path=storage_path,
        models=MODELS,
        config=config
    )
    
    # Print summary
    subcategory_count = len(taxonomy.get("subcategories", []))
    logger.info(f"Generated {category} taxonomy with {subcategory_count} top-level categories")
    logger.info(f"Saved to {output_path}")
    
    return taxonomy

async def main():
    """Run the taxonomy generation for all categories."""
    logger.info("Starting compliance taxonomy generation...")
    
    # Generate taxonomies sequentially
    for category in CATEGORIES:
        try:
            await generate_compliance_taxonomy(category)
        except Exception as e:
            logger.error(f"Error generating taxonomy for {category}: {e}")
    
    logger.info("Compliance taxonomy generation complete!")

if __name__ == "__main__":
    asyncio.run(main())