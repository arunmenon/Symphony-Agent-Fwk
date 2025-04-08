"""Main implementation of Taxonomy Planner."""

import asyncio
import os
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

from symphony import Symphony
from .config import TaxonomyConfig
from .agents import create_agents
from .patterns import create_patterns, apply_pattern
from .tools import register_tools
from .persistence import TaxonomyStore

logger = logging.getLogger(__name__)

class TaxonomyPlanner:
    """Main class for taxonomy generation using Symphony workflow orchestration."""
    
    def __init__(self, config: Optional[TaxonomyConfig] = None):
        """Initialize the taxonomy planner.
        
        Args:
            config: Taxonomy configuration
        """
        self.config = config or TaxonomyConfig()
        self.symphony = Symphony(persistence_enabled=True)
        self.agents = {}
        self.patterns = {}
        self.store = None
        self.initialized = False
        self.workflow_definition = None
    
    async def setup(self, storage_path: Optional[str] = None):
        """Initialize Symphony and set up components.
        
        Args:
            storage_path: Path to save taxonomy data (optional)
        """
        if self.initialized:
            return
        
        # Initialize Symphony with persistence enabled
        await self.symphony.setup(state_dir=".symphony/taxonomy_planner_state")
        
        # Register tools
        register_tools(self.symphony, self.config)
        
        # Create agents
        self.agents = create_agents(self.symphony, self.config)
        
        # Create patterns
        self.patterns = create_patterns()
        
        # Create taxonomy store with persistence
        if not storage_path:
            # Use default path in Symphony state directory
            storage_path = ".symphony/taxonomy_planner_state/taxonomy_store.json"
            
        self.store = TaxonomyStore(storage_path=storage_path)
        
        # Create workflow definition for taxonomy generation
        self._create_workflow_definition()
        
        self.initialized = True
    
    def _create_workflow_definition(self):
        """Create workflow definition for taxonomy generation process."""
        workflow_builder = self.symphony.build_workflow()
        
        # Start building the workflow
        workflow_builder.create(
            name="Taxonomy Generation Workflow",
            description="Workflow for generating hierarchical taxonomies with compliance and legal mappings"
        )
        
        # Planning step
        planning_step = (workflow_builder.build_step()
            .name("Planning")
            .description("Plan the taxonomy structure")
            .agent(self.agents["planner"])
            .task("Create a comprehensive taxonomy for {{root_category}}. Include main subcategories, important distinctions, and organization principles. Focus on creating a well-structured hierarchical taxonomy that could be further expanded.")
            .pattern(self.patterns["chain_of_thought"])
            .output_key("plan")
            .build()
        )
        workflow_builder.add_step(planning_step)
        
        # NEW: Plan processing step
        plan_processing_step = (workflow_builder.build_step()
            .name("PlanProcessing")
            .description("Process planner output and initialize taxonomy")
            .processing_function(self._process_plan)
            .context_data({
                "plan": "{{plan}}",
                "root_category": "{{root_category}}",
                "store": self.store
            })
            .output_key("initial_categories")
            .build()
        )
        workflow_builder.add_step(plan_processing_step)
        
        # Exploration step (updated to use store)
        exploration_step = (workflow_builder.build_step()
            .name("Exploration")
            .description("Explore the taxonomy tree")
            .agent(self.agents["explorer"])
            .task("Explore the taxonomy tree for {{root_category}} with initial categories: {{initial_categories}}")
            .pattern(self.patterns["search_enhanced_exploration"])
            .context_data({
                "category": "{{root_category}}",
                "parent": None,
                "store": self.store,
                "agent": self.agents["explorer"],
                "tools": ["search_knowledge_base", "search_subcategories", "search_category_info"],
                "max_depth": "{{max_depth}}",
                "breadth_limit": "{{breadth_limit}}",
                "strategy": "{{strategy}}",
                "initial_categories": "{{initial_categories}}"
            })
            .output_key("exploration_result")
            .build()
        )
        workflow_builder.add_step(exploration_step)
        
        # Compliance mapping step (updated to use store)
        compliance_step = (workflow_builder.build_step()
            .name("ComplianceMapping")
            .description("Map compliance requirements to taxonomy")
            .agent(self.agents["compliance"])
            .task("Map compliance requirements for all categories")
            .pattern(self.patterns["verify_execute"])
            .context_data({
                "categories": self.store.get_all_nodes,
                "jurisdictions": "{{jurisdictions}}",
                "store": self.store,
                "tools": ["get_compliance_requirements", "search_compliance_requirements"]
            })
            .output_key("compliance_results")
            .build()
        )
        workflow_builder.add_step(compliance_step)
        
        # Legal mapping step (updated to use store)
        legal_step = (workflow_builder.build_step()
            .name("LegalMapping")
            .description("Map legal requirements to taxonomy")
            .agent(self.agents["legal"])
            .task("Map legal requirements for all categories")
            .pattern(self.patterns["verify_execute"])
            .context_data({
                "categories": self.store.get_all_nodes,
                "jurisdictions": "{{jurisdictions}}",
                "store": self.store,
                "tools": ["get_applicable_laws", "search_legal_requirements"]
            })
            .output_key("legal_results")
            .build()
        )
        workflow_builder.add_step(legal_step)
        
        # Tree building step (using processing step instead of agent step)
        tree_step = (workflow_builder.build_step()
            .name("TreeBuilding")
            .description("Build final taxonomy tree")
            .processing_function(self._build_taxonomy_tree)
            .context_data({
                "root_category": "{{root_category}}",
                "compliance_results": "{{compliance_results}}",
                "legal_results": "{{legal_results}}",
                "store": self.store
            })
            .output_key("taxonomy")
            .build()
        )
        workflow_builder.add_step(tree_step)
        
        # Output step (using processing step)
        output_step = (workflow_builder.build_step()
            .name("SaveOutput")
            .description("Save taxonomy to output file if path provided")
            .processing_function(self._save_taxonomy)
            .context_data({
                "taxonomy": "{{taxonomy}}",
                "output_path": "{{output_path}}"
            })
            .build()
        )
        workflow_builder.add_step(output_step)
        
        # Build the final workflow definition
        self.workflow_definition = workflow_builder.build()
    
    async def _process_plan(self, context: Dict[str, Any]) -> List[str]:
        """Process planner output to extract initial categories.
        
        This step analyzes the planner's output and extracts the key categories
        to initialize the taxonomy structure.
        
        Args:
            context: Workflow step context with plan and root category
            
        Returns:
            List of initial categories
        """
        plan = context.get("plan", "")
        root_category = context.get("root_category", "")
        store = context.get("store")
        
        # Add root category to store if not already present
        if not store.get_node(root_category):
            store.add_node(root_category)
        
        # Extract categories from planner output
        initial_categories = []
        
        # Look for list patterns in the plan
        list_patterns = [
            r'[\*\-•] ([^:\n]+)(?::|$)',  # Bullet points
            r'^\d+\.\s+([^:\n]+)(?::|$)',  # Numbered lists
            r'([A-Z][a-zA-Z\s]+)(?::|$)'   # Capitalized headers
        ]
        
        # Combine extracted categories from different patterns
        all_matches = []
        for pattern in list_patterns:
            matches = re.finditer(pattern, plan, re.MULTILINE)
            for match in matches:
                category = match.group(1).strip()
                if category and len(category) > 2:
                    # Filter out common non-category phrases
                    if not category.lower().startswith(('here', 'this', 'these', 'those', 'the', 'a', 'an')):
                        all_matches.append(category)
        
        # Remove duplicates while preserving order
        seen = set()
        initial_categories = [cat for cat in all_matches if cat not in seen and not seen.add(cat)]
        
        # Add each category to the store
        for category in initial_categories:
            store.add_node(category, parent=root_category)
            
        # Save store to disk
        store.save()
        
        return initial_categories
    
    async def generate_taxonomy(
        self, 
        root_category: str, 
        jurisdictions: Optional[List[str]] = None,
        max_depth: Optional[int] = None,
        breadth_limit: Optional[int] = None,
        strategy: str = "parallel",
        output_path: Optional[str] = None,
        storage_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a taxonomy with compliance and legal mappings.
        
        Args:
            root_category: Root category of the taxonomy
            jurisdictions: List of jurisdictions to map
            max_depth: Maximum depth of taxonomy
            breadth_limit: Maximum number of subcategories per node
            strategy: Exploration strategy ('parallel', 'breadth_first', 'depth_first')
            output_path: Path to save the output JSON
            storage_path: Path to save taxonomy store data
            
        Returns:
            Generated taxonomy
        """
        if not self.initialized:
            await self.setup(storage_path)
        
        # Use default jurisdictions if not provided
        jurisdictions = jurisdictions or self.config.default_jurisdictions
        
        # Use configured max depth and breadth if not provided
        effective_max_depth = max_depth if max_depth is not None else self.config.max_depth
        effective_breadth_limit = breadth_limit if breadth_limit is not None else self.config.pattern_configs.get("recursive_exploration", {}).get("breadth_limit", 10)
        
        # Clear existing store data
        self.store.clear()
        
        # Add root node to store
        self.store.add_node(root_category)
        
        # Prepare initial context for workflow
        initial_context = {
            "root_category": root_category,
            "jurisdictions": jurisdictions,
            "max_depth": effective_max_depth,
            "breadth_limit": effective_breadth_limit,
            "strategy": strategy,
            "output_path": output_path,
            "store": self.store
        }
        
        # Generate workflow name based on category
        workflow_name = f"taxonomy_{root_category.lower().replace(' ', '_')}"
        
        # Execute workflow with automatic checkpointing and resumption
        workflow_engine = self.symphony.workflows.get_engine()
        workflow_result = await workflow_engine.execute_workflow(
            workflow_def=self.workflow_definition,
            initial_context=initial_context,
            auto_checkpoint=True,
            resume_from_checkpoint=True
        )
        
        # Get final taxonomy from workflow result context
        context = workflow_result.metadata.get("context", {})
        taxonomy = context.get("taxonomy", {})
        
        return taxonomy
    
    async def _build_taxonomy_tree(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build complete taxonomy tree with compliance and legal data.
        
        Args:
            context: Workflow step context
            
        Returns:
            Complete taxonomy tree
        """
        root_category = context.get("root_category")
        store = context.get("store")
        
        # Get the fully built taxonomy tree from the store
        taxonomy = store.get_taxonomy_tree(root_category)
        
        # Add metadata
        if "metadata" not in taxonomy:
            taxonomy["metadata"] = {}
            
        taxonomy["metadata"].update({
            "generated_at": datetime.now().isoformat(),
            "max_depth": context.get("max_depth"),
            "jurisdictions": context.get("jurisdictions", [])
        })
        
        return taxonomy
    
    async def _save_taxonomy(self, context: Dict[str, Any]) -> None:
        """Save taxonomy to a file.
        
        Args:
            context: Workflow step context with taxonomy and output path
        """
        taxonomy = context.get("taxonomy", {})
        path = context.get("output_path")
        
        if not path:
            # No output path, nothing to do
            return
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        # Save taxonomy
        with open(path, 'w') as f:
            json.dump(taxonomy, f, indent=2)
        
        logger.info(f"Taxonomy saved to {path}")


async def generate_taxonomy(
    root_category: str,
    jurisdictions: Optional[List[str]] = None,
    max_depth: Optional[int] = None,
    breadth_limit: Optional[int] = None,
    strategy: str = "parallel",
    output_path: Optional[str] = None,
    storage_path: Optional[str] = None,
    config: Optional[TaxonomyConfig] = None,
    **kwargs
) -> Dict[str, Any]:
    """Generate a taxonomy with compliance and legal mappings.
    
    Args:
        root_category: Root category of the taxonomy
        jurisdictions: List of jurisdictions to map
        max_depth: Maximum depth of taxonomy
        breadth_limit: Maximum number of subcategories per node
        strategy: Exploration strategy ('parallel', 'breadth_first', 'depth_first') 
        output_path: Path to save the output JSON
        storage_path: Path to save taxonomy store data
        config: Custom configuration
        **kwargs: Additional configuration options
        
    Returns:
        Generated taxonomy
    """
    # Create config if not provided
    if config is None:
        config = TaxonomyConfig()
    
    # Handle model assignments if present in kwargs
    if "models" in kwargs:
        models = kwargs.pop("models")
        if isinstance(models, dict):
            for agent_name, model in models.items():
                config.set_model_for_agent(agent_name, model)
    
    # Create and set up planner
    planner = TaxonomyPlanner(config)
    await planner.setup(storage_path)
    
    # Generate taxonomy
    return await planner.generate_taxonomy(
        root_category=root_category,
        jurisdictions=jurisdictions,
        max_depth=max_depth,
        breadth_limit=breadth_limit,
        strategy=strategy,
        output_path=output_path,
        storage_path=storage_path
    )