# Externalizing Prompt Templates in Taxonomy Planner

This guide provides a detailed plan for refactoring the Taxonomy Planner to properly externalize all prompt templates.

## Current State Analysis

The current implementation uses a hybrid approach to prompt templates:

1. **Hardcoded Templates**:
   - Most agent instructions are directly embedded in Python code
   - These templates include dynamic elements (interpolated variables)
   - Templates are mixed with business logic in main functions

2. **External Templates**:
   - The `task-prompts/` directory contains some template files
   - These external templates aren't consistently used in the codebase
   - The loading mechanism for these templates isn't standardized

## Example of Current Hardcoded Templates

In `generate_taxonomy.py`:

```python
planning_agent_builder.create(
    name="TaxonomyPlanner",
    role="Planning comprehensive taxonomies",
    instruction_template=(
        f"Develop a hierarchical taxonomy plan for the domain: {category}. "
        f"Include categories, subcategories, and plan for enhanced fields: "
        f"{', '.join(enhanced_fields)}. "
        f"Consider the following jurisdictions: {', '.join(jurisdictions)}."
    )
)
```

## Problems with the Current Approach

1. **Lack of Separation of Concerns**:
   - Prompt content is mixed with application logic
   - Makes it difficult to iterate on prompts independently
   
2. **Inconsistent Implementation**:
   - Some templates are external, some are hardcoded
   - No standardized approach for loading and formatting
   
3. **Limited Maintainability**:
   - Changing prompts requires code changes
   - No version control for prompts
   - Difficult to manage prompt variants

4. **Difficult Testing**:
   - Cannot test prompt templates independently
   - Hard to verify prompt changes in isolation

## Complete Refactoring Plan

### 1. Create Template Infrastructure

First, establish proper template management infrastructure:

```python
# prompt_manager.py

import os
import logging
from typing import Dict, Any, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

class TemplateNotFoundError(Exception):
    """Raised when a requested template cannot be found."""
    pass

class PromptManager:
    """Manages loading and formatting of prompt templates."""
    
    def __init__(self, template_dirs: Dict[str, str] = None):
        """Initialize prompt manager.
        
        Args:
            template_dirs: Dictionary mapping template types to directory paths
        """
        self.template_dirs = template_dirs or {
            "task": "task-prompts",
            "system": "system-prompts",
            "example": "example-prompts"
        }
        
        # Validate template directories
        for template_type, dir_path in self.template_dirs.items():
            if not os.path.isdir(dir_path):
                logger.warning(f"Template directory {dir_path} for {template_type} does not exist")
    
    @lru_cache(maxsize=100)
    def load_template(self, template_name: str, template_type: str = "task") -> str:
        """Load template from filesystem with caching.
        
        Args:
            template_name: Template name without extension
            template_type: Type of template (task, system, example)
            
        Returns:
            Template content as string
            
        Raises:
            TemplateNotFoundError: If template cannot be found
        """
        template_dir = self.template_dirs.get(template_type)
        if not template_dir:
            raise ValueError(f"Unknown template type: {template_type}")
            
        template_path = os.path.join(template_dir, f"{template_name}.txt")
        
        try:
            with open(template_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            raise TemplateNotFoundError(f"Template {template_name} not found at {template_path}")
    
    def format_template(self, template_name: str, template_type: str = "task", **kwargs) -> str:
        """Load and format a template with the provided variables.
        
        Args:
            template_name: Template name without extension
            template_type: Type of template (task, system, example)
            **kwargs: Variables to substitute in the template
            
        Returns:
            Formatted template string
            
        Raises:
            TemplateNotFoundError: If template cannot be found
            KeyError: If a required variable is missing
        """
        template_content = self.load_template(template_name, template_type)
        
        try:
            return template_content.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing required variable {e} in template {template_name}")
            raise
```

### 2. Externalize All Templates

Extract all hardcoded templates to files in the appropriate directories:

#### Example: Planning Template

Create `task-prompts/planning.txt`:

```
Develop a hierarchical taxonomy plan for the domain: {category}.

Include categories, subcategories, and plan for the following enhanced fields:
{enhanced_fields}

Consider the following jurisdictions:
{jurisdictions}

Your output should include:
1. A high-level overview of the domain
2. Main categories (5-10)
3. First level of subcategories for each main category
4. Recommendations for taxonomy organization
```

#### Example: Explorer Template

Create `task-prompts/exploration.txt`:

```
Explore the given taxonomy category and identify subcategories for: {category}.

Research each category to provide enhanced metadata including:
{enhanced_fields}

Consider regulations in these jurisdictions:
{jurisdictions}

For each subcategory:
1. Provide a clear name
2. Add relevant metadata for all enhanced fields
3. Suggest further subcategories where appropriate
4. Link to relevant regulations when possible

Base your work on this initial taxonomy plan:
{taxonomy_plan}
```

### 3. Refactor Code to Use Template Manager

Update the code to use the new template manager:

```python
# First, initialize the prompt manager globally
prompt_manager = PromptManager({
    "task": "task-prompts",
    "system": "system-prompts",
    "example": "example-prompts"
})

# Then, use it in the agent creation
async def create_planning_agent(workflow_system, category: str, enhanced_fields: List[str], jurisdictions: List[str]):
    """Create planning agent with externalized template."""
    
    # Format the planning template
    instruction = prompt_manager.format_template(
        "planning",
        category=category,
        enhanced_fields=", ".join(enhanced_fields),
        jurisdictions=", ".join(jurisdictions)
    )
    
    # Create and return the agent
    planning_agent_builder = workflow_system.build_agent()
    planning_agent_builder.create(
        name="TaxonomyPlanner",
        role="Planning comprehensive taxonomies",
        instruction_template=instruction
    )
    
    planning_agent = planning_agent_builder.build()
    planning_agent_id = await workflow_system.agents.save_agent(planning_agent)
    
    return planning_agent, planning_agent_id
```

### 4. Update Generation Functions

Refactor the main generation functions to use the externalized templates:

```python
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
    """Generate a compliance-focused taxonomy for the given category."""
    # ...existing setup code...
    
    if enhanced:
        # Use enhanced workflow with externalized templates
        workflow_system = await setup_workflow_system(storage_dir)
        
        # Create agents with externalized templates
        planning_agent, planning_agent_id = await create_planning_agent(
            workflow_system, category, enhanced_fields, jurisdictions
        )
        
        explorer_agent, explorer_agent_id = await create_explorer_agent(
            workflow_system, category, enhanced_fields, jurisdictions
        )
        
        # Create workflow and steps
        # ...rest of function implementation...
```

### 5. Add Template Validation

Implement template validation to ensure all required variables are present:

```python
def validate_template_variables(template_content: str, available_vars: Dict[str, Any]) -> List[str]:
    """Validate that all variables required by a template are available.
    
    Args:
        template_content: Template content string
        available_vars: Dictionary of available variables
        
    Returns:
        List of missing variable names, empty if all are available
    """
    # Extract variable names from template using regex
    import re
    var_pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
    required_vars = set(re.findall(var_pattern, template_content))
    
    # Check which variables are missing
    missing_vars = [var for var in required_vars if var not in available_vars]
    
    return missing_vars
```

## Implementation Timeline

1. **Phase 1: Infrastructure Setup**
   - Create PromptManager class
   - Set up directory structure
   - Add template loading utilities
   
2. **Phase 2: Template Extraction**
   - Identify all hardcoded templates
   - Extract to external files
   - Document variables and purpose
   
3. **Phase 3: Code Refactoring**
   - Update agent creation code
   - Refactor task generation
   - Add validation
   
4. **Phase 4: Testing and Validation**
   - Add tests for template loading
   - Verify template substitution
   - Ensure functional equivalence

## Best Practices Going Forward

1. **Never hardcode templates** in Python code
2. **Version templates** when making significant changes
3. **Document variables** in template files with comments
4. Implement **automated validation** of template variables
5. Use a **consistent formatting style** across all templates
6. Consider adding **template validation tests** to ensure they remain valid

## Conclusion

By externalizing all prompt templates, we'll significantly improve the maintainability and flexibility of the Taxonomy Planner application. This approach separates prompt content from business logic, making it easier to iterate on prompts independently of code changes.

The refactored system will support:

- Independent prompt iteration
- Better version control
- A/B testing of different prompt variants
- Easier prompt translation for multilingual support
- Better collaboration between prompt engineers and developers