# Simplified Template Refactoring Plan

## Core Principles
- **DRY**: Don't repeat template handling logic across applications
- **Minimal Cognitive Load**: One consistent way to load templates
- **Cross-Cutting**: Same approach works for all Symphony applications
- **Framework-First**: Design as a Symphony core utility

## The PromptLoader Class

The existing `PromptLoader` in `prompt_utils.py` is already generic and reusable. This should be the *only* class developers need to work with templates:

```python
# Load from any location
loader = PromptLoader(template_dirs=["/path/to/templates"])

# Format with variables
template = loader.format_template("template_name", var1="value1", var2="value2")

# Validate required variables are provided
missing = loader.validate_variables("template_name", variables_dict)
```

## Refactoring Implementation

### 1. Make PromptLoader Available Application-Wide

Create a simple application-level accessor for the PromptLoader:

```python
# utils/prompt_utils.py (add this function)

def get_app_template_loader():
    """Get application-wide template loader.
    
    Returns:
        A PromptLoader configured for this application
    """
    app_root = os.path.dirname(os.path.dirname(__file__))
    task_prompts_dir = os.path.join(app_root, "task-prompts")
    
    loader = PromptLoader(template_dirs=[task_prompts_dir])
    return loader
```

### 2. Replace load_task_prompt in main.py

```python
# main.py
from utils.prompt_utils import get_app_template_loader

def load_task_prompt(name):
    """Load a task prompt from a text file."""
    loader = get_app_template_loader()
    
    # Keep backward compatibility with variable naming
    if name == "planning":
        return loader.format_template(name, root_category="{{root_category}}")
    elif name == "exploration":
        return loader.format_template(name, 
            category="{{category}}",
            initial_categories="{{initial_categories}}"
        )
    elif name == "compliance":
        return loader.format_template(name, root_category="{{root_category}}")
    elif name == "legal":
        return loader.format_template(name, root_category="{{root_category}}")
    else:
        return f"Generate content for {name}"
```

### 3. Refactor generate_taxonomy.py Agent Creation

```python
from utils.prompt_utils import get_app_template_loader

# Inside generate_enhanced_taxonomy or similar function:
loader = get_app_template_loader()

# For planning agent
planning_template = loader.format_template_string(
    "Develop a hierarchical taxonomy plan for the domain: ${category}.\n"
    "Include categories, subcategories, and plan for enhanced fields: "
    "${enhanced_fields}.\n"
    "Consider the following jurisdictions: ${jurisdictions}.",
    category=category,
    enhanced_fields=", ".join(enhanced_fields),
    jurisdictions=", ".join(jurisdictions)
)

planning_agent_builder.create(
    name="TaxonomyPlanner",
    role="Planning comprehensive taxonomies",
    instruction_template=planning_template
)
```

### 4. Refactor patterns.py

```python
from utils.prompt_utils import get_app_template_loader

# Inside SearchEnhancedExplorationPattern.execute:
loader = get_app_template_loader()
enhanced_info_prompt = loader.format_template_string(
    "For the category '${category}', provide the following information in a structured format:\n"
    "1. A concise description (1-2 sentences)\n"
    "2. 2-3 typical enforcement examples or challenges\n"
    "3. 2-3 recent social media trends related to this category\n"
    "4. Risk level assessment (High, Medium, or Low) with brief justification\n"
    "5. 2-3 common detection methods",
    category=category
)

enhanced_info = await agent.execute(
    enhanced_info_prompt,
    use_tools=["search_category_info"]
)
```

### 5. Considering Long-Term: Moving to Symphony Core

Since this is a cross-cutting concern, eventually the `PromptLoader` should be moved to Symphony core:

```
symphony/utils/prompts/loader.py  # PromptLoader class
symphony/utils/prompts/registry.py  # Enhanced integration with Symphony's registry
```

Applications would then import from Symphony core:

```python
from symphony.utils.prompts import PromptLoader
# or 
from symphony.utils.prompts import get_template_loader
```

## Next Steps for Symphony Core Integration

1. Evaluate the PromptLoader in Taxonomy Planner first
2. Add tests to ensure functionality is solid
3. Move to Symphony core once proven
4. Create integration with Symphony's existing registry system
5. Document the pattern for all applications

This approach:
- Provides a single consistent way to handle templates
- Minimizes cognitive load for developers
- Works across all applications
- Follows DRY principles
- Positions template handling as a core Symphony framework feature