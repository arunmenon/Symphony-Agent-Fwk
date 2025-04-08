"""Example usage of Taxonomy Planner application with enhanced features."""

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
    """Run the taxonomy planner example with enhanced features."""
    
    # Define output directory
    output_dir = os.path.join(os.path.dirname(__file__), "../applications/taxonomy_planner/output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Define storage directory for taxonomy store
    storage_dir = os.path.join(os.path.dirname(__file__), "../applications/taxonomy_planner/storage")
    os.makedirs(storage_dir, exist_ok=True)
    
    # Example 1: Generate a technology taxonomy using optimal model assignments
    # with parallel exploration strategy for better performance
    logger.info("\n=== Example 1: Technology Taxonomy with Parallel Exploration ===")
    
    # Define model assignments for different agents
    models = {
        "planner": "openai/gpt-4o",     # Use the most advanced model for planning
        "explorer": "anthropic/claude-3-sonnet",  # Use Claude for exploration
        "compliance": "openai/gpt-4o-mini",  # Use smaller models for simpler tasks
        "legal": "openai/gpt-4o-mini"
    }
    
    # Generate taxonomy with model assignments and parallel exploration
    tech_taxonomy = await generate_taxonomy(
        root_category="Technology",
        strategy="parallel",  # Use parallel exploration for better performance
        breadth_limit=8,     # Limit breadth to prevent explosion
        output_path=os.path.join(output_dir, "technology_taxonomy.json"),
        storage_path=os.path.join(storage_dir, "technology_store.json"),
        models=models
    )
    
    logger.info("Using different models for each agent:")
    for agent, model in models.items():
        logger.info(f"  {agent.capitalize()}: {model}")
        
    logger.info(f"Generated Technology taxonomy with {len(tech_taxonomy['subcategories'])} top-level categories")
    logger.info(f"Exploration strategy: parallel with breadth limit of 8")
    
    # Example 2: Generate a pharmaceuticals taxonomy with depth-first exploration
    # This approaches focuses on deep exploration of a few branches
    logger.info("\n=== Example 2: Pharmaceuticals Taxonomy with Depth-First Exploration ===")
    
    # Create custom config for pharmaceuticals
    pharma_config = TaxonomyConfig()
    pharma_config.max_depth = 4
    pharma_config.default_jurisdictions = ["USA", "EU", "Japan", "International"]
    
    # Add custom knowledge sources
    pharma_config.knowledge_sources.extend(["FDA Database", "EMA Database"])
    
    # Set pattern config for depth-first exploration
    pharma_config.pattern_configs["recursive_exploration"] = {
        "max_depth": 4,
        "breadth_limit": 5  # Lower breadth limit for deeper exploration
    }
    
    # Generate taxonomy with depth-first strategy
    pharma_taxonomy = await generate_taxonomy(
        root_category="Pharmaceuticals",
        jurisdictions=["USA", "EU", "Japan"],
        max_depth=4,
        breadth_limit=5,
        strategy="depth_first",  # Use depth-first exploration
        output_path=os.path.join(output_dir, "pharma_taxonomy.json"),
        storage_path=os.path.join(storage_dir, "pharma_store.json"),
        config=pharma_config
    )
    logger.info(f"Generated Pharmaceuticals taxonomy with {len(pharma_taxonomy['subcategories'])} top-level categories")
    logger.info(f"Exploration strategy: depth-first with depth of 4 and breadth limit of 5")
    
    # Example 3: Using breadth-first exploration for balanced taxonomy
    logger.info("\n=== Example 3: Weapons Taxonomy with Breadth-First Exploration ===")
    
    # Create custom config for weapons
    weapons_config = TaxonomyConfig()
    weapons_config.max_depth = 3
    weapons_config.default_jurisdictions = ["USA", "International"]
    
    # Define model assignments in a clean, declarative way
    models = {
        "planner": "openai/gpt-4o",       # Complex reasoning needs powerful model 
        "explorer": "openai/gpt-4-turbo",  # Balanced model for exploration
        "compliance": "openai/gpt-4o-mini", # Cost-effective for simpler tasks
        "legal": "openai/gpt-4o-mini"       # Cost-effective for simpler tasks
    }
    
    # Apply model assignments to config
    for agent_name, model in models.items():
        weapons_config.set_model_for_agent(agent_name, model)
    
    # Create planner instance
    planner = TaxonomyPlanner(config=weapons_config)
    await planner.setup(storage_path=os.path.join(storage_dir, "weapons_store.json"))
    
    # Log the model assignments
    logger.info("Model assignments:")
    for agent_name, model in models.items():
        logger.info(f"  {agent_name.capitalize()}: {model}")
    
    # Generate taxonomy with breadth-first exploration
    weapons_taxonomy = await planner.generate_taxonomy(
        root_category="Weapons",
        jurisdictions=["USA", "EU", "International"],
        strategy="breadth_first",  # Use breadth-first exploration
        max_depth=3,
        breadth_limit=7,          # Moderate breadth limit for balanced exploration
        output_path=os.path.join(output_dir, "weapons_taxonomy.json")
    )
    logger.info(f"Generated Weapons taxonomy with {len(weapons_taxonomy['subcategories'])} top-level categories")
    logger.info(f"Exploration strategy: breadth-first with depth of 3 and breadth limit of 7")
    
    # Example 4: Demonstrating plan utilization and persistence
    logger.info("\n=== Example 4: Foods Taxonomy with Plan Utilization and Persistence ===")
    logger.info("This example demonstrates how the planner's output is utilized and taxonomy is persisted")
    
    # Create config
    foods_config = TaxonomyConfig()
    foods_config.max_depth = 3
    
    # This would automatically use the plan processing step and TaxonomyStore persistence
    foods_taxonomy = await generate_taxonomy(
        root_category="Foods",
        jurisdictions=["USA", "EU", "Asia"],
        strategy="parallel",
        max_depth=3,
        breadth_limit=6,
        output_path=os.path.join(output_dir, "foods_taxonomy.json"),
        storage_path=os.path.join(storage_dir, "foods_store.json"),
        config=foods_config
    )
    logger.info(f"Generated Foods taxonomy with {len(foods_taxonomy['subcategories'])} top-level categories")
    logger.info(f"Taxonomy persisted to disk at: {os.path.join(storage_dir, 'foods_store.json')}")
    
    # Display summary of enhancements
    logger.info("\n=== Summary of Enhancements ===")
    logger.info("1. Implemented TaxonomyStore with adjacency list structure for efficient persistence")
    logger.info("2. Added plan processing step to utilize planner's strategic output")
    logger.info("3. Improved exploration with parallel processing and breadth limiting")
    logger.info("4. Added support for different exploration strategies (parallel, breadth-first, depth-first)")
    
    logger.info("\nAll taxonomies generated successfully!")

if __name__ == "__main__":
    asyncio.run(run_example())