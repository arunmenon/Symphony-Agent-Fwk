"""Pattern integration for Taxonomy Planner."""

from typing import Dict, Any, List, Optional, Callable

from symphony import Symphony
from symphony.patterns import (
    Pattern, 
    ChainOfThoughtPattern,
    RecursiveToolUsePattern,
    ExpertPanelPattern,
    VerifyExecutePattern,
    ReflectionPattern
)

class SearchEnhancedExplorationPattern(RecursiveToolUsePattern):
    """Pattern for taxonomy exploration enhanced with search capabilities."""
    
    @property
    def name(self) -> str:
        return "search_enhanced_exploration"
    
    @property
    def description(self) -> str:
        return "Explores taxonomy using both knowledge base and search results"
    
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
        memory = context.get("memory")
        agent = context.get("agent")
        tools = context.get("tools", [])
        depth = context.get("depth", 1)
        max_depth = context.get("max_depth", 5)
        
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
        
        # Step 3: Merge and validate subcategories
        all_subcategories = list(set(kb_subcategories + search_results))
        validation_result = await agent.execute(
            f"Validate and filter subcategories for {category}: {', '.join(all_subcategories)}"
        )
        final_subcategories = self._extract_subcategories(validation_result)
        
        # Step 4: Add validated subcategories to memory
        for subcategory in final_subcategories:
            memory.add_node(subcategory, parent=category)
        
        # Step 5: Recursively explore each subcategory
        if depth < max_depth:
            for subcategory in final_subcategories:
                # Create new context for subcategory
                subcontext = dict(context)
                subcontext["category"] = subcategory
                subcontext["parent"] = category
                subcontext["depth"] = depth + 1
                
                # Recursive call
                await self.execute(subcontext)
        
        return {
            "category": category,
            "subcategories": final_subcategories
        }
    
    def _extract_subcategories(self, result: Any) -> List[str]:
        """Extract subcategories from a result."""
        if isinstance(result, str):
            # Extract from text
            subcategories = []
            lines = result.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("- ") or line.startswith("* "):
                    subcategory = line[2:].split(":")[0].strip()
                    subcategories.append(subcategory)
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
    patterns = {
        "chain_of_thought": ChainOfThoughtPattern(),
        "recursive_exploration": RecursiveToolUsePattern(),
        "search_enhanced_exploration": SearchEnhancedExplorationPattern(),
        "expert_panel": ExpertPanelPattern(),
        "verify_execute": VerifyExecutePattern(),
        "reflection": ReflectionPattern(),
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