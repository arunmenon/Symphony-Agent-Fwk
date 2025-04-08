"""Pattern integration for Taxonomy Planner."""

import asyncio
from typing import Dict, Any, List, Optional, Callable, Set, Tuple

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
        
        # Step 7: Add validated subcategories to store
        for subcategory in final_subcategories:
            store.add_node(subcategory, parent=category)
        
        # Persist store incrementally
        store.save()
        
        # Step 8: Explore subcategories based on strategy
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
            "subcategories": final_subcategories
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
            result = await self.execute(subcontext)
            
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