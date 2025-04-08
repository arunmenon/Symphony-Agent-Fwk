"""Generate regulatory compliance taxonomies for various regulated domains."""

import os
import asyncio
import json
import logging
import argparse
from typing import Dict, Any, List, Optional

from config import TaxonomyConfig
from main import generate_taxonomy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Default categories for compliance taxonomies
DEFAULT_CATEGORIES = ["Alcohol", "Weapons", "Pharmaceuticals", "Gambling"]

# Default jurisdictions to consider
DEFAULT_JURISDICTIONS = ["USA"]

# Configure default paths
DEFAULT_OUTPUT_DIR = "output/us_jurisdictions"
DEFAULT_STORAGE_DIR = "storage/us_jurisdictions"

# Set default model assignments
DEFAULT_MODELS = {
    "planner": "o1-mini",         # For initial taxonomy planning
    "explorer": "gpt-4o-mini",    # For exploring subcategories
    "compliance": "gpt-4o-mini",  # For mapping regulatory requirements
    "legal": "gpt-4o-mini"        # For mapping applicable laws
}

async def generate_compliance_taxonomy(
    category: str,
    jurisdictions: List[str] = None,
    output_dir: str = None,
    storage_dir: str = None,
    max_depth: int = 4,
    breadth_limit: int = 10,
    strategy: str = "parallel",
    models: Dict[str, str] = None
):
    """Generate a compliance-focused taxonomy for the given category.
    
    Args:
        category: The root category to generate taxonomy for
        jurisdictions: List of jurisdictions to include
        output_dir: Directory to save the generated taxonomy
        storage_dir: Directory to store taxonomy data
        max_depth: Maximum depth of the taxonomy tree
        breadth_limit: Maximum number of subcategories per category
        strategy: Exploration strategy ("parallel", "breadth_first", or "depth_first")
        models: Model assignments for different agents
    
    Returns:
        Generated taxonomy as a dictionary
    """
    # Set defaults
    jurisdictions = jurisdictions or DEFAULT_JURISDICTIONS
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    storage_dir = storage_dir or DEFAULT_STORAGE_DIR
    models = models or DEFAULT_MODELS
    
    logger.info(f"Generating compliance taxonomy for {category}...")
    
    # Create output directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(storage_dir, exist_ok=True)
    
    # Set paths
    category_slug = category.lower().replace(' ', '_')
    output_path = os.path.join(output_dir, f"{category_slug}_taxonomy.json")
    storage_path = os.path.join(storage_dir, f"{category_slug}_store.json")
    
    # Create custom config optimized for compliance
    config = TaxonomyConfig()
    config.max_depth = max_depth
    config.default_jurisdictions = jurisdictions
    
    # Configure patterns for compliance exploration
    config.pattern_configs["recursive_exploration"] = {
        "max_depth": max_depth,
        "breadth_limit": breadth_limit
    }
    
    # Enable search if credentials are available
    if os.environ.get("SERAPI_API_KEY"):
        config.search_config["enable_search"] = True
        logger.info("Search capabilities enabled for compliance research")
    
    # Generate taxonomy
    taxonomy = await generate_taxonomy(
        root_category=category,
        jurisdictions=jurisdictions,
        max_depth=max_depth,
        breadth_limit=breadth_limit,
        strategy=strategy,
        output_path=output_path,
        storage_path=storage_path,
        models=models,
        config=config
    )
    
    # Print summary
    subcategory_count = len(taxonomy.get("subcategories", []))
    logger.info(f"Generated {category} taxonomy with {subcategory_count} top-level categories")
    logger.info(f"Saved to {output_path}")
    
    return taxonomy

async def main():
    """Run the compliance taxonomy generation with command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate regulatory compliance taxonomies")
    parser.add_argument("categories", nargs="?", default=None, 
                        help="Comma-separated list of categories (e.g., 'Alcohol,Weapons')")
    parser.add_argument("--jurisdictions", default="USA",
                        help="Comma-separated jurisdictions (e.g., 'USA,EU,UK')")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="Directory to save taxonomies")
    parser.add_argument("--storage-dir", default=DEFAULT_STORAGE_DIR,
                        help="Directory to store taxonomy data")
    parser.add_argument("--max-depth", type=int, default=4,
                        help="Maximum depth of taxonomy")
    parser.add_argument("--breadth-limit", type=int, default=10,
                        help="Maximum subcategories per category")
    parser.add_argument("--strategy", default="parallel",
                        choices=["parallel", "breadth_first", "depth_first"],
                        help="Exploration strategy")
    
    args = parser.parse_args()
    
    # Parse categories
    if args.categories:
        categories = [cat.strip() for cat in args.categories.split(",")]
    else:
        categories = DEFAULT_CATEGORIES
    
    # Parse jurisdictions
    jurisdictions = [j.strip() for j in args.jurisdictions.split(",")]
    
    logger.info(f"Starting compliance taxonomy generation for: {', '.join(categories)}")
    logger.info(f"Jurisdictions: {', '.join(jurisdictions)}")
    
    # Generate taxonomies sequentially
    for category in categories:
        try:
            await generate_compliance_taxonomy(
                category=category,
                jurisdictions=jurisdictions,
                output_dir=args.output_dir,
                storage_dir=args.storage_dir,
                max_depth=args.max_depth,
                breadth_limit=args.breadth_limit,
                strategy=args.strategy
            )
        except Exception as e:
            logger.error(f"Error generating taxonomy for {category}: {e}")
    
    logger.info("Compliance taxonomy generation complete!")

if __name__ == "__main__":
    asyncio.run(main())