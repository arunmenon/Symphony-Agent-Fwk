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

# Add the parent directory of 'applications' to Python path
symphony_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, symphony_root)

# Now import using the proper paths
from applications.taxonomy_planner.config import TaxonomyConfig
# Import is kept for compatibility, but we're using direct model calls now
# from applications.taxonomy_planner.main import generate_taxonomy

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
    
    # Since the Symphony integration is still having issues,
    # we'll generate a real taxonomy using the specified models directly
    # This will use the actual models to generate content
    
    # Determine the appropriate model to use
    actual_models = models or DEFAULT_MODELS
    planner_model = actual_models.get("planner", "o1-mini")
    
    # Call OpenAI directly to plan the taxonomy structure
    import openai
    from openai import OpenAI
    
    # Import necessary libraries
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
        
    client = OpenAI(api_key=openai_api_key)
    
    # Plan the taxonomy structure
    planning_prompt = f"""
    Create a comprehensive taxonomy for {category}. 
    
    Your task is to develop a hierarchical taxonomy with the following characteristics:
    1. Start with {category} as the root node
    2. Create main subcategories that cover the domain thoroughly
    3. For each subcategory, provide 3-5 sub-subcategories
    4. Focus on creating a well-structured classification system
    5. Consider regulatory and compliance aspects for {', '.join(jurisdictions)}
    
    Format your taxonomy as a nested JSON structure with:
    - A 'name' field for each category
    - A 'subcategories' array containing child categories
    - A 'compliance' object with jurisdiction-specific regulatory information
    - A 'legal' object with jurisdiction-specific legal requirements
    
    Start with 5-8 top-level categories under {category}.
    """
    
    # Make the API call to generate the taxonomy
    logger.info(f"Using {planner_model} to plan the taxonomy structure...")
    
    # Create an internal function to handle model-specific parameter differences
    @tracer.trace_model_call
    async def _generate_taxonomy_with_model(model_name, prompt_text):
        """Internal function to generate taxonomy using the appropriate model with correct parameters."""
        system_message = "You are a specialized AI assistant for creating detailed taxonomies with compliance and legal mappings."
        
        # Model-specific handling
        if "o1" in model_name:
            # o1 models have specific requirements
            logger.info("Using o1-specific parameters")
            # Only provide parameters that are supported by o1 models
            return client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": system_message + "\n\n" + prompt_text}]
            )
        else:
            # Standard handling for other models (GPT, etc.)
            logger.info("Using standard parameters")
            return client.chat.completions.create(
                model=model_name,
                temperature=0.7,
                max_tokens=4000,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt_text}
                ]
            )
    
    # Call the internal function with appropriate parameters
    response = await _generate_taxonomy_with_model(planner_model, planning_prompt)
    
    taxonomy_json = response.choices[0].message.content
    
    # Try to extract the JSON structure from the response
    try:
        # Look for JSON structure in the text
        import re
        import json
        
        # Trace the raw model response
        tracer.log_event("json_extraction_start", {
            "raw_response": taxonomy_json[:1000] + "..." if len(taxonomy_json) > 1000 else taxonomy_json
        })
        
        # Try to find JSON block if it's not a pure JSON response
        json_match = re.search(r'```json\n([\s\S]*?)\n```', taxonomy_json)
        if json_match:
            taxonomy_json = json_match.group(1)
            tracer.log_event("json_block_extracted", {
                "extracted_json": taxonomy_json[:1000] + "..." if len(taxonomy_json) > 1000 else taxonomy_json
            })
        
        # Clean up any potential issues
        taxonomy_json = taxonomy_json.strip()
        
        # Parse the JSON
        taxonomy = json.loads(taxonomy_json)
        
        # Trace successful parsing
        tracer.log_event("json_parsing_success", {
            "category_count": len(taxonomy.get("subcategories", [])),
            "taxonomy_structure": {
                "name": taxonomy.get("name"),
                "subcategories_count": len(taxonomy.get("subcategories", [])),
                "has_compliance": "compliance" in taxonomy,
                "has_legal": "legal" in taxonomy
            }
        })
    except Exception as e:
        # If parsing fails, create a simple taxonomy structure with the content
        logger.warning(f"Couldn't parse the model output as JSON: {e}")
        
        # Trace parsing failure
        tracer.log_event("json_parsing_error", {
            "error": str(e),
            "raw_excerpt": taxonomy_json[:500] + "..." if len(taxonomy_json) > 500 else taxonomy_json
        })
        
        taxonomy = {
            "name": category,
            "description": "Generated taxonomy",
            "subcategories": [],
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": planner_model,
                "jurisdictions": jurisdictions
            }
        }
        
        # Add the raw response as a field for reference
        taxonomy["raw_response"] = taxonomy_json
    
    # Add metadata if it doesn't exist
    if "metadata" not in taxonomy:
        taxonomy["metadata"] = {}
    
    # Update metadata
    taxonomy["metadata"].update({
        "generated_at": datetime.now().isoformat(),
        "model": planner_model,
        "max_depth": max_depth,
        "breadth_limit": breadth_limit,
        "strategy": strategy,
        "jurisdictions": jurisdictions
    })
    
    # Save the taxonomy to the specified output path
    with open(output_path, 'w') as f:
        json.dump(taxonomy, f, indent=2)
    
    # Log the final taxonomy output event
    tracer.log_event("taxonomy_output", {
        "category": category,
        "output_path": output_path,
        "subcategory_count": len(taxonomy.get("subcategories", [])),
        "total_nodes": sum(len(cat.get("subcategories", [])) for cat in taxonomy.get("subcategories", [])) + len(taxonomy.get("subcategories", [])) + 1
    })
    
    # Call cleanup to end the tracing session
    tracer.cleanup()
    
    # Get trace file path
    trace_file = tracer.get_trace_file_path()
    
    # Create a trace summary file for easy access
    trace_summary_path = os.path.join(os.path.dirname(output_path), f"{category.lower().replace(' ', '_')}_trace.txt")
    with open(trace_summary_path, 'w') as f:
        f.write(f"Taxonomy generation trace for {category}\n")
        f.write(f"Generated at: {datetime.now().isoformat()}\n")
        f.write(f"Model: {planner_model}\n")
        f.write(f"Jurisdictions: {', '.join(jurisdictions)}\n")
        f.write(f"Output: {output_path}\n")
        f.write(f"Trace file: {trace_file}\n")
        f.write(f"Session ID: {tracer.session_id}\n")
    
    # Print summary
    subcategory_count = len(taxonomy.get("subcategories", []))
    logger.info(f"Generated {category} taxonomy with {subcategory_count} top-level categories")
    logger.info(f"Saved to {output_path}")
    logger.info(f"Trace saved to {trace_file}")
    logger.info(f"Trace summary saved to {trace_summary_path}")
    
    return taxonomy


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