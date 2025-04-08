#!/usr/bin/env python
"""
Run the full Taxonomy Planner pipeline: generation, analysis, and visualization.

This script provides a convenient way to generate taxonomies, analyze their performance,
and create visualizations all in one step.
"""

import os
import sys
import asyncio
import argparse
import logging
import glob
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"taxonomy_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def run_generation(categories: List[str], base_dir: str, args: Dict[str, Any]) -> bool:
    """Run the taxonomy generation step.
    
    Args:
        categories: List of categories to generate taxonomies for
        base_dir: Base directory for outputs
        args: Additional arguments for generation
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Starting taxonomy generation for: {', '.join(categories)}")
    
    # Import the generate_multiple module to run generation
    try:
        # Add parent directory to sys.path if needed
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import the generate_multiple module
        from generate_multiple import generate_taxonomies
        
        # Set up output directories
        output_dir = os.path.join(base_dir, "taxonomies")
        storage_dir = os.path.join(base_dir, "storage")
        
        # Run generation
        await generate_taxonomies(
            categories=categories,
            jurisdictions=args.get("jurisdictions", "USA"),
            output_dir=output_dir,
            storage_dir=storage_dir,
            max_depth=args.get("max_depth", 4),
            breadth_limit=args.get("breadth_limit", 10),
            strategy=args.get("strategy", "parallel"),
            planner_model=args.get("planner_model", "o1-mini"),
            explorer_model=args.get("explorer_model", "gpt-4o-mini"),
            compliance_model=args.get("compliance_model", "gpt-4o-mini"),
            legal_model=args.get("legal_model", "gpt-4o-mini")
        )
        
        logger.info(f"Taxonomy generation complete for {len(categories)} categories")
        return True
        
    except Exception as e:
        logger.error(f"Error during taxonomy generation: {e}")
        return False

async def run_analysis(base_dir: str) -> bool:
    """Run the trace analysis step.
    
    Args:
        base_dir: Base directory for outputs
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Starting trace analysis")
    
    try:
        # Find all trace files
        trace_files = glob.glob("traces/taxonomy_generation/trace_*.jsonl")
        
        if not trace_files:
            logger.warning("No trace files found for analysis")
            return False
        
        logger.info(f"Found {len(trace_files)} trace files")
        
        # Set up analysis directory
        analysis_dir = os.path.join(base_dir, "analysis")
        os.makedirs(analysis_dir, exist_ok=True)
        
        # Import the analyze_traces module
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import analyze_traces
        
        # Analyze each trace file
        for trace_file in trace_files:
            try:
                trace_id = os.path.basename(trace_file).replace("trace_", "").replace(".jsonl", "")
                logger.info(f"Analyzing trace file: {trace_file}")
                
                # Load trace data
                events = analyze_traces.load_trace_data(trace_file)
                
                # Run analysis
                analysis = analyze_traces.analyze_model_calls(events)
                
                # Generate visualizations
                report_path = analyze_traces.generate_visualizations(
                    analysis, 
                    analysis_dir, 
                    f"trace_{trace_id}"
                )
                
                logger.info(f"Analysis complete for {trace_file}, report saved to {report_path}")
                
            except Exception as e:
                logger.error(f"Error analyzing trace file {trace_file}: {e}")
        
        logger.info("Trace analysis complete")
        return True
        
    except Exception as e:
        logger.error(f"Error during trace analysis: {e}")
        return False

async def run_visualization(base_dir: str) -> bool:
    """Run the visualization step.
    
    Args:
        base_dir: Base directory for outputs
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Starting taxonomy visualization")
    
    try:
        # Import visualization modules
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from visualize_all import visualize_all_taxonomies
        
        # Set up taxonomy and output directories
        taxonomy_dir = os.path.join(base_dir, "taxonomies")
        visualization_dir = os.path.join(base_dir, "visualizations")
        
        # Run visualization
        html_files = await visualize_all_taxonomies(
            input_dir=taxonomy_dir,
            output_dir=visualization_dir,
            pattern="*_taxonomy.json"
        )
        
        if html_files:
            index_path = [f for f in html_files if f.endswith("index.html")]
            if index_path:
                logger.info(f"Visualization complete! Index page: {index_path[0]}")
            else:
                logger.info(f"Visualization complete! {len(html_files)} HTML files generated")
            return True
        else:
            logger.warning("No visualizations were created")
            return False
        
    except Exception as e:
        logger.error(f"Error during visualization: {e}")
        return False

async def run_pipeline(categories: List[str], base_dir: str, args: Dict[str, Any]) -> bool:
    """Run the full taxonomy pipeline.
    
    Args:
        categories: List of categories to generate taxonomies for
        base_dir: Base directory for outputs
        args: Additional arguments for the pipeline
        
    Returns:
        True if successful, False otherwise
    """
    pipeline_start = time.time()
    
    # Create base directory
    os.makedirs(base_dir, exist_ok=True)
    
    # Step 1: Generation
    generation_success = await run_generation(categories, base_dir, args)
    if not generation_success:
        logger.error("Generation failed, stopping pipeline")
        return False
    
    # Step 2: Analysis
    analysis_success = await run_analysis(base_dir)
    if not analysis_success:
        logger.warning("Analysis failed or no traces found, continuing with visualization")
    
    # Step 3: Visualization
    visualization_success = await run_visualization(base_dir)
    if not visualization_success:
        logger.warning("Visualization failed or no taxonomies found")
    
    # Calculate total time
    pipeline_duration = time.time() - pipeline_start
    
    # Summary
    logger.info(f"Pipeline complete in {pipeline_duration:.2f} seconds")
    logger.info(f"- Generation: {'Success' if generation_success else 'Failed'}")
    logger.info(f"- Analysis: {'Success' if analysis_success else 'Failed or no traces'}")
    logger.info(f"- Visualization: {'Success' if visualization_success else 'Failed or no taxonomies'}")
    
    # Output summary
    logger.info(f"Output directory: {os.path.abspath(base_dir)}")
    logger.info(f"- Taxonomies: {os.path.join(base_dir, 'taxonomies')}")
    logger.info(f"- Analysis: {os.path.join(base_dir, 'analysis')}")
    logger.info(f"- Visualizations: {os.path.join(base_dir, 'visualizations')}")
    
    return generation_success

async def main():
    """Parse arguments and run the pipeline."""
    parser = argparse.ArgumentParser(description="Run the full taxonomy pipeline")
    
    parser.add_argument(
        "categories",
        help="Comma-separated list of categories (e.g., 'Sports,Finance,Technology')"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Base directory for outputs (default: pipeline_output_YYYYMMDD_HHMMSS)",
        default=f"pipeline_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    parser.add_argument(
        "--jurisdictions",
        help="Comma-separated list of jurisdictions (default: USA)",
        default="USA"
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
    
    # Parse arguments
    args = parser.parse_args()
    
    # Extract categories
    categories = [c.strip() for c in args.categories.split(",")]
    
    # Convert args to dict for easier passing
    args_dict = {
        "jurisdictions": args.jurisdictions,
        "max_depth": args.max_depth,
        "breadth_limit": args.breadth_limit,
        "strategy": args.strategy,
        "planner_model": args.planner_model,
        "explorer_model": args.explorer_model,
        "compliance_model": args.compliance_model,
        "legal_model": args.legal_model
    }
    
    # Run the pipeline
    try:
        success = await run_pipeline(categories, args.output_dir, args_dict)
        
        if success:
            logger.info("Pipeline completed successfully!")
            sys.exit(0)
        else:
            logger.error("Pipeline failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())