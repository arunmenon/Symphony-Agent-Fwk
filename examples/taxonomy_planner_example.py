"""Example usage of Taxonomy Planner application with state management."""

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

logger = logging.getLogger(__name__)

async def run_example():
    """Run the taxonomy planner example with state management."""
    
    # Define output directory
    output_dir = os.path.join(os.path.dirname(__file__), "../applications/taxonomy_planner/output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Example 1: Generate a technology taxonomy using default settings
    # Note that we don't need to worry about state management - it's handled automatically
    logger.info("\n=== Example 1: Technology Taxonomy ===")
    tech_taxonomy = await generate_taxonomy(
        root_category="Technology",
        output_path=os.path.join(output_dir, "technology_taxonomy.json")
    )
    logger.info(f"Generated Technology taxonomy with {len(tech_taxonomy['subcategories'])} top-level categories")
    
    # Example 2: Generate a pharmaceuticals taxonomy with custom configuration
    logger.info("\n=== Example 2: Pharmaceuticals Taxonomy (Custom Config) ===")
    
    # Create custom config for pharmaceuticals
    pharma_config = TaxonomyConfig()
    pharma_config.max_depth = 3
    pharma_config.default_jurisdictions = ["USA", "EU", "Japan", "International"]
    
    # Add custom knowledge sources
    pharma_config.knowledge_sources.extend(["FDA Database", "EMA Database"])
    
    # Generate taxonomy - state is automatically persisted and can be resumed
    pharma_taxonomy = await generate_taxonomy(
        root_category="Pharmaceuticals",
        jurisdictions=["USA", "EU", "Japan"],
        max_depth=3,
        output_path=os.path.join(output_dir, "pharma_taxonomy.json"),
        config=pharma_config
    )
    logger.info(f"Generated Pharmaceuticals taxonomy with {len(pharma_taxonomy['subcategories'])} top-level categories")
    
    # Example 3: Using the TaxonomyPlanner class directly with automatic state management
    logger.info("\n=== Example 3: Using TaxonomyPlanner Class ===")
    
    # Create custom config for weapons
    weapons_config = TaxonomyConfig()
    weapons_config.max_depth = 4
    weapons_config.default_jurisdictions = ["USA", "International"]
    
    # Create planner instance - state management is automatically enabled
    planner = TaxonomyPlanner(config=weapons_config)
    await planner.setup()
    
    # Generate taxonomy - if interrupted, it will resume from last checkpoint when run again
    weapons_taxonomy = await planner.generate_taxonomy(
        root_category="Weapons",
        jurisdictions=["USA", "EU", "International"],
        output_path=os.path.join(output_dir, "weapons_taxonomy.json")
    )
    logger.info(f"Generated Weapons taxonomy with {len(weapons_taxonomy['subcategories'])} top-level categories")
    
    # Demonstrate workflow resumption
    logger.info("\n=== Example 4: Resuming from interruption (simulation) ===")
    logger.info("Simulating a new run that would resume from checkpoint if interrupted")
    
    # Create a new planner instance but it will automatically find and resume any in-progress workflows
    resume_planner = TaxonomyPlanner(config=weapons_config)
    await resume_planner.setup()
    
    # This would automatically resume if the previous run was interrupted
    foods_taxonomy = await resume_planner.generate_taxonomy(
        root_category="Foods",
        jurisdictions=["USA", "EU", "Asia"],
        output_path=os.path.join(output_dir, "foods_taxonomy.json")
    )
    logger.info(f"Generated Foods taxonomy with {len(foods_taxonomy['subcategories'])} top-level categories")
    
    logger.info("\nAll taxonomies generated successfully!")

if __name__ == "__main__":
    asyncio.run(run_example())