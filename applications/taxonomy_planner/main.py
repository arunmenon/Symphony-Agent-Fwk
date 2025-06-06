"""Main implementation of Taxonomy Planner."""

import os
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

# Use stable API imports
from symphony.api import Symphony
# Use direct imports for running as script
from config import TaxonomyConfig
from agents import create_agents
from patterns import create_patterns
from tools import register_tools
from persistence import TaxonomyStore

def load_task_prompt(name):
    """Load a task prompt from a text file.
    
    Args:
        name: Name of the prompt file without extension
        
    Returns:
        String content of the prompt
    """
    # Load the template using PromptLoader
    from utils.prompt_utils import get_app_template_loader
    
    loader = get_app_template_loader()
    template_content = loader.load_template(name)
    
    if template_content:
        logger.debug(f"Loaded task prompt '{name}' ({len(template_content)} chars)")
        return template_content
    else:
        logger.warning(f"Task prompt '{name}' not found")
        # Create a default prompt for testing (keeping backward compatibility)
        if name == "planning":
            default = f"Plan a comprehensive taxonomy structure for {{{{root_category}}}}."
        elif name == "exploration":
            default = f"Explore subcategories for {{{{category}}}} with initial categories: {{{{initial_categories}}}}"
        elif name == "compliance":
            default = f"Map compliance requirements for all categories in {{{{root_category}}}} taxonomy."
        elif name == "legal":
            default = f"Map legal requirements for all categories in {{{{root_category}}}} taxonomy."
        else:
            default = f"Generate content for {name}"
        
        logger.warning(f"Using default prompt: {default}")
        return default

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
        try:
            logger.debug("Starting workflow definition creation")
            workflow_builder = self.symphony.build_workflow()
            
            # Start building the workflow
            workflow_builder.create(
                name="Taxonomy Generation Workflow",
                description="Workflow for generating hierarchical taxonomies with compliance and legal mappings"
            )
            logger.debug("Workflow builder created successfully")
        
            # Planning step with externalized prompt and search tools
            planning_step = (workflow_builder.build_step()
                .name("Planning")
                .description("Plan the taxonomy structure")
                .agent(self.agents["planner"])
                .task(load_task_prompt("planning"))
                .pattern(self.patterns["chain_of_thought"])
                .context_data({
                    "tools": ["search_subcategories", "search_category_info"]
                })
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
            
            # Exploration step with externalized prompt and search tools
            exploration_step = (workflow_builder.build_step()
                .name("Exploration")
                .description("Explore the taxonomy tree")
                .agent(self.agents["explorer"])
                .task(load_task_prompt("exploration"))
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
            
            # Compliance mapping step with externalized prompt
            compliance_step = (workflow_builder.build_step()
                .name("ComplianceMapping")
                .description("Map compliance requirements to taxonomy")
                .agent(self.agents["compliance"])
                .task(load_task_prompt("compliance"))
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
            
            # Legal mapping step with externalized prompt
            legal_step = (workflow_builder.build_step()
                .name("LegalMapping")
                .description("Map legal requirements to taxonomy")
                .agent(self.agents["legal"])
                .task(load_task_prompt("legal"))
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
            logger.debug("Building final workflow definition")
            self.workflow_definition = workflow_builder.build()
            logger.debug(f"Workflow definition created with {len(self.workflow_definition.steps)} steps")
        except Exception as e:
            logger.error(f"Error creating workflow definition: {e}")
            # Create a minimal workflow definition for error recovery
            logger.warning("Creating minimal workflow definition for recovery")
            workflow_builder = self.symphony.build_workflow()
            self.workflow_definition = workflow_builder.create(
                name="Minimal Taxonomy Workflow",
                description="Minimal workflow for error recovery"
            ).build()
    
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
        
        # Create a direct taxonomy tree without workflow for debugging
        logger.debug(f"Search config enabled: {self.config.search_config.get('enable_search', False)}")
        logger.debug(f"Search API key configured: {bool(self.config.search_config.get('api_key'))}")
        logger.debug(f"Workflow definition steps: {len(self.workflow_definition.steps)}")
        
        # Log all steps for debugging
        try:
            for i, step in enumerate(self.workflow_definition.steps):
                if hasattr(step, 'name') and hasattr(step, 'description'):
                    logger.debug(f"Step {i+1}: {step.name} - {step.description}")
                else:
                    logger.debug(f"Step {i+1}: {step}")
        except Exception as e:
            logger.error(f"Error listing workflow steps: {e}")
        
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
        
        try:
            # Execute workflow with automatic checkpointing and resumption using stable API
            workflow_result = await self.symphony.workflows.execute_workflow(
                workflow=self.workflow_definition,
                initial_context=initial_context,
                auto_checkpoint=True,
                resume_from_checkpoint=True
            )
            
            # Get final taxonomy from workflow result context
            context = workflow_result.metadata.get("context", {})
            taxonomy = context.get("taxonomy", {})
            
            # Additional logging for empty taxonomies
            if not taxonomy or not taxonomy.get("subcategories"):
                logger.warning(f"Empty taxonomy returned from workflow. Context keys: {list(context.keys())}")
                
                # Check if there were any errors in the workflow execution
                if "errors" in context:
                    logger.error(f"Workflow execution errors: {context['errors']}")
                
                # Verify the store has data after workflow execution
                store_categories = self.store.get_all_nodes()
                logger.debug(f"Store contains {len(store_categories)} categories after workflow execution")
                
                # If the workflow didn't produce a taxonomy but the store has data,
                # generate one directly from the store
                if len(store_categories) > 1:  # More than just the root node
                    logger.info("Generating taxonomy directly from store")
                    taxonomy = self.store.get_taxonomy_tree(root_category)
                else:
                    logger.warning("Store contains only the root node. Workflow steps did not populate the taxonomy.")
        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            # Create a minimal valid taxonomy
            taxonomy = {
                "category": root_category,
                "subcategories": [],
                "compliance": {},
                "legal": {},
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "error": str(e),
                    "note": "Error generating taxonomy"
                }
            }
            
            # If output path provided, save this minimal taxonomy
            if output_path:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(taxonomy, f, indent=2)
                logger.info(f"Minimal taxonomy saved to {output_path} after error")
        
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
        
        # Generate dynamic compliance areas based on taxonomy content
        compliance_areas = await self._generate_dynamic_compliance_areas(taxonomy, context)
        taxonomy["metadata"]["compliance_areas"] = compliance_areas
            
        # Track search usage for reporting
        search_used = False
        search_results_count = 0
        
        # Check if the context has tools used info
        if context.get("tools_used"):
            # Check if any of the search tools were used
            search_tools = ["search_subcategories", "search_category_info", 
                           "search_compliance_requirements", "search_legal_requirements"]
            for tool_name, count in context.get("tools_used", {}).items():
                if tool_name in search_tools and count > 0:
                    search_used = True
                    search_results_count += count
        
        taxonomy["metadata"].update({
            "generated_at": datetime.now().isoformat(),
            "max_depth": context.get("max_depth"),
            "jurisdictions": context.get("jurisdictions", []),
            "search_used": search_used,
            "search_results_count": search_results_count,
            "domain": root_category
        })
        
        return taxonomy
        
    async def _generate_dynamic_compliance_areas(self, taxonomy: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate dynamic compliance areas based on taxonomy content.
        
        This analyzes the taxonomy structure and content to identify appropriate
        compliance dimensions that are relevant to this particular domain.
        
        Args:
            taxonomy: Complete taxonomy tree
            context: Workflow context
            
        Returns:
            List of compliance areas with descriptions
        """
        # Use compliance agent to analyze taxonomy and suggest areas
        if "compliance" not in self.agents:
            return []
            
        compliance_agent = self.agents["compliance"]
        category = taxonomy.get("category", "")
        
        # Create a concise version of the taxonomy to include in the prompt
        simplified_taxonomy = self._simplify_taxonomy(taxonomy)
        
        # Get prompt for dynamic compliance areas using PromptLoader
        from utils.prompt_utils import get_app_template_loader
        
        prompt_loader = get_app_template_loader()
        prompt = prompt_loader.format_template(
            "compliance-areas",
            category=category,
            simplified_taxonomy=simplified_taxonomy
        )
        
        # Execute with compliance agent
        result = await compliance_agent.execute(prompt)
        
        # Parse results to extract compliance areas
        compliance_areas = []
        
        if isinstance(result, str):
            # Process text to extract areas
            sections = result.split("\n\n")
            current_area = {}
            
            for section in sections:
                if not section.strip():
                    continue
                    
                # Check if this looks like a new compliance area
                lines = [line.strip() for line in section.split("\n") if line.strip()]
                
                if len(lines) >= 2 and (lines[0].startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.")) or 
                                       lines[0].startswith("-") or
                                       ":" in lines[0]):
                    # This looks like a new area
                    if current_area and "name" in current_area:
                        compliance_areas.append(current_area)
                    
                    current_area = {"name": "", "description": "", "importance": ""}
                    
                    # Extract name from first line
                    first_line = lines[0]
                    if ":" in first_line:
                        # Format: "Name: Description"
                        name_part = first_line.split(":", 1)[0]
                        # Remove any numbering or bullets
                        name_part = re.sub(r'^[\d\.\-\*•]+\s*', '', name_part)
                        current_area["name"] = name_part.strip()
                    elif first_line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.")) or first_line.startswith("-"):
                        # Format: "1. Name" or "- Name"
                        name_part = re.sub(r'^[\d\.\-\*•]+\s*', '', first_line)
                        current_area["name"] = name_part.strip()
                    
                    # Process remaining lines for description and importance
                    remaining_text = " ".join(lines[1:])
                    
                    # Look for importance markers
                    importance_markers = ["important because", "important for", "significance", "critical for"]
                    importance_parts = []
                    description_parts = []
                    
                    for part in remaining_text.split(". "):
                        if any(marker in part.lower() for marker in importance_markers):
                            importance_parts.append(part)
                        else:
                            description_parts.append(part)
                    
                    if importance_parts:
                        current_area["importance"] = ". ".join(importance_parts)
                    if description_parts:
                        current_area["description"] = ". ".join(description_parts)
            
            # Add the last area if it exists
            if current_area and "name" in current_area:
                compliance_areas.append(current_area)
        
        return compliance_areas
        
    def _simplify_taxonomy(self, taxonomy: Dict[str, Any], max_depth: int = 2, current_depth: int = 0) -> str:
        """Create a simplified text representation of the taxonomy.
        
        Args:
            taxonomy: Taxonomy tree or subtree
            max_depth: Maximum depth to include
            current_depth: Current depth in recursion
            
        Returns:
            Text representation of simplified taxonomy
        """
        if not taxonomy:
            return ""
            
        # Add indentation based on depth
        indent = "  " * current_depth
        
        # Start with the category
        result = f"{indent}- {taxonomy.get('category', 'Unknown')}"
        
        # Add description if available and not empty
        description = taxonomy.get("description", "")
        if description:
            # Truncate long descriptions
            if len(description) > 100:
                description = description[:97] + "..."
            result += f": {description}"
        
        result += "\n"
        
        # Recursively add subcategories if we haven't reached max depth
        if current_depth < max_depth and "subcategories" in taxonomy:
            for subcategory in taxonomy.get("subcategories", []):
                result += self._simplify_taxonomy(
                    subcategory, 
                    max_depth=max_depth,
                    current_depth=current_depth + 1
                )
        
        return result
    
    async def _save_taxonomy(self, context: Dict[str, Any]) -> None:
        """Save taxonomy to a file.
        
        Args:
            context: Workflow step context with taxonomy and output path
        """
        taxonomy = context.get("taxonomy", {})
        path = context.get("output_path")
        
        if not path:
            # No output path, nothing to do
            logger.warning("No output path provided, taxonomy not saved")
            return
            
        # Check if taxonomy is valid
        if not taxonomy or not isinstance(taxonomy, dict):
            logger.warning(f"Empty or invalid taxonomy: {taxonomy}. Creating default structure.")
            # Create a minimal valid structure
            taxonomy = {
                "category": context.get("root_category", "Unknown"),
                "subcategories": [],
                "compliance": {},
                "legal": {},
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "note": "Default structure due to empty taxonomy result"
                }
            }
        
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