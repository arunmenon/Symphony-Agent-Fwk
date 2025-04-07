"""Example usage of Taxonomy Planner application."""

import asyncio
import json
import os
import logging
from typing import Dict, Any, List, Optional

from symphony import Symphony
from applications.taxonomy_planner import (
    TaxonomyPlanner,
    TaxonomyConfig,
    generate_taxonomy
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def run_example():
    """Run the taxonomy planner example."""
    
    # Define output directory
    output_dir = os.path.join(os.path.dirname(__file__), "../applications/taxonomy_planner/output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Example 1: Generate a technology taxonomy using default settings
    print("\n=== Example 1: Technology Taxonomy ===")
    tech_taxonomy = await generate_taxonomy(
        root_category="Technology",
        output_path=os.path.join(output_dir, "technology_taxonomy.json")
    )
    print(f"Generated Technology taxonomy with {len(tech_taxonomy['subcategories'])} top-level categories")
    
    # Example 2: Generate a pharmaceuticals taxonomy with custom configuration
    print("\n=== Example 2: Pharmaceuticals Taxonomy (Custom Config) ===")
    
    # Create custom config for pharmaceuticals
    pharma_config = TaxonomyConfig()
    pharma_config.max_depth = 3
    pharma_config.default_jurisdictions = ["USA", "EU", "Japan", "International"]
    
    # Add custom knowledge sources
    pharma_config.knowledge_sources.extend(["FDA Database", "EMA Database"])
    
    pharma_taxonomy = await generate_taxonomy(
        root_category="Pharmaceuticals",
        jurisdictions=["USA", "EU", "Japan"],
        max_depth=3,
        output_path=os.path.join(output_dir, "pharma_taxonomy.json"),
        config=pharma_config
    )
    print(f"Generated Pharmaceuticals taxonomy with {len(pharma_taxonomy['subcategories'])} top-level categories")
    
    # Example 3: Using the TaxonomyPlanner class directly
    print("\n=== Example 3: Using TaxonomyPlanner Class ===")
    
    # Create custom config for weapons
    weapons_config = TaxonomyConfig()
    weapons_config.max_depth = 4
    weapons_config.default_jurisdictions = ["USA", "International"]
    
    # Create planner instance
    planner = TaxonomyPlanner(config=weapons_config)
    await planner.setup()
    
    # Generate taxonomy
    weapons_taxonomy = await planner.generate_taxonomy(
        root_category="Weapons",
        jurisdictions=["USA", "EU", "International"],
        output_path=os.path.join(output_dir, "weapons_taxonomy.json")
    )
    print(f"Generated Weapons taxonomy with {len(weapons_taxonomy['subcategories'])} top-level categories")
    
    print("\nAll taxonomies generated successfully!")

if __name__ == "__main__":
    asyncio.run(run_example())