# Template Refactoring Plan for Taxonomy Planner

This document outlines a systematic approach to refactor the template loading in the Taxonomy Planner application using the new generic `PromptLoader` utility.

## Current Template Usage

The application currently has several places where templates are loaded or defined:

1. **main.py**: Contains the `load_task_prompt()` function which loads templates from the task-prompts directory
2. **generate_taxonomy.py**: Contains hardcoded instruction templates for agents
3. **patterns.py**: Contains hardcoded templates for enhanced metadata
4. **main.py**: Contains hardcoded templates for compliance areas

## Step 1: Create a TaxonomyPromptManager

First, create a specialized prompt manager for Taxonomy Planner that uses our generic PromptLoader:

```python
# utils/taxonomy_prompt_manager.py

import os
import logging
from typing import Dict, Any, List, Optional

from .prompt_utils import PromptLoader

logger = logging.getLogger(__name__)

class TaxonomyPromptManager:
    """Specialized prompt manager for Taxonomy Planner application.
    
    This class uses the generic PromptLoader but specializes it for
    the Taxonomy Planner's specific template needs.
    """
    
    _instance = None  # Singleton instance
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = TaxonomyPromptManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the prompt manager."""
        # Set up loader with the task-prompts directory
        self.app_root = os.path.dirname(os.path.dirname(__file__))
        self.task_prompts_dir = os.path.join(self.app_root, "task-prompts")
        
        # Create loader with primary template directory
        self.loader = PromptLoader(template_dirs=[self.task_prompts_dir])
        logger.info(f"Initialized TaxonomyPromptManager with directory: {self.task_prompts_dir}")
    
    def load_planning_template(self, root_category: str, **variables) -> str:
        """Load and format the planning template.
        
        Args:
            root_category: Root category for taxonomy
            **variables: Additional variables
            
        Returns:
            Formatted template
        """
        all_vars = {"root_category": root_category, **variables}
        return self.loader.format_template("planning", **all_vars)
    
    def load_exploration_template(self, category: str, **variables) -> str:
        """Load and format the exploration template.
        
        Args:
            category: Category to explore
            **variables: Additional variables
            
        Returns:
            Formatted template
        """
        all_vars = {"category": category, **variables}
        return self.loader.format_template("exploration", **all_vars)
    
    def load_compliance_template(self, root_category: str, **variables) -> str:
        """Load and format the compliance template.
        
        Args:
            root_category: Root category for taxonomy
            **variables: Additional variables
            
        Returns:
            Formatted template
        """
        all_vars = {"root_category": root_category, **variables}
        return self.loader.format_template("compliance", **all_vars)
    
    def load_legal_template(self, root_category: str, **variables) -> str:
        """Load and format the legal template.
        
        Args:
            root_category: Root category for taxonomy
            **variables: Additional variables
            
        Returns:
            Formatted template
        """
        all_vars = {"root_category": root_category, **variables}
        return self.loader.format_template("legal", **all_vars)
    
    def load_enhanced_metadata_template(self, category: str) -> str:
        """Load and format the enhanced metadata template.
        
        Args:
            category: Category to get enhanced metadata for
            
        Returns:
            Formatted template
        """
        return self.loader.format_template_string(
            "For the category '${category}', provide the following information in a structured format:\n"
            "1. A concise description (1-2 sentences)\n"
            "2. 2-3 typical enforcement examples or challenges\n"
            "3. 2-3 recent social media trends related to this category\n"
            "4. Risk level assessment (High, Medium, or Low) with brief justification\n"
            "5. 2-3 common detection methods",
            category=category
        )
    
    def load_compliance_areas_template(self, category: str, simplified_taxonomy: str) -> str:
        """Load and format the compliance areas template.
        
        Args:
            category: Category for compliance areas
            simplified_taxonomy: Simplified taxonomy text
            
        Returns:
            Formatted template
        """
        return self.loader.format_template_string(
            "Based on this taxonomy for '${category}', identify 5-8 key compliance areas or dimensions that are "
            "relevant across this domain. For each area, provide:\n"
            "1. Name of the compliance area\n"
            "2. Brief description\n"
            "3. Why it's important for this domain\n\n"
            "Simplified taxonomy:\n${simplified_taxonomy}\n\n"
            "Format as a list with each area clearly labeled.",
            category=category,
            simplified_taxonomy=simplified_taxonomy
        )
    
    def load_agent_instruction_template(self, agent_type: str, **variables) -> str:
        """Load agent instruction template.
        
        Args:
            agent_type: Type of agent (planner, explorer, etc.)
            **variables: Template variables
            
        Returns:
            Formatted template
        """
        if agent_type == "planner":
            return self.loader.format_template_string(
                "Develop a hierarchical taxonomy plan for the domain: ${category}.\n"
                "Include categories, subcategories, and plan for enhanced fields: "
                "${enhanced_fields}.\n"
                "Consider the following jurisdictions: ${jurisdictions}.",
                **variables
            )
        elif agent_type == "explorer":
            return self.loader.format_template_string(
                "Explore the given taxonomy category and identify subcategories for: ${category}.\n"
                "Research each category to provide enhanced metadata including: "
                "${enhanced_fields}.\n"
                "Consider regulations in these jurisdictions: ${jurisdictions}",
                **variables
            )
        else:
            logger.warning(f"Unknown agent type: {agent_type}")
            return f"Instructions for {agent_type} agent"
```

## Step 2: Replace main.py's load_task_prompt function

Replace the `load_task_prompt` function in main.py with the TaxonomyPromptManager:

```python
# Add at top of main.py
from utils.taxonomy_prompt_manager import TaxonomyPromptManager

# Replace load_task_prompt with this:
def load_task_prompt(name):
    """Load a task prompt from a text file.
    
    Args:
        name: Name of the prompt file without extension
        
    Returns:
        String content of the prompt
    """
    # Use the prompt manager instead of direct file loading
    prompt_manager = TaxonomyPromptManager.get_instance()
    
    if name == "planning":
        return prompt_manager.load_planning_template(root_category="{{root_category}}")
    elif name == "exploration":
        return prompt_manager.load_exploration_template(
            category="{{category}}",
            initial_categories="{{initial_categories}}"
        )
    elif name == "compliance":
        return prompt_manager.load_compliance_template(root_category="{{root_category}}")
    elif name == "legal":
        return prompt_manager.load_legal_template(root_category="{{root_category}}")
    else:
        logger.warning(f"Unknown prompt type: {name}")
        return f"Generate content for {name}"
```

## Step 3: Refactor Workflow Steps in main.py

Update the workflow steps in the `_create_workflow_definition` method:

```python
# Current code
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

# Refactored code
prompt_manager = TaxonomyPromptManager.get_instance()
planning_step = (workflow_builder.build_step()
    .name("Planning")
    .description("Plan the taxonomy structure")
    .agent(self.agents["planner"])
    .task(prompt_manager.load_planning_template(root_category="{{root_category}}"))
    .pattern(self.patterns["chain_of_thought"])
    .context_data({
        "tools": ["search_subcategories", "search_category_info"]
    })
    .output_key("plan")
    .build()
)
```

## Step 4: Refactor generate_taxonomy.py

Update the agent creation in `generate_taxonomy.py` to use the TaxonomyPromptManager:

```python
# Add at top of generate_taxonomy.py
from utils.taxonomy_prompt_manager import TaxonomyPromptManager

# Refactor agent creation
prompt_manager = TaxonomyPromptManager.get_instance()
planning_agent_builder.create(
    name="TaxonomyPlanner",
    role="Planning comprehensive taxonomies",
    instruction_template=prompt_manager.load_agent_instruction_template(
        agent_type="planner",
        category=category,
        enhanced_fields=", ".join(enhanced_fields),
        jurisdictions=", ".join(jurisdictions)
    )
)
```

## Step 5: Refactor patterns.py's Enhanced Metadata Template

Update the enhanced metadata prompt in the `SearchEnhancedExplorationPattern` class:

```python
# Add at top of patterns.py
from utils.taxonomy_prompt_manager import TaxonomyPromptManager

# In the execute method of SearchEnhancedExplorationPattern
# Replace the hardcoded enhanced_info_prompt with:
prompt_manager = TaxonomyPromptManager.get_instance()
enhanced_info = await agent.execute(
    prompt_manager.load_enhanced_metadata_template(category=category),
    use_tools=["search_category_info"]
)
```

## Step 6: Refactor Compliance Areas Template in main.py

Update the compliance areas prompt in the `_generate_dynamic_compliance_areas` method:

```python
# Replace the hardcoded prompt with:
prompt_manager = TaxonomyPromptManager.get_instance()
prompt = prompt_manager.load_compliance_areas_template(
    category=category,
    simplified_taxonomy=simplified_taxonomy
)
```

## Step 7: Testing

Create tests to verify that the refactored code:
1. Loads templates correctly
2. Formats variables properly
3. Handles fallbacks for missing templates

## Implementation Order

1. Create the utils/taxonomy_prompt_manager.py file
2. Update main.py's load_task_prompt function
3. Refactor main.py's workflow steps
4. Refactor patterns.py's enhanced metadata template
5. Refactor generate_taxonomy.py's agent creation
6. Refactor compliance areas template in main.py
7. Add tests for the new template loading

This plan systematically refactors all template usage in the Taxonomy Planner application to use the new PromptLoader utility, while maintaining backward compatibility.