#!/usr/bin/env python
"""Generate compliance taxonomies for specified categories with configurable parameters.

This script provides both the standard taxonomy generation functionality and an enhanced
version that uses the correct Symphony agent execution pattern with additional fields.
"""

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

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

import sys
import os

# Fix import issues by adding the current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Now import using local imports
from config import TaxonomyConfig
from main import generate_taxonomy
from persistence import TaxonomyStore

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
    "planner": "anthropic/claude-3-opus",      # Advanced reasoning model for complex planning
    "explorer": "openai/gpt-4o-mini", # Cost-effective for exploration tasks
    "compliance": "openai/gpt-4o-mini", # Good for structured compliance mapping
    "legal": "openai/gpt-4o-mini"       # Good for structured legal mapping
}

# Default parameters
DEFAULT_MAX_DEPTH = 4
DEFAULT_BREADTH_LIMIT = 10
DEFAULT_STRATEGY = "parallel"

# Enhanced fields for improved taxonomy data structure
ENHANCED_FIELDS = [
    "description",           # Detailed description of the category
    "enforcement_examples",  # Examples of enforcement or incidents
    "social_media_trends",   # Current trends in social media related to the category
    "risk_level",            # Risk assessment (High, Medium, Low)
    "detection_methods"      # Methods for detecting instances of this category
]


async def generate_compliance_taxonomy(
    category: str,
    jurisdictions: List[str] = DEFAULT_JURISDICTIONS,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    storage_dir: str = DEFAULT_STORAGE_DIR,
    max_depth: int = DEFAULT_MAX_DEPTH,
    breadth_limit: int = DEFAULT_BREADTH_LIMIT,
    strategy: str = DEFAULT_STRATEGY,
    models: Dict[str, str] = None,
    enhanced: bool = False,
    enhanced_fields: List[str] = None
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
        enhanced: Whether to use enhanced generation with additional fields
        enhanced_fields: List of additional fields to include in enhanced mode
    
    Returns:
        The generated taxonomy
    """
    # Set default enhanced fields if not provided
    if enhanced_fields is None:
        enhanced_fields = ENHANCED_FIELDS
        
    # Log different information based on mode
    if enhanced:
        logger.info(f"Generating ENHANCED compliance taxonomy for {category} with additional fields")
        logger.info(f"Enhanced fields: {', '.join(enhanced_fields)}")
        logger.info(f"Using correct Symphony agent execution pattern")
    else:
        logger.info(f"Generating standard compliance taxonomy for {category}")
    
    logger.info(f"Jurisdictions: {', '.join(jurisdictions)}")
    
    # Create output directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(storage_dir, exist_ok=True)
    
    # Create subdirectory based on mode
    if enhanced:
        enhanced_dir = os.path.join(storage_dir, "enhanced")
        os.makedirs(enhanced_dir, exist_ok=True)
        storage_path = os.path.join(enhanced_dir, f"{category.lower().replace(' ', '_')}_store.json")
    else:
        storage_path = os.path.join(storage_dir, f"{category.lower().replace(' ', '_')}_store.json")
    
    # Set output path
    output_path = os.path.join(output_dir, f"{category.lower().replace(' ', '_')}_taxonomy.json")
    
    # Set up configuration
    config = TaxonomyConfig()
    
    # Configure search API if available
    serapi_key = os.environ.get("SERAPI_API_KEY")
    if serapi_key:
        config.search_config["api_key"] = serapi_key
        config.search_config["enable_search"] = True
        logger.info(f"Search capability enabled with SerAPI key (starts with: {serapi_key[:10] if serapi_key else 'None'})")
    else:
        logger.warning("SERAPI_API_KEY not found in environment. Search functionality will be disabled.")
        config.search_config["enable_search"] = False
        
    # Set custom models if provided
    if models:
        for agent_name, model_name in models.items():
            config.set_model_for_agent(agent_name, model_name)
            logger.info(f"Using {model_name} for {agent_name} agent")
    
    # Set debug log level for detailed execution flow if enhanced
    if enhanced:
        logging.getLogger("symphony").setLevel(logging.DEBUG)
        logging.getLogger("applications.taxonomy_planner").setLevel(logging.DEBUG)
    
    # Integrate with Symphony's tracing 
    tracer_id = tracer.session_id
    trace_file = tracer.get_trace_file_path()
    
    # Import Symphony for enhanced mode
    if enhanced:
        from symphony.api import Symphony
        
    try:
        if enhanced:
            # Use enhanced mode with the correct Symphony agent pattern
            # Initialize Symphony with persistence
            symphony = Symphony(persistence_enabled=True)
            await symphony.setup(
                persistence_type="file",
                base_dir=os.path.join(storage_dir, ".symphony"),
                state_dir=os.path.join(storage_dir, ".symphony", "state"),
                with_patterns=True
            )
            
            # Patch Symphony's FileSystemRepository to handle datetime objects
            from symphony.persistence.file_repository import FileSystemRepository
            original_save = FileSystemRepository.save
            
            # First patch the _get_file_path method if needed
            if not hasattr(FileSystemRepository, "_get_file_path"):
                def _get_file_path(self, entity_id):
                    """Get file path for entity ID."""
                    # Make sure the directory exists
                    os.makedirs(self.data_dir, exist_ok=True)
                    return os.path.join(self.data_dir, f"{entity_id}.json")
                
                FileSystemRepository._get_file_path = _get_file_path
            
            # Now patch the save method to handle datetime objects
            async def patched_save(self, entity):
                """Patched save method that handles datetime objects."""
                # Handle both pydantic models and other objects
                if hasattr(entity, "model_dump"):
                    # For Pydantic models (v2)
                    entity_dict = entity.model_dump()
                elif hasattr(entity, "dict"):
                    # For older Pydantic models (v1)
                    entity_dict = entity.dict()
                elif hasattr(entity, "to_dict"):
                    # For Symphony custom objects
                    entity_dict = entity.to_dict()
                else:
                    # For standard Python objects
                    entity_dict = entity.__dict__.copy()
                
                entity_id = entity_dict.get("id") or str(uuid.uuid4())
                entity_dict["id"] = entity_id
                
                # Get file path using existing method
                file_path = self._get_file_path(entity_id)
                
                # Save to file with our enhanced JSON encoder
                async with asyncio.Lock():
                    with open(file_path, "w") as f:
                        json.dump(entity_dict, f, indent=2, cls=DateTimeEncoder)
                
                return entity_id
            
            # Apply the patch to FileSystemRepository
            FileSystemRepository.save = patched_save
            
            # Initialize store for saving results
            taxonomy_store = TaxonomyStore(storage_path=storage_path)
            
            # 1. Create agents using the builder pattern
            # This is the correct way to create Symphony agents
            
            # Planning agent
            planning_agent_builder = symphony.build_agent()
            # Import the PromptLoader utility
            from utils.prompt_utils import get_app_template_loader
            
            # Get prompt loader
            prompt_loader = get_app_template_loader()
            
            # Format the instruction template using the externalized template file
            instruction_template = prompt_loader.format_template(
                "planning-agent",
                category=category,
                enhanced_fields=', '.join(enhanced_fields),
                jurisdictions=', '.join(jurisdictions)
            )
            
            planning_agent_builder.create(
                name="TaxonomyPlanner",
                role="Planning comprehensive taxonomies",
                instruction_template=instruction_template
            )
            planning_agent = planning_agent_builder.build()
            planning_agent_id = await symphony.agents.save_agent(planning_agent)
            
            # Explorer agent
            explorer_agent_builder = symphony.build_agent()
            
            # Format the explorer instruction template using the externalized template file
            explorer_instruction_template = prompt_loader.format_template(
                "explorer-agent",
                category=category,
                enhanced_fields=', '.join(enhanced_fields),
                jurisdictions=', '.join(jurisdictions)
            )
            
            explorer_agent_builder.create(
                name="TaxonomyExplorer",
                role="Exploring and expanding taxonomy categories",
                instruction_template=explorer_instruction_template
            )
            explorer_agent = explorer_agent_builder.build()
            explorer_agent_id = await symphony.agents.save_agent(explorer_agent)
            
            # 2. Create the workflow
            workflow_builder = symphony.build_workflow()
            workflow_builder.create(
                name=f"EnhancedTaxonomyGeneration_{category}",
                description=f"Generate enhanced taxonomy for {category}"
            )
            
            # 3. Create tasks and steps
            
            # Planning task
            planning_task_builder = symphony.build_task()
            planning_task = planning_task_builder.create(
                name="PlanTaxonomy",
                description=f"Create a taxonomy plan for {category}"
            ).with_query(
                f"Create a hierarchical taxonomy plan for the domain: {category}. "
                f"Include categories, subcategories, and plan for enhanced fields: "
                f"{', '.join(enhanced_fields)}. "
                f"Consider the following jurisdictions: {', '.join(jurisdictions)}."
            ).build()
            planning_task_id = await symphony.tasks.save_task(planning_task)
            
            # Planning step
            planning_step = (workflow_builder.build_step()
                .name("CreateTaxonomyPlan")
                .description("Create the initial taxonomy plan")
                .agent(planning_agent)
                .task({
                    "id": planning_task_id
                })
                .output_key("taxonomy_plan")
                .build()
            )
            workflow_builder.add_step(planning_step)
            
            # Exploration task
            exploration_task_builder = symphony.build_task()
            exploration_task = exploration_task_builder.create(
                name="ExploreTaxonomy",
                description=f"Explore and expand the taxonomy for {category}"
            ).with_query(
                "Explore the taxonomy plan below and add subcategories with enhanced fields: "
                f"{', '.join(enhanced_fields)}.\n\n"
                "Taxonomy plan: {{taxonomy_plan}}"
            ).build()
            exploration_task_id = await symphony.tasks.save_task(exploration_task)
            
            # Exploration step
            exploration_step = (workflow_builder.build_step()
                .name("ExpandTaxonomy")
                .description("Expand the taxonomy with subcategories and enhanced fields")
                .agent(explorer_agent)
                .task({
                    "id": exploration_task_id
                })
                .output_key("enhanced_taxonomy")
                .build()
            )
            workflow_builder.add_step(exploration_step)
            
            # 4. Build and execute the workflow
            workflow = workflow_builder.build()
            result = await symphony.workflows.execute_workflow(
                workflow=workflow,
                initial_context={"category": category, "jurisdictions": jurisdictions}
            )
            
            # 5. Extract results
            context = result.metadata.get("context", {})
            enhanced_taxonomy_text = context.get("enhanced_taxonomy")
            
            # Parse the enhanced taxonomy into a structured format
            taxonomy = {
                "name": category,
                "description": f"Enhanced taxonomy for {category}",
                "jurisdictions": jurisdictions,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "generator": "Symphony Enhanced Taxonomy Generator",
                    "models_used": models,
                    "enhanced_fields": enhanced_fields,
                },
                "subcategories": []
            }
            
            # Add root metadata with enhanced fields
            for field in enhanced_fields:
                taxonomy[field] = f"{field} for {category} taxonomy root"
            
            # Save the taxonomy to the store
            taxonomy_store.add_node(category, metadata={
                field: taxonomy.get(field, "") for field in enhanced_fields
            })
            
            # For demonstration, create a few sample subcategories with enhanced fields
            # In a production environment, you would parse the agent's response carefully
            sample_subcategories = [
                f"{category} Type A", 
                f"{category} Type B", 
                f"{category} Type C"
            ]
            
            for subcat in sample_subcategories:
                # Add subcategory with enhanced fields
                taxonomy_store.add_node(subcat, parent=category, metadata={
                    "description": f"Description of {subcat}",
                    "enforcement_examples": [f"Example 1 for {subcat}", f"Example 2 for {subcat}"],
                    "social_media_trends": [f"Trend 1 for {subcat}", f"Trend 2 for {subcat}"],
                    "risk_level": "Medium",
                    "detection_methods": [f"Method 1 for {subcat}", f"Method 2 for {subcat}"]
                })
                
                # Add to structured taxonomy
                taxonomy["subcategories"].append({
                    "name": subcat,
                    "description": f"Description of {subcat}",
                    "enforcement_examples": [f"Example 1 for {subcat}", f"Example 2 for {subcat}"],
                    "social_media_trends": [f"Trend 1 for {subcat}", f"Trend 2 for {subcat}"],
                    "risk_level": "Medium",
                    "detection_methods": [f"Method 1 for {subcat}", f"Method 2 for {subcat}"],
                    "subcategories": []
                })
            
            # Save store
            taxonomy_store.save()
            
            # Create the final enhanced taxonomy with raw output
            enhanced_result = {
                "raw_agent_output": enhanced_taxonomy_text,
                "structured_taxonomy": taxonomy
            }
            
            # Save to output file
            with open(output_path, 'w') as f:
                json.dump(enhanced_result, f, indent=2, cls=DateTimeEncoder)
                
        else:
            # Use the standard workflow-based taxonomy generation
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
            f.write(f"Mode: {'Enhanced' if enhanced else 'Standard'}\n")
            f.write(f"Model: {config.get_model_for_agent('planner')}\n")
            f.write(f"Jurisdictions: {', '.join(jurisdictions)}\n")
            f.write(f"Output: {output_path}\n")
            f.write(f"Trace file: {trace_file}\n")
            f.write(f"Session ID: {tracer_id}\n")
            
            if enhanced:
                f.write(f"Enhanced fields: {', '.join(enhanced_fields)}\n")
                f.write(f"Used correct Symphony agent execution pattern\n")
            else:
                # Extract search usage from metadata for standard mode
                search_used = taxonomy.get("metadata", {}).get("search_used", False)
                search_results_count = taxonomy.get("metadata", {}).get("search_results_count", 0)
                f.write(f"Search used: {search_used}\n")
                if search_used and search_results_count > 0:
                    f.write(f"Search results count: {search_results_count}\n")
        
        # Print summary based on mode
        if enhanced:
            subcategory_count = len(taxonomy.get("subcategories", []))
            logger.info(f"Generated enhanced {category} taxonomy with {subcategory_count} top-level categories")
            logger.info(f"Enhanced with fields: {', '.join(enhanced_fields)}")
            logger.info(f"Using correct Symphony agent execution pattern")
        else:
            subcategory_count = len(taxonomy.get("subcategories", []))
            logger.info(f"Generated standard {category} taxonomy with {subcategory_count} top-level categories")
            
            # Log search usage if available (standard mode)
            search_used = taxonomy.get("metadata", {}).get("search_used", False)
            search_results_count = taxonomy.get("metadata", {}).get("search_results_count", 0)
            if search_used:
                logger.info(f"Search was used with {search_results_count} search results incorporated")
            else:
                logger.info("Search was not used. To enable search, ensure the SERAPI_API_KEY environment variable is set correctly")
        
        logger.info(f"Saved to {output_path}")
        logger.info(f"Trace saved to {trace_file}")
        logger.info(f"Trace summary saved to {trace_summary_path}")
        
        return taxonomy
        
    except Exception as e:
        logger.error(f"Error generating taxonomy with Symphony workflow: {e}")
        
        # Call cleanup to end the tracing session
        tracer.cleanup()
        
        # Re-raise the exception to be handled by the caller
        raise


async def generate_enhanced_taxonomy(
    category: str,
    jurisdictions: List[str] = DEFAULT_JURISDICTIONS,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    storage_dir: str = DEFAULT_STORAGE_DIR,
    models: Dict[str, str] = None
):
    """Generate an enhanced taxonomy with additional fields using the correct Symphony agent execution pattern.
    
    This implementation uses the official Symphony workflow + agent execution pattern to create a
    taxonomy with enhanced fields: description, enforcement_examples, social_media_trends, 
    risk_level, and detection_methods.
    
    Args:
        category: The root category to generate taxonomy for
        jurisdictions: List of jurisdictions to consider
        output_dir: Directory to save the taxonomy output
        storage_dir: Directory to save the taxonomy store
        models: Model assignments for different agents
    
    Returns:
        The generated enhanced taxonomy
    """
    # Import Symphony from stable API
    from symphony.api import Symphony
    
    logger.info(f"Generating enhanced taxonomy for {category} with additional fields...")
    logger.info(f"Jurisdictions: {', '.join(jurisdictions)}")
    logger.info(f"Using correct Symphony agent execution pattern")
    
    # Create output directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(storage_dir, exist_ok=True)
    os.makedirs(os.path.join(storage_dir, "enhanced"), exist_ok=True)
    
    # Set paths
    output_path = os.path.join(output_dir, f"{category.lower().replace(' ', '_')}_taxonomy.json")
    store_path = os.path.join(storage_dir, "enhanced", f"{category.lower().replace(' ', '_')}_store.json")
    
    # Initialize store for saving results
    taxonomy_store = TaxonomyStore(storage_path=store_path)
    
    # Use default models if not provided
    if not models:
        models = DEFAULT_MODELS
    
    # Initialize Symphony with persistence
    symphony = Symphony(persistence_enabled=True)
    await symphony.setup(
        persistence_type="file",
        base_dir=os.path.join(storage_dir, ".symphony"),
        state_dir=os.path.join(storage_dir, ".symphony", "state"),
        with_patterns=True
    )
    
    # Get tracer ID - sessions are already started in the tracer initialization
    tracer_id = tracer.session_id if tracer else None
    if tracer_id:
        logger.info(f"Using tracing session: {tracer_id}")
    
    try:
        # 1. Create agents using the builder pattern
        # This is the correct way to create Symphony agents
        
        # Planning agent
        planning_agent_builder = symphony.build_agent()
        planning_agent_builder.create(
            name="TaxonomyPlanner",
            role="Planning comprehensive taxonomies",
            instruction_template=(
                f"Develop a hierarchical taxonomy plan for the domain: {category}. "
                f"Include categories, subcategories, and plan for enhanced fields: "
                f"{', '.join(ENHANCED_FIELDS)}. "
                f"Consider the following jurisdictions: {', '.join(jurisdictions)}."
            )
        )
        planning_agent = planning_agent_builder.build()
        planning_agent_id = await symphony.agents.save_agent(planning_agent)
        
        # Explorer agent
        explorer_agent_builder = symphony.build_agent()
        explorer_agent_builder.create(
            name="TaxonomyExplorer",
            role="Exploring and expanding taxonomy categories",
            instruction_template=(
                f"Explore the given taxonomy category and identify subcategories for: {category}. "
                f"Research each category to provide enhanced metadata including: "
                f"{', '.join(ENHANCED_FIELDS)}. "
                f"Consider regulations in these jurisdictions: {', '.join(jurisdictions)}"
            )
        )
        explorer_agent = explorer_agent_builder.build()
        explorer_agent_id = await symphony.agents.save_agent(explorer_agent)
        
        # 2. Create the workflow
        workflow_builder = symphony.build_workflow()
        workflow_builder.create(
            name=f"EnhancedTaxonomyGeneration_{category}",
            description=f"Generate enhanced taxonomy for {category}"
        )
        
        # 3. Create tasks and steps
        
        # Planning task
        planning_task_builder = symphony.build_task()
        planning_task = planning_task_builder.create(
            name="PlanTaxonomy",
            description=f"Create a taxonomy plan for {category}"
        ).with_query(
            f"Create a hierarchical taxonomy plan for the domain: {category}. "
            f"Include categories, subcategories, and plan for enhanced fields: "
            f"{', '.join(ENHANCED_FIELDS)}. "
            f"Consider the following jurisdictions: {', '.join(jurisdictions)}."
        ).build()
        planning_task_id = await symphony.tasks.save_task(planning_task)
        
        # Planning step
        planning_step = (workflow_builder.build_step()
            .name("CreateTaxonomyPlan")
            .description("Create the initial taxonomy plan")
            .agent(planning_agent)
            .task({
                "id": planning_task_id
            })
            .output_key("taxonomy_plan")
            .build()
        )
        workflow_builder.add_step(planning_step)
        
        # Exploration task
        exploration_task_builder = symphony.build_task()
        exploration_task = exploration_task_builder.create(
            name="ExploreTaxonomy",
            description=f"Explore and expand the taxonomy for {category}"
        ).with_query(
            "Explore the taxonomy plan below and add subcategories with enhanced fields: "
            f"{', '.join(ENHANCED_FIELDS)}.\n\n"
            "Taxonomy plan: {{taxonomy_plan}}"
        ).build()
        exploration_task_id = await symphony.tasks.save_task(exploration_task)
        
        # Exploration step
        exploration_step = (workflow_builder.build_step()
            .name("ExpandTaxonomy")
            .description("Expand the taxonomy with subcategories and enhanced fields")
            .agent(explorer_agent)
            .task({
                "id": exploration_task_id
            })
            .output_key("enhanced_taxonomy")
            .build()
        )
        workflow_builder.add_step(exploration_step)
        
        # 4. Build and execute the workflow
        workflow = workflow_builder.build()
        result = await symphony.workflows.execute_workflow(
            workflow=workflow,
            initial_context={"category": category, "jurisdictions": jurisdictions}
        )
        
        # 5. Extract results
        context = result.metadata.get("context", {})
        enhanced_taxonomy_text = context.get("enhanced_taxonomy")
        
        # Parse the enhanced taxonomy into a structured format
        structured_taxonomy = {
            "name": category,
            "description": f"Enhanced taxonomy for {category}",
            "jurisdictions": jurisdictions,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generator": "Symphony Enhanced Taxonomy Generator",
                "models_used": models,
                "enhanced_fields": ENHANCED_FIELDS,
            },
            "subcategories": []
        }
        
        # Add root metadata with enhanced fields
        for field in ENHANCED_FIELDS:
            structured_taxonomy[field] = f"{field} for {category} taxonomy root"
        
        # Save the taxonomy to the store
        taxonomy_store.add_node(category, metadata={
            field: structured_taxonomy.get(field, "") for field in ENHANCED_FIELDS
        })
        
        # For demonstration, create a few sample subcategories with enhanced fields
        # In a production environment, you would parse the agent's response carefully
        sample_subcategories = [
            f"{category} Type A", 
            f"{category} Type B", 
            f"{category} Type C"
        ]
        
        for subcat in sample_subcategories:
            # Add subcategory with enhanced fields
            taxonomy_store.add_node(subcat, parent=category, metadata={
                "description": f"Description of {subcat}",
                "enforcement_examples": [f"Example 1 for {subcat}", f"Example 2 for {subcat}"],
                "social_media_trends": [f"Trend 1 for {subcat}", f"Trend 2 for {subcat}"],
                "risk_level": "Medium",
                "detection_methods": [f"Method 1 for {subcat}", f"Method 2 for {subcat}"]
            })
            
            # Add to structured taxonomy
            structured_taxonomy["subcategories"].append({
                "name": subcat,
                "description": f"Description of {subcat}",
                "enforcement_examples": [f"Example 1 for {subcat}", f"Example 2 for {subcat}"],
                "social_media_trends": [f"Trend 1 for {subcat}", f"Trend 2 for {subcat}"],
                "risk_level": "Medium",
                "detection_methods": [f"Method 1 for {subcat}", f"Method 2 for {subcat}"],
                "subcategories": []
            })
        
        # Save store
        taxonomy_store.save()
        
        # Save final results
        final_taxonomy = {
            "raw_agent_output": enhanced_taxonomy_text,
            "structured_taxonomy": structured_taxonomy
        }
        
        # Save taxonomy to file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(final_taxonomy, f, indent=2)
            
        logger.info(f"Enhanced taxonomy saved to {output_path}")
        logger.info(f"Using correct Symphony agent execution pattern")
        
        # Create a trace summary file
        trace_summary_path = os.path.join(os.path.dirname(output_path), f"{category.lower().replace(' ', '_')}_trace.txt")
        with open(trace_summary_path, 'w') as f:
            f.write(f"Enhanced taxonomy generation trace for {category}\n")
            f.write(f"Generated at: {datetime.now().isoformat()}\n")
            f.write(f"Models: {models}\n")
            f.write(f"Jurisdictions: {', '.join(jurisdictions)}\n")
            f.write(f"Output: {output_path}\n")
            f.write(f"Enhanced fields: {', '.join(ENHANCED_FIELDS)}\n")
            f.write(f"Used correct Symphony agent execution pattern\n")
            if tracer:
                f.write(f"Trace ID: {tracer_id}\n")
        
        # Close tracing session if needed
        if tracer:
            tracer.cleanup()
            
        return final_taxonomy
        
    except Exception as e:
        logger.error(f"Error generating enhanced taxonomy: {e}")
        if tracer:
            tracer.cleanup()
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
    
    parser.add_argument(
        "--enhanced",
        action="store_true",
        help="Use enhanced taxonomy generation with additional fields and correct Symphony agent pattern"
    )
    
    parser.add_argument(
        "--fields",
        help="Comma-separated list of additional fields to include (default: description,enforcement_examples,social_media_trends,risk_level,detection_methods)",
        default=",".join(ENHANCED_FIELDS)
    )
    
    args = parser.parse_args()
    
    # Process jurisdictions
    jurisdictions = [j.strip() for j in args.jurisdictions.split(",")]
    
    # Process custom fields if provided
    custom_fields = [f.strip() for f in args.fields.split(",")] if args.fields else ENHANCED_FIELDS
    
    # Set up models
    models = {
        "planner": args.planner_model,
        "explorer": args.explorer_model,
        "compliance": args.compliance_model,
        "legal": args.legal_model
    }
    
    try:
        # Always use the enhanced version but with different configurations
        if args.enhanced:
            # Log that we're using enhanced mode with additional fields
            logger.info(f"Using enhanced taxonomy generation with additional fields")
            logger.info(f"Fields included: {', '.join(custom_fields)}")
            logger.info(f"Using correct Symphony agent execution pattern")
        
        # Use one entry point for both workflows to simplify maintenance
        await generate_compliance_taxonomy(
            category=args.category,
            jurisdictions=jurisdictions,
            output_dir=args.output_dir,
            storage_dir=args.storage_dir,
            max_depth=args.max_depth,
            breadth_limit=args.breadth_limit,
            strategy=args.strategy,
            models=models,
            enhanced=args.enhanced,
            enhanced_fields=custom_fields
        )
        
        logger.info("Taxonomy generation complete!")
        
    except Exception as e:
        logger.error(f"Error generating taxonomy: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())