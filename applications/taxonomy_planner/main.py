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
    """Main class for taxonomy generation."""
    
    def __init__(self, config: Optional[TaxonomyConfig] = None):
        """Initialize the taxonomy planner.
        
        Args:
            config: Taxonomy configuration
        """
        self.config = config or TaxonomyConfig()
        self.symphony = Symphony()
        self.agents = {}
        self.patterns = {}
        self.memory = None
        self.initialized = False
    
    async def setup(self):
        """Initialize Symphony and set up components."""
        if self.initialized:
            return
        
        # Initialize Symphony
        await self.symphony.setup()
        
        # Register tools
        register_tools(self.symphony, self.config)
        
        # Create agents
        self.agents = create_agents(self.symphony, self.config)
        
        # Create patterns
        self.patterns = create_patterns()
        
        # Create memory
        self.memory = self.symphony.create_memory()
        
        self.initialized = True
    
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
        
        # Override max depth if provided
        if max_depth is not None:
            self.config.max_depth = max_depth
        
        # Initialize taxonomy with root node
        taxonomy = {
            "category": root_category,
            "subcategories": [],
            "compliance": {},
            "legal": {},
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "max_depth": self.config.max_depth,
                "jurisdictions": jurisdictions
            }
        }
        
        # Add root node to memory
        self.memory.add_node(root_category)
        
        # Step 1: Planning phase
        logger.info(f"Planning taxonomy for {root_category}")
        plan = await apply_pattern(
            self.symphony,
            self.patterns["chain_of_thought"],
            self.agents["planner"],
            f"Create a plan for generating a taxonomy for {root_category} across jurisdictions: {', '.join(jurisdictions)}",
            {"max_depth": self.config.max_depth}
        )
        
        # Step 2: Exploration phase with search enhancement
        logger.info(f"Exploring subcategories for {root_category}")
        exploration_result = await apply_pattern(
            self.symphony,
            self.patterns["search_enhanced_exploration"],
            self.agents["explorer"],
            f"Explore the taxonomy tree for {root_category}",
            {
                "category": root_category,
                "parent": None,
                "memory": self.memory,
                "agent": self.agents["explorer"],
                "tools": ["search_knowledge_base", "search_subcategories", "search_category_info"],
                "max_depth": self.config.max_depth
            }
        )
        
        # Step 3: Compliance mapping phase
        logger.info("Mapping compliance requirements")
        compliance_results = {}
        
        # Get all categories from memory
        categories = self.memory.get_all_nodes()
        
        for category in categories:
            compliance_results[category] = {}
            
            for jurisdiction in jurisdictions:
                result = await apply_pattern(
                    self.symphony,
                    self.patterns["verify_execute"],
                    self.agents["compliance"],
                    f"Identify compliance requirements for {category} in {jurisdiction}",
                    {
                        "tools": ["get_compliance_requirements", "search_compliance_requirements"]
                    }
                )
                
                if isinstance(result, dict):
                    compliance_results[category][jurisdiction] = result
                else:
                    # Handle string results
                    requirements = self._extract_requirements(result)
                    compliance_results[category][jurisdiction] = requirements
        
        # Step 4: Legal mapping phase
        logger.info("Mapping legal requirements")
        legal_results = {}
        
        for category in categories:
            legal_results[category] = {}
            
            for jurisdiction in jurisdictions:
                result = await apply_pattern(
                    self.symphony,
                    self.patterns["verify_execute"],
                    self.agents["legal"],
                    f"Identify applicable laws for {category} in {jurisdiction}",
                    {
                        "tools": ["get_applicable_laws", "search_legal_requirements"]
                    }
                )
                
                if isinstance(result, dict):
                    legal_results[category][jurisdiction] = result
                else:
                    # Handle string results
                    laws = self._extract_laws(result)
                    legal_results[category][jurisdiction] = laws
        
        # Step 5: Final refinement phase
        logger.info("Refining taxonomy")
        taxonomy = await self._build_taxonomy_tree(
            root_category, 
            compliance_results, 
            legal_results
        )
        
        # Save output if path provided
        if output_path:
            self._save_taxonomy(taxonomy, output_path)
        
        return taxonomy
    
    async def _build_taxonomy_tree(
        self, 
        root: str, 
        compliance_data: Dict[str, Dict[str, Any]], 
        legal_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build complete taxonomy tree with compliance and legal data.
        
        Args:
            root: Root category
            compliance_data: Compliance data by category and jurisdiction
            legal_data: Legal data by category and jurisdiction
            
        Returns:
            Complete taxonomy tree
        """
        # Build tree recursively
        tree = await self._build_node(root, None, compliance_data, legal_data)
        return tree
    
    async def _build_node(
        self, 
        category: str, 
        parent: Optional[str], 
        compliance_data: Dict[str, Dict[str, Any]], 
        legal_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build a single node and its children recursively.
        
        Args:
            category: Current category
            parent: Parent category
            compliance_data: Compliance data by category and jurisdiction
            legal_data: Legal data by category and jurisdiction
            
        Returns:
            Node and its children
        """
        # Get subcategories for this node
        subcategories = self.memory.get_edges(category) or []
        
        # Get compliance and legal data for this category
        compliance = compliance_data.get(category, {})
        legal = legal_data.get(category, {})
        
        # Create node
        node = {
            "category": category,
            "subcategories": [],
            "compliance": compliance,
            "legal": legal
        }
        
        # Add parent reference if this isn't the root
        if parent:
            node["parent"] = parent
        
        # Process subcategories recursively
        for subcategory in subcategories:
            child_node = await self._build_node(
                subcategory, 
                category, 
                compliance_data, 
                legal_data
            )
            node["subcategories"].append(child_node)
        
        return node
    
    def _extract_requirements(self, text: str) -> List[str]:
        """Extract compliance requirements from text.
        
        Args:
            text: Text containing requirements
            
        Returns:
            List of requirements
        """
        requirements = []
        
        # Simple extraction based on line formatting
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                requirement = line[2:].strip()
                if requirement:
                    requirements.append(requirement)
        
        # If no formatted list found, try to use the whole text
        if not requirements and text.strip():
            return [text.strip()]
        
        return requirements
    
    def _extract_laws(self, text: str) -> List[Dict[str, str]]:
        """Extract laws from text.
        
        Args:
            text: Text containing laws
            
        Returns:
            List of laws
        """
        laws = []
        
        # Simple extraction based on line formatting
        lines = text.strip().split("\n")
        current_law = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                if current_law:
                    laws.append(current_law)
                
                # Start a new law
                title = line[2:].strip()
                current_law = {"title": title}
            elif current_law and line:
                # Add description to current law
                current_law["description"] = line
        
        # Add the last law if not already added
        if current_law:
            laws.append(current_law)
        
        # If no formatted list found, try to use the whole text
        if not laws and text.strip():
            return [{"title": text.strip()}]
        
        return laws
    
    def _save_taxonomy(self, taxonomy: Dict[str, Any], path: str) -> None:
        """Save taxonomy to a file.
        
        Args:
            taxonomy: Taxonomy to save
            path: Output path
        """
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
    config: Optional[TaxonomyConfig] = None
) -> Dict[str, Any]:
    """Generate a taxonomy with compliance and legal mappings.
    
    Args:
        root_category: Root category of the taxonomy
        jurisdictions: List of jurisdictions to map
        max_depth: Maximum depth of taxonomy
        output_path: Path to save the output JSON
        config: Custom configuration
        
    Returns:
        Generated taxonomy
    """
    planner = TaxonomyPlanner(config)
    await planner.setup()
    
    return await planner.generate_taxonomy(
        root_category=root_category,
        jurisdictions=jurisdictions,
        max_depth=max_depth,
        output_path=output_path
    )