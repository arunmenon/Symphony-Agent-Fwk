"""Main implementation of Taxonomy Planner."""

import asyncio
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

from symphony import Symphony
from .config import TaxonomyConfig
from .agents import create_agents
from .patterns import create_patterns, apply_pattern
from .tools import register_tools

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
        self.memory = None
        self.initialized = False
        self.workflow_definition = None
    
    async def setup(self):
        """Initialize Symphony and set up components."""
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
        
        # Create memory
        self.memory = self.symphony.create_memory()
        
        # Create workflow definition for taxonomy generation
        self._create_workflow_definition()
        
        self.initialized = True
    
    def _create_workflow_definition(self):
        """Create workflow definition for taxonomy generation process."""
        workflow_builder = self.symphony.build_workflow()
        
        # Start building the workflow
        workflow = (workflow_builder
            .name("Taxonomy Generation Workflow")
            .description("Workflow for generating hierarchical taxonomies with compliance and legal mappings")
            # Planning step
            .add_step(
                self.symphony.build_step()
                .name("Planning")
                .description("Plan the taxonomy structure")
                .agent(self.agents["planner"])
                .task("{{root_category}}")
                .pattern(self.patterns["chain_of_thought"])
                .output_key("plan")
                .build()
            )
            # Exploration step
            .add_step(
                self.symphony.build_step()
                .name("Exploration")
                .description("Explore the taxonomy tree")
                .agent(self.agents["explorer"])
                .task("Explore the taxonomy tree for {{root_category}}")
                .pattern(self.patterns["search_enhanced_exploration"])
                .context_data({
                    "category": "{{root_category}}",
                    "parent": None,
                    "memory": self.memory,
                    "agent": self.agents["explorer"],
                    "tools": ["search_knowledge_base", "search_subcategories", "search_category_info"],
                    "max_depth": "{{max_depth}}"
                })
                .output_key("exploration_result")
                .build()
            )
            # Compliance mapping step
            .add_step(
                self.symphony.build_step()
                .name("ComplianceMapping")
                .description("Map compliance requirements to taxonomy")
                .agent(self.agents["compliance"])
                .task("Map compliance requirements for all categories")
                .pattern(self.patterns["verify_execute"])
                .context_data({
                    "categories": "{{memory.get_all_nodes()}}",
                    "jurisdictions": "{{jurisdictions}}",
                    "tools": ["get_compliance_requirements", "search_compliance_requirements"]
                })
                .output_key("compliance_results")
                .build()
            )
            # Legal mapping step
            .add_step(
                self.symphony.build_step()
                .name("LegalMapping")
                .description("Map legal requirements to taxonomy")
                .agent(self.agents["legal"])
                .task("Map legal requirements for all categories")
                .pattern(self.patterns["verify_execute"])
                .context_data({
                    "categories": "{{memory.get_all_nodes()}}",
                    "jurisdictions": "{{jurisdictions}}",
                    "tools": ["get_applicable_laws", "search_legal_requirements"]
                })
                .output_key("legal_results")
                .build()
            )
            # Tree building step (using processing step instead of agent step)
            .add_step(
                self.symphony.build_step()
                .name("TreeBuilding")
                .description("Build final taxonomy tree")
                .processing_function(self._build_taxonomy_tree)
                .context_data({
                    "root_category": "{{root_category}}",
                    "compliance_results": "{{compliance_results}}",
                    "legal_results": "{{legal_results}}",
                    "memory": "{{memory}}"
                })
                .output_key("taxonomy")
                .build()
            )
            # Output step (using processing step)
            .add_step(
                self.symphony.build_step()
                .name("SaveOutput")
                .description("Save taxonomy to output file if path provided")
                .processing_function(self._save_taxonomy)
                .context_data({
                    "taxonomy": "{{taxonomy}}",
                    "output_path": "{{output_path}}"
                })
                .build()
            )
            .build()
        )
        
        self.workflow_definition = workflow
    
    async def generate_taxonomy(
        self, 
        root_category: str, 
        jurisdictions: Optional[List[str]] = None,
        max_depth: Optional[int] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a taxonomy with compliance and legal mappings.
        
        Args:
            root_category: Root category of the taxonomy
            jurisdictions: List of jurisdictions to map
            max_depth: Maximum depth of taxonomy
            output_path: Path to save the output JSON
            
        Returns:
            Generated taxonomy
        """
        if not self.initialized:
            await self.setup()
        
        # Use default jurisdictions if not provided
        jurisdictions = jurisdictions or self.config.default_jurisdictions
        
        # Use configured max depth if not provided
        effective_max_depth = max_depth if max_depth is not None else self.config.max_depth
        
        # Add root node to memory
        self.memory.add_node(root_category)
        
        # Prepare initial context for workflow
        initial_context = {
            "root_category": root_category,
            "jurisdictions": jurisdictions,
            "max_depth": effective_max_depth,
            "output_path": output_path,
            "memory": self.memory
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
        compliance_data = context.get("compliance_results", {})
        legal_data = context.get("legal_results", {})
        memory = context.get("memory")
        
        # Initialize taxonomy with root node
        taxonomy = {
            "category": root_category,
            "subcategories": [],
            "compliance": {},
            "legal": {},
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "max_depth": context.get("max_depth"),
                "jurisdictions": context.get("jurisdictions", [])
            }
        }
        
        # Build tree recursively
        await self._build_node(
            taxonomy, 
            root_category, 
            None, 
            compliance_data, 
            legal_data, 
            memory
        )
        
        return taxonomy
    
    async def _build_node(
        self, 
        node: Dict[str, Any],
        category: str, 
        parent: Optional[str], 
        compliance_data: Dict[str, Dict[str, Any]], 
        legal_data: Dict[str, Dict[str, Any]],
        memory
    ) -> None:
        """Build a single node and its children recursively.
        
        Args:
            node: Current node to populate
            category: Current category
            parent: Parent category
            compliance_data: Compliance data by category and jurisdiction
            legal_data: Legal data by category and jurisdiction
            memory: Symphony memory instance
        """
        # Get subcategories for this node
        subcategories = memory.get_edges(category) or []
        
        # Get compliance and legal data for this category
        if category in compliance_data:
            node["compliance"] = compliance_data[category]
        
        if category in legal_data:
            node["legal"] = legal_data[category]
        
        # Process subcategories recursively
        for subcategory in subcategories:
            child_node = {
                "category": subcategory,
                "subcategories": [],
                "compliance": {},
                "legal": {}
            }
            
            if parent:
                child_node["parent"] = parent
            
            # Process child recursively
            await self._build_node(
                child_node,
                subcategory, 
                category, 
                compliance_data, 
                legal_data,
                memory
            )
            
            # Add to parent's subcategories
            node["subcategories"].append(child_node)
    
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
    output_path: Optional[str] = None,
    config: Optional[TaxonomyConfig] = None,
    **kwargs
) -> Dict[str, Any]:
    """Generate a taxonomy with compliance and legal mappings.
    
    Args:
        root_category: Root category of the taxonomy
        jurisdictions: List of jurisdictions to map
        max_depth: Maximum depth of taxonomy
        output_path: Path to save the output JSON
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
    await planner.setup()
    
    # Generate taxonomy
    return await planner.generate_taxonomy(
        root_category=root_category,
        jurisdictions=jurisdictions,
        max_depth=max_depth,
        output_path=output_path
    )