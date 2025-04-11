"""Pattern integration for Taxonomy Planner."""

import asyncio
from typing import Dict, Any, List, Optional

from symphony import Symphony
from symphony.patterns.base import Pattern
from symphony.patterns.reasoning.chain_of_thought import ChainOfThoughtPattern
from symphony.patterns.tool_usage.recursive_tool_use import RecursiveToolUsePattern
from symphony.patterns.multi_agent.expert_panel import ExpertPanelPattern
from symphony.patterns.tool_usage.verify_execute import VerifyExecutePattern
from symphony.patterns.learning.reflection import ReflectionPattern

class SearchEnhancedExplorationPattern(RecursiveToolUsePattern):
    """Pattern for taxonomy exploration enhanced with search capabilities.
    
    This implementation includes several enhancements:
    1. Parallel exploration of subcategories for better performance
    2. Breadth limiting to prevent explosive growth of categories
    3. Support for different exploration strategies
    4. Incremental persistence using TaxonomyStore
    """
    
    def __init__(self, config):
        """Initialize the pattern with config."""
        super().__init__(config)
    
    @property
    def name(self) -> str:
        return "search_enhanced_exploration"
    
    @property
    def description(self) -> str:
        return "Explores taxonomy using both knowledge base and search results with optimized strategies"
    
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Execute the pattern.
        
        Args:
            context: Execution context
            
        Returns:
            Exploration results
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Executing SearchEnhancedExplorationPattern for context: {context.get('category', 'Unknown')}")
        
        # Get parameters from context
        category = context.get("category")
        parent = context.get("parent")
        store = context.get("store")  # Using TaxonomyStore instead of memory
        agent = context.get("agent")
        tools = context.get("tools", [])
        depth = context.get("depth", 1)
        max_depth = context.get("max_depth", 5)
        breadth_limit = context.get("breadth_limit", 10)  # Maximum subcategories per node
        strategy = context.get("strategy", "parallel")  # Exploration strategy
        initial_categories = context.get("initial_categories", [])  # Categories from planner
        
        # Log key parameters
        logger.debug(f"Pattern execution - Category: {category}, Depth: {depth}/{max_depth}, Tools: {tools}")
        
        if not store:
            logger.error("TaxonomyStore not provided in context!")
            return {"category": category, "subcategories": []}
        
        if not agent:
            logger.error("Agent not provided in context!")
            return {"category": category, "subcategories": []}
        
        # Ensure required tools are available
        required_tools = ["search_subcategories", "search_category_info"]
        for tool in required_tools:
            if tool not in tools:
                tools.append(tool)
        
        # Step 1: Get subcategories from knowledge base
        kb_result = await agent.execute(
            f"List subcategories of {category} from internal knowledge",
            use_tools=["search_knowledge_base"]
        )
        kb_subcategories = self._extract_subcategories(kb_result)
        
        # Step 2: Get subcategories from search
        search_subcategories = await agent.execute(
            f"Search for subcategories of {category}",
            use_tools=["search_subcategories"]
        )
        search_results = self._extract_subcategories(search_subcategories)
        
        # Step 3: Include initial categories from planner if this is the root category
        if parent is None and initial_categories:
            kb_subcategories.extend(initial_categories)
        
        # Step 4: Merge and validate subcategories
        all_subcategories = list(set(kb_subcategories + search_results))
        
        # Step 5: Apply breadth limit if needed to avoid explosion
        if len(all_subcategories) > breadth_limit:
            # Ask agent to prioritize subcategories
            prioritization_result = await agent.execute(
                f"From this list of subcategories for {category}, select the {breadth_limit} most important ones: "
                f"{', '.join(all_subcategories)}",
                use_tools=[]
            )
            all_subcategories = self._extract_subcategories(prioritization_result)[:breadth_limit]
        
        # Step 6: Validate and filter subcategories
        validation_result = await agent.execute(
            f"Validate and filter subcategories for {category}: {', '.join(all_subcategories)}"
        )
        final_subcategories = self._extract_subcategories(validation_result)
        
        # Step 7: Gather enhanced information for the current category
        enhanced_info_prompt = (
            f"For the category '{category}', provide the following information in a structured format:\n"
            f"1. A concise description (1-2 sentences)\n"
            f"2. 2-3 typical enforcement examples or challenges\n"
            f"3. 2-3 recent social media trends related to this category\n"
            f"4. Risk level assessment (High, Medium, or Low) with brief justification\n"
            f"5. 2-3 common detection methods"
        )
        
        enhanced_info = await agent.execute(
            enhanced_info_prompt,
            use_tools=["search_category_info"]
        )
        
        # Extract structured information from response
        metadata = self._extract_enhanced_metadata(enhanced_info)
        
        # Step 8: Add validated subcategories to store with enhanced metadata
        for subcategory in final_subcategories:
            store.add_node(subcategory, parent=category)
        
        # Update the current category with enhanced metadata
        current_node = store.get_node(category) or {}
        current_node.update(metadata)
        store.nodes[category] = current_node
        
        # Persist store incrementally
        store.save()
        
        # Step 9: Explore subcategories based on strategy
        if depth < max_depth:
            if strategy == "parallel":
                # Parallel exploration
                await self._explore_parallel(final_subcategories, category, context, depth)
            elif strategy == "breadth_first":
                # Breadth-first exploration
                await self._explore_breadth_first(final_subcategories, category, context, depth)
            else:
                # Default to depth-first
                await self._explore_depth_first(final_subcategories, category, context, depth)
        
        return {
            "category": category,
            "subcategories": final_subcategories,
            **metadata  # Include enhanced metadata in response
        }
    
    async def _explore_parallel(self, subcategories: List[str], parent: str, context: Dict[str, Any], depth: int) -> None:
        """Explore subcategories in parallel.
        
        Args:
            subcategories: List of subcategories to explore
            parent: Parent category
            context: Original execution context
            depth: Current depth level
        """
        tasks = []
        
        for subcategory in subcategories:
            # Create new context for subcategory
            subcontext = dict(context)
            subcontext["category"] = subcategory
            subcontext["parent"] = parent
            subcontext["depth"] = depth + 1
            
            # Create task
            task = asyncio.create_task(self.execute(subcontext))
            tasks.append(task)
        
        # Run all tasks concurrently
        if tasks:
            await asyncio.gather(*tasks)
    
    async def _explore_breadth_first(self, subcategories: List[str], parent: str, context: Dict[str, Any], depth: int) -> None:
        """Explore subcategories in breadth-first order.
        
        Args:
            subcategories: List of subcategories to explore
            parent: Parent category
            context: Original execution context
            depth: Current depth level
        """
        # Explore all siblings at this level before moving deeper
        queue = [(subcategory, parent, depth + 1) for subcategory in subcategories]
        
        while queue:
            subcategory, parent, current_depth = queue.pop(0)
            
            # Create new context for subcategory
            subcontext = dict(context)
            subcontext["category"] = subcategory
            subcontext["parent"] = parent
            subcontext["depth"] = current_depth
            
            # Explore this subcategory
            await self.execute(subcontext)
            
            # No need to add more subcategories to queue - already handled in execute
    
    async def _explore_depth_first(self, subcategories: List[str], parent: str, context: Dict[str, Any], depth: int) -> None:
        """Explore subcategories in depth-first order.
        
        Args:
            subcategories: List of subcategories to explore
            parent: Parent category
            context: Original execution context
            depth: Current depth level
        """
        # Explore each branch completely before moving to siblings
        for subcategory in subcategories:
            # Create new context for subcategory
            subcontext = dict(context)
            subcontext["category"] = subcategory
            subcontext["parent"] = parent
            subcontext["depth"] = depth + 1
            
            # Recursive call - depth-first
            await self.execute(subcontext)
    
    def _extract_subcategories(self, result: Any) -> List[str]:
        """Extract subcategories from a result."""
        if isinstance(result, str):
            # Extract from text
            subcategories = []
            lines = result.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("- ") or line.startswith("* ") or line.startswith("•"):
                    try:
                        subcategory = line[2:].split(":")[0].strip()
                        if subcategory:
                            subcategories.append(subcategory)
                    except IndexError:
                        pass
                elif line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
                    try:
                        subcategory = line.split(".", 1)[1].split(":")[0].strip()
                        if subcategory:
                            subcategories.append(subcategory)
                    except IndexError:
                        pass
            return subcategories
        elif isinstance(result, dict) and "subcategories" in result:
            # Extract from dictionary
            return result["subcategories"]
        elif isinstance(result, list):
            # Already a list
            return result
        else:
            # Unknown format
            return []
            
    def _extract_enhanced_metadata(self, result: str) -> Dict[str, Any]:
        """Extract enhanced metadata from agent response.
        
        Args:
            result: Textual response from agent
            
        Returns:
            Dictionary of extracted metadata
        """
        # Initialize with empty values
        metadata = {
            "description": "",
            "enforcement_examples": [],
            "social_media_trends": [],
            "risk_level": "",
            "detection_methods": []
        }
        
        if not result or not isinstance(result, str):
            return metadata
        
        # Split text into sections
        lines = result.split("\n")
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Check for section headers
            if "description" in line.lower() or line.startswith("1."):
                current_section = "description"
                # Extract description from this line if it contains a colon
                if ":" in line:
                    metadata["description"] = line.split(":", 1)[1].strip()
                continue
                
            if "enforcement" in line.lower() or "example" in line.lower() or line.startswith("2."):
                current_section = "enforcement_examples"
                continue
                
            if "social media" in line.lower() or "trend" in line.lower() or line.startswith("3."):
                current_section = "social_media_trends"
                continue
                
            if "risk" in line.lower() or line.startswith("4."):
                current_section = "risk_level"
                # Extract risk level from this line if it contains a colon
                if ":" in line:
                    metadata["risk_level"] = line.split(":", 1)[1].strip()
                # Also check for High/Medium/Low directly in the line
                elif any(level in line for level in ["High", "Medium", "Low"]):
                    for level in ["High", "Medium", "Low"]:
                        if level in line:
                            metadata["risk_level"] = level
                            break
                continue
                
            if "detection" in line.lower() or "method" in line.lower() or line.startswith("5."):
                current_section = "detection_methods"
                continue
            
            # Process content based on current section
            if current_section == "description" and not metadata["description"]:
                metadata["description"] = line
                
            elif current_section == "enforcement_examples":
                # Check if line is a list item
                if line.startswith(("-", "*", "•")) or (len(line) >= 2 and line[0].isdigit() and line[1] == "."):
                    item = line[2:].strip() if line.startswith(("-", "*", "•")) else line[2:].strip()
                    metadata["enforcement_examples"].append(item)
                elif metadata["enforcement_examples"] and line:  # If not a list item but we're in this section
                    metadata["enforcement_examples"].append(line)
                    
            elif current_section == "social_media_trends":
                # Check if line is a list item
                if line.startswith(("-", "*", "•")) or (len(line) >= 2 and line[0].isdigit() and line[1] == "."):
                    item = line[2:].strip() if line.startswith(("-", "*", "•")) else line[2:].strip()
                    metadata["social_media_trends"].append(item)
                elif metadata["social_media_trends"] and line:  # If not a list item but we're in this section
                    metadata["social_media_trends"].append(line)
                    
            elif current_section == "risk_level" and not metadata["risk_level"]:
                metadata["risk_level"] = line
                
            elif current_section == "detection_methods":
                # Check if line is a list item
                if line.startswith(("-", "*", "•")) or (len(line) >= 2 and line[0].isdigit() and line[1] == "."):
                    item = line[2:].strip() if line.startswith(("-", "*", "•")) else line[2:].strip()
                    metadata["detection_methods"].append(item)
                elif metadata["detection_methods"] and line:  # If not a list item but we're in this section
                    metadata["detection_methods"].append(line)
        
        # Limit lists to reasonable sizes
        for key in ["enforcement_examples", "social_media_trends", "detection_methods"]:
            if len(metadata[key]) > 5:
                metadata[key] = metadata[key][:5]
                
        return metadata

def create_patterns() -> Dict[str, Pattern]:
    """Create patterns for taxonomy generation."""
    # Create base configurations for each pattern
    chain_of_thought_config = {
        "name": "chain_of_thought",
        "description": "Sequential reasoning with explicit intermediate steps",
        "max_iterations": 5
    }
    
    recursive_exploration_config = {
        "name": "recursive_exploration",
        "description": "Recursively explore a hierarchy",
        "max_iterations": 10
    }
    
    search_enhanced_config = {
        "name": "search_enhanced_exploration",
        "description": "Explores taxonomy using both knowledge base and search results with optimized strategies",
        "max_iterations": 10
    }
    
    expert_panel_config = {
        "name": "expert_panel",
        "description": "Multiple experts collaborating on a solution",
        "max_iterations": 3
    }
    
    verify_execute_config = {
        "name": "verify_execute",
        "description": "Verify a plan before execution",
        "max_iterations": 2
    }
    
    reflection_config = {
        "name": "reflection",
        "description": "Reflect on previous decisions",
        "max_iterations": 2
    }
    
    # Create pattern instances with configurations
    patterns = {
        "chain_of_thought": ChainOfThoughtPattern(chain_of_thought_config),
        "recursive_exploration": RecursiveToolUsePattern(recursive_exploration_config),
        "search_enhanced_exploration": SearchEnhancedExplorationPattern(search_enhanced_config),
        "expert_panel": ExpertPanelPattern(expert_panel_config),
        "verify_execute": VerifyExecutePattern(verify_execute_config),
        "reflection": ReflectionPattern(reflection_config),
    }
    
    return patterns

async def apply_pattern(
    symphony: Symphony,
    pattern: Pattern,
    agent: Any,
    task: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Any:
    """Apply a Symphony pattern to a task.
    
    Args:
        symphony: Symphony instance
        pattern: Pattern to apply
        agent: Agent to use with pattern
        task: Task description
        context: Context for the pattern
        **kwargs: Additional pattern arguments
        
    Returns:
        Result of pattern application
    """
    context = context or {}
    
    return await symphony.patterns.apply_pattern(
        pattern=pattern,
        agent=agent,
        task=task,
        context=context,
        **kwargs
    )