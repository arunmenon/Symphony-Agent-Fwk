# Taxonomy Planner Application

A Symphony-powered application for automated generation of hierarchical taxonomies with compliance and legal mapping capabilities.

## Overview

The Taxonomy Planner is a complete Symphony application that demonstrates how to build sophisticated multi-agent systems for complex tasks. It uses a team of specialized agents to generate comprehensive taxonomies for any domain, with integrated search capabilities to enhance completeness and accuracy.

Key features include:
- Multi-agent taxonomy generation with specialized agent roles
- Search enhancement using SerAPI integration
- Compliance and legal requirement mapping across multiple jurisdictions
- Depth-first recursive exploration of taxonomy branches
- Custom patterns for efficient taxonomy generation
- Configurable taxonomy parameters (depth, breadth, domains)
- LLM call tracing with performance metrics and analysis tools

## Architecture

The application uses a modular architecture with the following components:

- **Core Components**
  - `TaxonomyPlanner`: Main orchestration class
  - `TaxonomyConfig`: Configuration management
  - `TaxonomyStore`: Efficient adjacency list-based persistence
  
- **Specialized Agents**
  - Planner Agent: Coordinates the overall taxonomy structure
  - Explorer Agent: Explores subcategories using depth-first search
  - Compliance Agent: Maps compliance requirements to taxonomy nodes
  - Legal Agent: Maps applicable laws to taxonomy nodes

- **Custom Patterns**
  - SearchEnhancedExplorationPattern: Combines knowledge-based and search-based exploration
  - ParallelExplorationPattern: Parallel processing of taxonomy branches
  - BreadthLimitedExploration: Controls taxonomy breadth to prevent explosive growth

- **Tools**
  - Knowledge Base Tools: Internal domain knowledge
  - Search Tools: SerAPI integration for web search
  - Compliance Tools: Regulatory requirement mapping
  - Legal Tools: Legal mapping tools
  
- **Tracing and Analysis**
  - LLMTracingPlugin: Symphony plugin for tracing model calls
  - TraceAnalyzer: Visualization and metrics for model performance

## Usage

### Using the Command Line Script

The easiest way to generate taxonomies is to use the provided command-line script:

```bash
# Generate a US compliance taxonomy for "Nudity"
./generate_us_taxonomies.sh "Nudity"

# Generate for other categories
./generate_us_taxonomies.sh "Alcohol"
./generate_us_taxonomies.sh "Weapons"

# Generate multiple taxonomies in one go
./generate_multiple.sh "Sports,Finance,Technology"

# Run full pipeline (generation, analysis, visualization)
./run_pipeline.sh "Sports,Finance,Technology"
```

### Custom Parameters with Python Script

For more control, you can use the Python script directly:

```bash
# Basic usage
python generate_taxonomy.py "Nudity"

# Custom parameters
python generate_taxonomy.py "Alcohol" \
    --jurisdictions "USA,EU,UK" \
    --output-dir "custom_output" \
    --storage-dir "custom_storage" \
    --max-depth 5 \
    --breadth-limit 15 \
    --strategy "breadth_first" \
    --planner-model "gpt-4o" \
    --explorer-model "gpt-4-turbo" \
    --compliance-model "gpt-4o" \
    --legal-model "gpt-4o"
```

### Programmatic Usage

```python
import asyncio
from applications.taxonomy_planner import generate_taxonomy

async def main():
    # Generate a taxonomy for "Technology" with default settings
    taxonomy = await generate_taxonomy(
        root_category="Technology",
        output_path="technology_taxonomy.json"
    )
    
    print(f"Generated taxonomy with {len(taxonomy['subcategories'])} top-level categories")

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Configuration

```python
import asyncio
from applications.taxonomy_planner import TaxonomyPlanner, TaxonomyConfig

async def main():
    # Create custom configuration
    config = TaxonomyConfig()
    config.max_depth = 4
    config.default_jurisdictions = ["USA", "EU", "Japan", "International"]
    
    # Customize search capabilities
    config.search_config["enable_search"] = True
    config.search_config["max_requests_per_minute"] = 30
    config.search_config["results_per_query"] = 5
    
    # Add domain-specific presets
    config.domain_presets["electronics"] = {
        "top_level_categories": [
            "Consumer Electronics", "Industrial Electronics", 
            "Telecommunications", "Components"
        ],
        "knowledge_sources": ["IEEE Database", "Electronics Standards"]
    }
    
    # Create planner with custom config
    planner = TaxonomyPlanner(config=config)
    await planner.setup()
    
    # Generate taxonomy
    taxonomy = await planner.generate_taxonomy(
        root_category="Electronics",
        jurisdictions=["USA", "EU", "Japan"],
        max_depth=3,
        output_path="electronics_taxonomy.json"
    )
    
    print(f"Generated taxonomy with {len(taxonomy['subcategories'])} top-level categories")

if __name__ == "__main__":
    asyncio.run(main())
```

## Output Structure

The generated taxonomy is a hierarchical JSON structure with the following format:

```json
{
  "category": "Root Category",
  "subcategories": [
    {
      "category": "Subcategory 1",
      "subcategories": [],
      "compliance": {
        "USA": ["Compliance Requirement 1", "Compliance Requirement 2"],
        "EU": ["EU Compliance Requirement 1"]
      },
      "legal": {
        "USA": [
          {"title": "US Law 1", "description": "Description of US Law 1"}
        ],
        "EU": [
          {"title": "EU Regulation 1", "description": "Description of EU Regulation 1"}
        ]
      }
    },
    {
      "category": "Subcategory 2",
      "subcategories": [
        {
          "category": "Sub-subcategory 1",
          "subcategories": [],
          "compliance": {...},
          "legal": {...}
        }
      ],
      "compliance": {...},
      "legal": {...}
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

## Using SerAPI Integration

The Taxonomy Planner can be enhanced with real web search capabilities using the SerAPI integration:

1. Sign up for a [SerAPI account](https://serpapi.com/) and get an API key
2. Set the API key in your environment:
   ```bash
   export SERAPI_API_KEY="your-api-key"
   ```
3. Enable search in your configuration:
   ```python
   config = TaxonomyConfig()
   config.search_config["enable_search"] = True
   ```

The provided `generate_us_taxonomies.sh` script already includes the API key for SerpAPI and OpenAI for convenience.

Without an API key, the application will use mock search results for demonstration purposes.

## Visualizing Taxonomies

The Taxonomy Planner includes visualization tools that create interactive HTML tree views:

```bash
# Visualize a single taxonomy
python visualize_taxonomy.py output/us_jurisdictions/sports_taxonomy.json

# Specify a custom output file
python visualize_taxonomy.py output/us_jurisdictions/sports_taxonomy.json --output custom_visualization.html

# Visualize all taxonomies in a directory
python visualize_all.py --input-dir output/us_jurisdictions

# Visualize taxonomies matching a pattern
python visualize_all.py --input-dir output --pattern "*_taxonomy.json"
```

The visualization provides:
- Interactive expandable/collapsible tree view
- Search functionality to find categories
- Compliance and legal information display
- Metadata summary
- Index page with links to all visualizations

## LLM Tracing and Analysis

The Taxonomy Planner includes a comprehensive tracing system to monitor and analyze LLM calls:

### Trace Generation

Tracing is automatically enabled when generating taxonomies:

```bash
# Generate taxonomy with tracing enabled (built-in)
./generate_us_taxonomies.sh "Sports"
```

This creates trace files in the `traces/taxonomy_generation/` directory with full request/response information.

### Analyzing Traces

Use the trace analysis tool to generate insights and visualizations:

```bash
# Analyze a trace file
python analyze_traces.py traces/taxonomy_generation/trace_*.jsonl

# Specify custom output directory
python analyze_traces.py traces/taxonomy_generation/trace_*.jsonl --output-dir "analysis/sports"
```

The analysis includes:
- Request/response statistics
- Response time distributions
- Model usage metrics
- Visualization of performance data

### Customizing Tracing

You can customize the tracing behavior in your code:

```python
from llm_tracing_plugin import LLMTracingPlugin

# Create a custom tracer
tracer = LLMTracingPlugin(trace_dir="custom_traces")

# Use the trace decorator
@tracer.trace_model_call
async def custom_model_call(model, prompt):
    # Your model call code here
    pass
```

## Example Applications

The Taxonomy Planner can be used for various applications:

- **Regulatory Compliance**: Generate comprehensive taxonomies of regulated items with applicable laws
- **Knowledge Management**: Create structured knowledge bases for specific domains
- **Content Organization**: Build content taxonomies for websites or documentation
- **Product Categorization**: Develop e-commerce product hierarchies
- **Legal Research**: Map legal requirements across different jurisdictions
- **Model Performance Analysis**: Analyze LLM performance across different models and tasks

## Extending the Application

You can extend the Taxonomy Planner in several ways:

1. **Add New Knowledge Sources**:
   - Extend the `knowledge_base.py` module with additional domain-specific knowledge

2. **Enhance Search Capabilities**:
   - Implement more sophisticated NLP for extracting information from search results
   - Add support for additional search APIs

3. **Create Custom Patterns**:
   - Develop specialized patterns for specific domain taxonomies

4. **Add Visualization**:
   - Implement visualization tools for the generated taxonomies

5. **Integrate with External Systems**:
   - Connect to databases or knowledge management systems
   - Integrate with commercial taxonomies or ontologies
   
6. **Extend Tracing Capabilities**:
   - Add support for additional metrics and visualizations
   - Integrate with monitoring systems for real-time insights
   
7. **Enhance Visualization Tools**:
   - Add interactive comparisons between taxonomies
   - Create dashboards for model performance metrics
   - Support exporting to other formats (PDF, SVG)