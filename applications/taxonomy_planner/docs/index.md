# Taxonomy Planner Documentation

Welcome to the Taxonomy Planner documentation! This guide will help you understand how to use and extend the Taxonomy Planner application.

## Contents

- [User Guide](user_guide.md) - Basic usage and configuration
- [Extending](extending.md) - How to extend the application with new features
- [Tracing](tracing.md) - LLM tracing and performance analysis

## Quick Start

The fastest way to get started is to generate a taxonomy for a specific category:

```bash
# Generate a taxonomy for "Sports"
./generate_us_taxonomies.sh "Sports"
```

This will create a detailed taxonomy with compliance and legal mappings for the US jurisdiction, saved to `output/us_jurisdictions/sports_taxonomy.json`.

## Key Features

- **Multi-agent generation**: Specialized agents for planning, exploration, compliance, and legal mapping
- **Efficient persistence**: Adjacency list-based storage for taxonomies
- **Configurable parameters**: Control depth, breadth, and exploration strategy
- **LLM tracing**: Monitor model performance and analyze results

## Understanding Taxonomies

Taxonomies are hierarchical classification systems that organize knowledge. The Taxonomy Planner creates comprehensive taxonomies with:

- Hierarchical relationships (parent-child)
- Compliance requirements for each category
- Legal information for each category
- Jurisdiction-specific information

The generated taxonomies can be used for regulatory compliance, content organization, product categorization, and more.

## Advanced Usage

For more advanced usage, see the [User Guide](user_guide.md), which covers:

- Custom configurations
- Different exploration strategies
- Multi-jurisdiction support
- Model selection
- Search integration

## Contributing

To extend the Taxonomy Planner with new features, see the [Extending](extending.md) guide, which covers:

- Adding new knowledge sources
- Creating custom exploration patterns
- Enhancing search capabilities
- Integrating with external systems