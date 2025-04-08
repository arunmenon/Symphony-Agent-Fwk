#!/usr/bin/env python
"""Generate compliance taxonomies for specified categories with configurable parameters."""

import os
import asyncio
import json
import logging
import argparse
import re
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

import sys
import os

# Fix import issues by adding the current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Now import using local imports
from config import TaxonomyConfig
from main import generate_taxonomy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import our tracing plugin
from llm_tracing_plugin import LLMTracingPlugin

# Create global tracer instance
tracer = LLMTracingPlugin(trace_dir="traces/taxonomy_generation")

# Default jurisdictions
DEFAULT_JURISDICTIONS = ["USA"]

# Configure default storage and output paths
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_STORAGE_DIR = "storage"

# Default models
DEFAULT_MODELS = {
    "planner": "o1-mini",      # Advanced reasoning model for complex planning
    "explorer": "gpt-4o-mini", # Cost-effective for exploration tasks
    "compliance": "gpt-4o-mini", # Good for structured compliance mapping
    "legal": "gpt-4o-mini"       # Good for structured legal mapping
}

# Default parameters
DEFAULT_MAX_DEPTH = 4
DEFAULT_BREADTH_LIMIT = 10
DEFAULT_STRATEGY = "parallel"


async def generate_compliance_taxonomy(
    category: str,
    jurisdictions: List[str] = DEFAULT_JURISDICTIONS,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    storage_dir: str = DEFAULT_STORAGE_DIR,
    max_depth: int = DEFAULT_MAX_DEPTH,
    breadth_limit: int = DEFAULT_BREADTH_LIMIT,
    strategy: str = DEFAULT_STRATEGY,
    models: Dict[str, str] = None
):
    """Generate a compliance-focused taxonomy for the given category.
    
    Args:
        category: The root category to generate taxonomy for
        jurisdictions: List of jurisdictions to consider
        output_dir: Directory to save the taxonomy output
        storage_dir: Directory to save the taxonomy store
        max_depth: Maximum depth of the taxonomy
        breadth_limit: Maximum breadth at each level
        strategy: Exploration strategy (parallel, breadth_first, depth_first)
        models: Model assignments for different agents
    
    Returns:
        The generated taxonomy
    """
    logger.info(f"Generating compliance taxonomy for {category}...")
    logger.info(f"Jurisdictions: {', '.join(jurisdictions)}")
    
    # Create output directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(storage_dir, exist_ok=True)
    
    # Set paths
    output_path = os.path.join(output_dir, f"{category.lower().replace(' ', '_')}_taxonomy.json")
    storage_path = os.path.join(storage_dir, f"{category.lower().replace(' ', '_')}_store.json")
    
    # Set up configuration
    config = TaxonomyConfig()
    
    # Configure search API if available
    serapi_key = os.environ.get("SERAPI_API_KEY")
    if serapi_key:
        config.search_config["api_key"] = serapi_key
        config.search_config["enable_search"] = True
        logger.info("Search capability enabled with SerAPI key")
    else:
        logger.warning("SERAPI_API_KEY not found in environment. Search functionality will be disabled.")
        config.search_config["enable_search"] = False
    
    # Set custom models if provided
    if models:
        for agent_name, model_name in models.items():
            config.set_model_for_agent(agent_name, model_name)
            logger.info(f"Using {model_name} for {agent_name} agent")
    
    # Integrate with Symphony's tracing 
    tracer_id = tracer.session_id
    trace_file = tracer.get_trace_file_path()
    
    try:
        # Use Symphony's workflow-based taxonomy generation
        # This properly integrates all steps including search tools
        taxonomy = await generate_taxonomy(
            root_category=category,
            jurisdictions=jurisdictions,
            max_depth=max_depth,
            breadth_limit=breadth_limit,
            strategy=strategy,
            output_path=output_path,
            storage_path=storage_path,
            config=config,
            models=models or DEFAULT_MODELS
        )
        
        # Create a trace summary file for easy access
        trace_summary_path = os.path.join(os.path.dirname(output_path), f"{category.lower().replace(' ', '_')}_trace.txt")
        with open(trace_summary_path, 'w') as f:
            f.write(f"Taxonomy generation trace for {category}\n")
            f.write(f"Generated at: {datetime.now().isoformat()}\n")
            f.write(f"Model: {config.get_model_for_agent('planner')}\n")
            f.write(f"Jurisdictions: {', '.join(jurisdictions)}\n")
            f.write(f"Output: {output_path}\n")
            f.write(f"Trace file: {trace_file}\n")
            f.write(f"Session ID: {tracer_id}\n")
            
            # Extract search usage from metadata if available
            search_used = taxonomy.get("metadata", {}).get("search_used", False)
            search_results_count = taxonomy.get("metadata", {}).get("search_results_count", 0)
            f.write(f"Search used: {search_used}\n")
            if search_used and search_results_count > 0:
                f.write(f"Search results count: {search_results_count}\n")
        
        # Print summary
        subcategory_count = len(taxonomy.get("subcategories", []))
        logger.info(f"Generated {category} taxonomy with {subcategory_count} top-level categories")
        logger.info(f"Saved to {output_path}")
        logger.info(f"Trace saved to {trace_file}")
        logger.info(f"Trace summary saved to {trace_summary_path}")
        
        # Log search usage if available
        search_used = taxonomy.get("metadata", {}).get("search_used", False)
        search_results_count = taxonomy.get("metadata", {}).get("search_results_count", 0)
        if search_used:
            logger.info(f"Search was used with {search_results_count} search results incorporated")
        else:
            logger.info("Search was not used. To enable search, ensure the SERAPI_API_KEY environment variable is set correctly")
        
        return taxonomy
        
    except Exception as e:
        logger.error(f"Error generating taxonomy with Symphony workflow: {e}")
        
        # Call cleanup to end the tracing session
        tracer.cleanup()
        
        # Re-raise the exception to be handled by the caller
        raise


async def main():
    """Parse arguments and run the taxonomy generation."""
    parser = argparse.ArgumentParser(description="Generate compliance taxonomies")
    
    parser.add_argument(
        "category",
        help="Root category to generate taxonomy for (e.g., 'Nudity', 'Alcohol', 'Weapons')"
    )
    
    parser.add_argument(
        "--jurisdictions",
        help="Comma-separated list of jurisdictions (default: USA)",
        default="USA"
    )
    
    parser.add_argument(
        "--output-dir",
        help=f"Directory to save the taxonomy output (default: {DEFAULT_OUTPUT_DIR})",
        default=DEFAULT_OUTPUT_DIR
    )
    
    parser.add_argument(
        "--storage-dir",
        help=f"Directory to save the taxonomy store (default: {DEFAULT_STORAGE_DIR})",
        default=DEFAULT_STORAGE_DIR
    )
    
    parser.add_argument(
        "--max-depth",
        help=f"Maximum depth of the taxonomy (default: {DEFAULT_MAX_DEPTH})",
        type=int,
        default=DEFAULT_MAX_DEPTH
    )
    
    parser.add_argument(
        "--breadth-limit",
        help=f"Maximum breadth at each level (default: {DEFAULT_BREADTH_LIMIT})",
        type=int,
        default=DEFAULT_BREADTH_LIMIT
    )
    
    parser.add_argument(
        "--strategy",
        help=f"Exploration strategy (parallel, breadth_first, depth_first) (default: {DEFAULT_STRATEGY})",
        choices=["parallel", "breadth_first", "depth_first"],
        default=DEFAULT_STRATEGY
    )
    
    parser.add_argument(
        "--planner-model",
        help=f"Model to use for planner agent (default: {DEFAULT_MODELS['planner']})",
        default=DEFAULT_MODELS["planner"]
    )
    
    parser.add_argument(
        "--explorer-model",
        help=f"Model to use for explorer agent (default: {DEFAULT_MODELS['explorer']})",
        default=DEFAULT_MODELS["explorer"]
    )
    
    parser.add_argument(
        "--compliance-model",
        help=f"Model to use for compliance agent (default: {DEFAULT_MODELS['compliance']})",
        default=DEFAULT_MODELS["compliance"]
    )
    
    parser.add_argument(
        "--legal-model",
        help=f"Model to use for legal agent (default: {DEFAULT_MODELS['legal']})",
        default=DEFAULT_MODELS["legal"]
    )
    
    args = parser.parse_args()
    
    # Process jurisdictions
    jurisdictions = [j.strip() for j in args.jurisdictions.split(",")]
    
    # Set up models
    models = {
        "planner": args.planner_model,
        "explorer": args.explorer_model,
        "compliance": args.compliance_model,
        "legal": args.legal_model
    }
    
    try:
        # Generate taxonomy for the specified category
        await generate_compliance_taxonomy(
            category=args.category,
            jurisdictions=jurisdictions,
            output_dir=args.output_dir,
            storage_dir=args.storage_dir,
            max_depth=args.max_depth,
            breadth_limit=args.breadth_limit,
            strategy=args.strategy,
            models=models
        )
        
        logger.info("Taxonomy generation complete!")
        
    except Exception as e:
        logger.error(f"Error generating taxonomy: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())