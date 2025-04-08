#!/usr/bin/env python
"""Generate multiple taxonomies in sequence with a single command."""

import os
import sys
import argparse
import asyncio
import logging
import subprocess
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def generate_taxonomies(categories: List[str], 
                        jurisdictions: str = "USA",
                        output_dir: str = "output/multiple",
                        storage_dir: str = "storage/multiple",
                        max_depth: int = 4,
                        breadth_limit: int = 10,
                        strategy: str = "parallel",
                        planner_model: str = "o1-mini",
                        explorer_model: str = "gpt-4o-mini",
                        compliance_model: str = "gpt-4o-mini",
                        legal_model: str = "gpt-4o-mini"):
    """Generate multiple taxonomies in sequence.
    
    Args:
        categories: List of root categories to generate taxonomies for
        jurisdictions: Comma-separated list of jurisdictions
        output_dir: Directory to save taxonomy outputs
        storage_dir: Directory to save taxonomy stores
        max_depth: Maximum depth of the taxonomies
        breadth_limit: Maximum breadth at each level
        strategy: Exploration strategy
        planner_model: Model for planner agent
        explorer_model: Model for explorer agent
        compliance_model: Model for compliance agent
        legal_model: Model for legal agent
    """
    # Create output/storage directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(storage_dir, exist_ok=True)
    
    # Set environment variables if they're not already set
    if "OPENAI_API_KEY" not in os.environ:
        try:
            with open(os.path.expanduser("~/.openai-api-key")) as f:
                os.environ["OPENAI_API_KEY"] = f.read().strip()
        except FileNotFoundError:
            logger.warning("OPENAI_API_KEY not found. Please set it in the environment.")
            
    # Generate each taxonomy in sequence
    for i, category in enumerate(categories):
        logger.info(f"Generating taxonomy {i+1}/{len(categories)}: {category}")
        
        # Build the command
        cmd = [
            "python", "generate_taxonomy.py", category,
            "--jurisdictions", jurisdictions,
            "--output-dir", output_dir,
            "--storage-dir", storage_dir,
            "--max-depth", str(max_depth),
            "--breadth-limit", str(breadth_limit),
            "--strategy", strategy,
            "--planner-model", planner_model,
            "--explorer-model", explorer_model,
            "--compliance-model", compliance_model,
            "--legal-model", legal_model
        ]
        
        # Run the command
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Successfully generated taxonomy for {category}")
                logger.info(f"Output saved to {output_dir}/{category.lower().replace(' ', '_')}_taxonomy.json")
            else:
                logger.error(f"Error generating taxonomy for {category}")
                logger.error(stderr.decode())
                
        except Exception as e:
            logger.error(f"Error running taxonomy generation for {category}: {e}")
    
    logger.info(f"Generated {len(categories)} taxonomies in {output_dir}")

async def main():
    """Parse arguments and run the taxonomy generation."""
    parser = argparse.ArgumentParser(description="Generate multiple taxonomies")
    
    parser.add_argument(
        "categories",
        help="Comma-separated list of categories to generate taxonomies for (e.g., 'Nudity,Alcohol,Weapons')"
    )
    
    parser.add_argument(
        "--jurisdictions",
        help="Comma-separated list of jurisdictions (default: USA)",
        default="USA"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Directory to save taxonomy outputs (default: output/multiple)",
        default="output/multiple"
    )
    
    parser.add_argument(
        "--storage-dir",
        help="Directory to save taxonomy stores (default: storage/multiple)",
        default="storage/multiple"
    )
    
    parser.add_argument(
        "--max-depth",
        help="Maximum depth of the taxonomies (default: 4)",
        type=int,
        default=4
    )
    
    parser.add_argument(
        "--breadth-limit",
        help="Maximum breadth at each level (default: 10)",
        type=int,
        default=10
    )
    
    parser.add_argument(
        "--strategy",
        help="Exploration strategy (default: parallel)",
        choices=["parallel", "breadth_first", "depth_first"],
        default="parallel"
    )
    
    parser.add_argument(
        "--planner-model",
        help="Model for planner agent (default: o1-mini)",
        default="o1-mini"
    )
    
    parser.add_argument(
        "--explorer-model",
        help="Model for explorer agent (default: gpt-4o-mini)",
        default="gpt-4o-mini"
    )
    
    parser.add_argument(
        "--compliance-model",
        help="Model for compliance agent (default: gpt-4o-mini)",
        default="gpt-4o-mini"
    )
    
    parser.add_argument(
        "--legal-model",
        help="Model for legal agent (default: gpt-4o-mini)",
        default="gpt-4o-mini"
    )
    
    args = parser.parse_args()
    
    # Parse categories
    categories = [c.strip() for c in args.categories.split(",")]
    
    try:
        await generate_taxonomies(
            categories=categories,
            jurisdictions=args.jurisdictions,
            output_dir=args.output_dir,
            storage_dir=args.storage_dir,
            max_depth=args.max_depth,
            breadth_limit=args.breadth_limit,
            strategy=args.strategy,
            planner_model=args.planner_model,
            explorer_model=args.explorer_model,
            compliance_model=args.compliance_model,
            legal_model=args.legal_model
        )
    except Exception as e:
        logger.error(f"Error generating taxonomies: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())