# Taxonomy Planner User Guide

This guide provides instructions for using the Taxonomy Planner application to generate comprehensive hierarchical taxonomies with compliance and legal mappings.

## Getting Started

### Installation

The Taxonomy Planner is included as part of the Symphony framework. To use it:

1. Make sure you have Symphony installed:
   ```bash
   pip install -e .
   ```

2. (Optional) Set up SerAPI integration for enhanced search capabilities:
   ```bash
   export SERAPI_API_KEY="your-api-key"
   ```

### Basic Usage

Here's a simple example of generating a taxonomy:

```python
import asyncio
from applications.taxonomy_planner import generate_taxonomy

async def main():
    # Generate a technology taxonomy
    taxonomy = await generate_taxonomy(
        root_category="Technology",
        output_path="./technology_taxonomy.json"
    )
    
    print(f"Generated taxonomy with {len(taxonomy['subcategories'])} top-level categories")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

The Taxonomy Planner can be configured with various parameters:

### Core Parameters

- `root_category`: The root category for the taxonomy
- `jurisdictions`: List of jurisdictions for compliance and legal mapping
- `max_depth`: Maximum depth of the taxonomy hierarchy
- `output_path`: File path for saving the generated taxonomy

### Custom Configuration

For more advanced configuration, create a custom `TaxonomyConfig`:

```python
from applications.taxonomy_planner import TaxonomyConfig, TaxonomyPlanner

# Create custom configuration
config = TaxonomyConfig()
config.max_depth = 4  # Set max depth to 4 levels
config.default_jurisdictions = ["USA", "EU", "Japan"]  # Set default jurisdictions

# Configure search settings
config.search_config["enable_search"] = True
config.search_config["max_requests_per_minute"] = 30

# Create planner with custom config
planner = TaxonomyPlanner(config=config)
```

### Domain-Specific Configuration

You can add domain-specific presets to the configuration:

```python
# Add a preset for medical domains
config.domain_presets["medical"] = {
    "top_level_categories": [
        "Pharmaceuticals", "Medical Devices", "Diagnostics", 
        "Therapies", "Healthcare IT"
    ],
    "knowledge_sources": ["FDA Database", "Medical Journals", "WHO Guidelines"]
}

# Use the preset when generating a taxonomy
taxonomy = await planner.generate_taxonomy(
    root_category="Medical",
    jurisdictions=["USA", "EU", "International"]
)
```

## Working with Agents

The Taxonomy Planner uses a multi-agent approach with specialized agents:

### Agent Roles

- **Planner Agent**: Coordinates the overall taxonomy structure
- **Explorer Agent**: Explores subcategories using depth-first search
- **Compliance Agent**: Maps compliance requirements to taxonomy nodes
- **Legal Agent**: Maps applicable laws to taxonomy nodes

### Customizing Agent Behavior

You can customize agent behavior through the configuration:

```python
# Configure agent settings
config.agent_configs["explorer"] = {
    "preset": "domain_expert",
    "model": "gpt-4",
    "temperature": 0.7  # Add creativity to subcategory generation
}

# Configure compliance agent
config.agent_configs["compliance"] = {
    "preset": "compliance",
    "model": "gpt-4",
    "temperature": 0.2  # Keep compliance information accurate
}
```

## Pattern Usage

The Taxonomy Planner uses specialized patterns for taxonomy generation:

### Available Patterns

- **Chain of Thought**: Used for initial planning
- **Search Enhanced Exploration**: Explores taxonomy branches with search
- **Verify Execute**: Validates mapping results
- **Reflection**: Improves output quality through reflection

### Customizing Patterns

You can customize pattern behavior through the configuration:

```python
# Configure chain of thought pattern
config.pattern_configs["chain_of_thought"] = {
    "reasoning_steps": 5
}

# Configure recursive exploration pattern
config.pattern_configs["recursive_exploration"] = {
    "max_depth": 5,
    "breadth_limit": 10  # Limit subcategories per node
}
```

## Search Integration

The Taxonomy Planner can use web search to enhance taxonomy completeness:

### Configuring Search

Configure the search functionality through the configuration:

```python
# Enable search
config.search_config["enable_search"] = True

# Configure search parameters
config.search_config["max_requests_per_minute"] = 30
config.search_config["results_per_query"] = 5
config.search_config["search_depth"] = 3  # Search depth (1=top level, 5=all levels)
```

### Search API Key

To use the search functionality with real results:

1. Sign up for a [SerAPI account](https://serpapi.com/)
2. Set the API key:
   ```bash
   export SERAPI_API_KEY="your-api-key"
   ```
   
   Or in your code:
   ```python
   import os
   os.environ["SERAPI_API_KEY"] = "your-api-key"
   ```

## Understanding Output

The Taxonomy Planner generates a hierarchical JSON structure:

### Output Format

```json
{
  "category": "Root Category",
  "subcategories": [
    {
      "category": "Subcategory 1",
      "subcategories": [...],
      "compliance": {
        "USA": ["Requirement 1", "Requirement 2"],
        "EU": ["EU Requirement 1"]
      },
      "legal": {
        "USA": [
          {"title": "US Law 1", "description": "Description"}
        ],
        "EU": [
          {"title": "EU Regulation 1", "description": "Description"}
        ]
      }
    }
  ],
  "compliance": {...},
  "legal": {...},
  "metadata": {
    "generated_at": "2025-04-08T14:30:00.000000",
    "max_depth": 5,
    "jurisdictions": ["USA", "EU", "International"]
  }
}
```

### Working with Output

You can process the output for various purposes:

```python
import json

# Load a saved taxonomy
with open("technology_taxonomy.json", "r") as f:
    taxonomy = json.load(f)

# Print all top-level categories
for subcategory in taxonomy["subcategories"]:
    print(subcategory["category"])

# Find all items with specific compliance requirements
def find_items_with_requirement(taxonomy, requirement, jurisdiction="USA"):
    results = []
    
    def search_node(node):
        compliance = node.get("compliance", {}).get(jurisdiction, [])
        if any(req for req in compliance if requirement.lower() in req.lower()):
            results.append(node["category"])
        
        for subcategory in node.get("subcategories", []):
            search_node(subcategory)
    
    search_node(taxonomy)
    return results

# Find all items requiring licensing
licensing_items = find_items_with_requirement(taxonomy, "license")
print(f"Items requiring licensing: {licensing_items}")
```

## Examples

See the following examples for detailed usage:

- `examples/taxonomy_planner_example.py`: Basic and advanced usage examples
- `applications/taxonomy_planner/README.md`: Overview and architecture
- `applications/taxonomy_planner/docs/extending.md`: Extending the application