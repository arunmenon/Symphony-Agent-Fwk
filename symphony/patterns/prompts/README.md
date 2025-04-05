# Symphony Pattern Prompt Templates

This directory contains externalized prompt templates for Symphony's pattern library.

## Overview

Instead of hardcoding prompts in pattern implementations, we store them in YAML files organized by pattern category. This approach provides several benefits:

- **Maintainability**: Templates can be updated without changing code
- **Flexibility**: Multiple prompt styles (default, academic, creative, etc.) for each pattern
- **Versioning**: New prompt variations can be added without breaking existing ones
- **Reusability**: Common prompt structures can be shared across patterns

## Directory Structure

```
prompts/
├── __init__.py             # PromptTemplateRegistry implementation
├── README.md               # This file
├── learning/               # Learning patterns
│   ├── few_shot.yaml       # Few-shot learning templates
│   └── reflection.yaml     # Reflection pattern templates
├── multi_agent/            # Multi-agent patterns
│   └── expert_panel.yaml   # Expert panel templates
├── reasoning/              # Reasoning patterns
│   ├── chain_of_thought.yaml  # Chain of thought templates
│   └── step_back.yaml      # Step back templates
├── tool_usage/             # Tool usage patterns
│   ├── multi_tool_chain.yaml  # Multi-tool chain templates
│   ├── recursive_tool_use.yaml  # Recursive tool use templates
│   └── verify_execute.yaml  # Verify-execute templates
└── verification/           # Verification patterns
    ├── critic_review.yaml  # Critic review templates
    └── self_consistency.yaml  # Self-consistency templates
```

## Template Format

Each template file contains one or more prompt versions for a specific pattern. The basic structure is:

```yaml
default:                # Prompt style/version
  content: |            # The actual template content with {placeholders}
    Task: {task}
    
    {examples_text}
    {format_instructions}
    
    Input: {query}
    Output:
  description: "Default few-shot learning prompt"

academic:               # Another prompt style
  content: |            # Different content for academic style
    You are presented with a task that requires application...
  description: "Academic-focused prompt"
```

For more complex patterns, sections can be nested:

```yaml
default:
  expert:               # Sub-component for expert prompts
    content: |
      You are an expert analyzing this question...
    description: "Expert panel member prompt"
  
  synthesis:            # Sub-component for synthesis prompts
    content: |
      You are tasked with synthesizing the insights...
    description: "Synthesis prompt"
```

## Using Templates in Pattern Implementation

Templates are accessed through the `PromptTemplateRegistry`:

```python
from symphony.patterns.prompts import get_registry

# In your pattern execution method:
prompt_registry = get_registry()
prompt_style = self.config.metadata.get("prompt_style", "default")

# Get a template and render it with variables
try:
    prompt = prompt_registry.render_template(
        "category.pattern_name",  # e.g., "reasoning.chain_of_thought"
        {"query": query, "other_var": value},
        version=prompt_style
    )
except ValueError:
    # Fallback to default prompt if template not found
    prompt = f"Default hardcoded prompt: {query}"
```

## Adding New Templates

To add a new template:

1. Create a YAML file in the appropriate category directory
2. Define your prompt templates with appropriate styles
3. Use placeholders with curly braces for variable substitution: `{variable_name}`
4. Add a description to document the purpose of each prompt style

## Template Versioning

Prompt styles/versions can be selected at runtime by specifying the `prompt_style` in the pattern configuration:

```python
result = await symphony.patterns.apply_reasoning_pattern(
    "chain_of_thought",
    query,
    config={
        "agent_roles": {"reasoner": agent_id},
        "metadata": {
            "prompt_style": "academic"  # Use the academic style
        }
    }
)
```

If not specified, the `default` version is used.