# Compliance Taxonomy Planner

A Symphony-powered application for automated generation of regulatory compliance taxonomies with legal mapping capabilities.

## Overview

The Compliance Taxonomy Planner is a Symphony application that generates structured taxonomies for regulatory compliance domains. It maps compliance requirements and applicable laws across jurisdictions, enabling organizations to efficiently navigate complex regulatory landscapes.

Key features include:
- Multi-agent compliance taxonomy generation with specialized legal mapping
- Regulatory requirement mapping across jurisdictions
- Applicable law identification and classification
- Search enhancement for up-to-date regulatory information
- Configurable taxonomy parameters for different compliance domains

## Architecture

The application uses a specialized multi-agent architecture:

- **Planner Agent**: Coordinates the overall taxonomy structure based on regulatory domains
- **Explorer Agent**: Explores subcategories with focus on compliance-relevant areas
- **Compliance Agent**: Maps specific regulatory requirements to taxonomy nodes
- **Legal Agent**: Maps applicable laws and regulations across jurisdictions

## Usage

### Quick Start (Recommended)

The simplest way to generate compliance taxonomies is using the command line script:

```bash
# Before running, set your API keys as environment variables:
export OPENAI_API_KEY="your-openai-api-key"
export SERAPI_API_KEY="your-serapi-api-key"  # Optional for enhanced search

# Generate a US compliance taxonomy for regulated items
./generate_us_taxonomies.sh "Alcohol"

# Other common regulatory domains
./generate_us_taxonomies.sh "Weapons"
./generate_us_taxonomies.sh "Pharmaceuticals"
./generate_us_taxonomies.sh "Gambling"
```

The script will:
1. Generate a comprehensive taxonomy for the specified domain
2. Map US regulatory requirements to each category
3. Identify applicable laws at federal and state levels
4. Save results to `output/us_jurisdictions/{domain}_taxonomy.json`

### Advanced Usage

For more control, use the Python script directly:

```bash
# Custom jurisdictions and parameters
python generate_taxonomy.py "Alcohol" \
    --jurisdictions "USA,EU,UK" \
    --output-dir "custom_output" \
    --max-depth 4 \
    --breadth-limit 10
```

### Visualizing Results

View the generated taxonomies in an interactive format:

```bash
# Visualize a specific taxonomy
python visualize_taxonomy.py output/us_jurisdictions/alcohol_taxonomy.json

# Visualize all taxonomies in a directory
python visualize_all.py --input-dir output/us_jurisdictions
```

## Output Structure

The generated compliance taxonomy follows this structure:

```json
{
  "category": "Alcohol",
  "subcategories": [
    {
      "category": "Distilled Spirits",
      "subcategories": [...],
      "compliance": {
        "USA": [
          "ATF permit required for production",
          "Age verification requirements for sales (21+)"
        ]
      },
      "legal": {
        "USA": [
          {
            "title": "Federal Alcohol Administration Act",
            "description": "Regulates the production and distribution of alcohol"
          },
          {
            "title": "State-specific regulations",
            "description": "Additional requirements vary by state"
          }
        ]
      }
    }
  ],
  "metadata": {
    "generated_at": "2025-04-08T14:30:00.000000",
    "jurisdictions": ["USA"]
  }
}
```

## API Requirements

This application requires:

1. **OpenAI API Key**: For the AI models that power the taxonomy generation
   - Set as environment variable: `export OPENAI_API_KEY="your-key"`
   - Models used: o1-mini for planning, gpt-4o-mini for exploration and mapping

2. **SerpAPI Key** (Optional): For enhanced search capabilities
   - Set as environment variable: `export SERAPI_API_KEY="your-key"`
   - Without this key, the system will use internal knowledge only

The script will automatically use environment variables if available.

## Example Applications

The Compliance Taxonomy Planner is ideal for:

- **Regulatory Compliance Teams**: Map applicable regulations to business activities
- **Legal Research**: Identify laws across jurisdictions for specific domains
- **Risk Management**: Structure compliance requirements for risk assessment
- **Training & Documentation**: Create structured compliance training materials
- **Product Classification**: Determine regulatory categories for new products

## Performance Metrics

For performance analysis of the taxonomy generation process:

```bash
# Analyze trace files from previous runs
python analyze_traces.py traces/taxonomy_generation/trace_*.jsonl
```

This generates charts and metrics showing model performance, response times, and token usage across different regulatory domains.