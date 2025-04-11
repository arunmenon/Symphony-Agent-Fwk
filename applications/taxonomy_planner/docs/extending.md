# Extending the Taxonomy Planner

This guide provides detailed instructions for extending the Taxonomy Planner application in various ways, with practical code examples and best practices.

## Table of Contents
- [Adding New Enhanced Fields](#adding-new-enhanced-fields)
- [Creating Custom Agents](#creating-custom-agents)
- [Implementing New Search Capabilities](#implementing-new-search-capabilities)
- [Customizing Exploration Patterns](#customizing-exploration-patterns)
- [Adding New Jurisdictions](#adding-new-jurisdictions)
- [Implementing Custom Output Formats](#implementing-custom-output-formats)
- [Advanced Symphony Integration](#advanced-symphony-integration)

## Adding New Enhanced Fields

The enhanced taxonomy structure supports additional metadata fields beyond the basic hierarchy. Here's how to add new fields:

### 1. Update the Enhanced Fields Constant

In `generate_taxonomy.py`, locate and modify the `ENHANCED_FIELDS` constant:

```python
# Enhanced fields for improved taxonomy data structure
ENHANCED_FIELDS = [
    "description",           # Detailed description of the category
    "enforcement_examples",  # Examples of enforcement or incidents
    "social_media_trends",   # Current trends in social media related to the category
    "risk_level",            # Risk assessment (High, Medium, Low)
    "detection_methods",     # Methods for detecting instances of this category
    "regulatory_bodies",     # NEW: Organizations that regulate this category
    "compliance_costs"       # NEW: Cost implications for compliance
]
```

### 2. Update Agent Instructions

Update the agent instructions to include guidance for the new fields:

```python
planning_agent_builder.create(
    name="TaxonomyPlanner",
    role="Planning comprehensive taxonomies",
    instruction_template=(
        f"Develop a hierarchical taxonomy plan for the domain: {category}. "
        f"Include categories, subcategories, and plan for enhanced fields: "
        f"{', '.join(enhanced_fields)}. "
        f"For regulatory_bodies, include government agencies and industry organizations that regulate this area. "
        f"For compliance_costs, estimate relative cost levels (Low, Medium, High) with brief justification. "
        f"Consider the following jurisdictions: {', '.join(jurisdictions)}."
    )
)
```

### 3. Update Sample Data Generation

In the taxonomy generation functions, update how sample data is generated:

```python
# Add to structured taxonomy
taxonomy["subcategories"].append({
    "name": subcat,
    "description": f"Description of {subcat}",
    "enforcement_examples": [f"Example 1 for {subcat}", f"Example 2 for {subcat}"],
    "social_media_trends": [f"Trend 1 for {subcat}", f"Trend 2 for {subcat}"],
    "risk_level": "Medium",
    "detection_methods": [f"Method 1 for {subcat}", f"Method 2 for {subcat}"],
    "regulatory_bodies": [f"Regulator 1 for {subcat}", f"Regulator 2 for {subcat}"],
    "compliance_costs": "Medium with significant ongoing reporting requirements",
    "subcategories": []
})
```

### 4. Test the New Fields

Create test cases for the new fields:

```python
def test_enhanced_fields_present():
    """Test that all enhanced fields are present in the taxonomy."""
    store = TaxonomyStore("test_store.json")
    store.add_node("Test Category", metadata={
        "description": "Test description",
        "enforcement_examples": ["Example 1", "Example 2"],
        "social_media_trends": ["Trend 1", "Trend 2"],
        "risk_level": "Medium",
        "detection_methods": ["Method 1", "Method 2"],
        "regulatory_bodies": ["Regulator 1", "Regulator 2"],
        "compliance_costs": "Medium"
    })
    
    taxonomy = store.get_taxonomy_tree("Test Category")
    
    # Verify all fields exist
    for field in ENHANCED_FIELDS:
        assert field in taxonomy, f"Field {field} missing from taxonomy"
```

## Creating Custom Agents

You can extend the Taxonomy Planner with specialized agents for specific domains or tasks.

### 1. Define a New Agent Type

In a suitable location (e.g., `agents.py` or a new file), define your specialized agent:

```python
async def create_financial_analysis_agent(symphony, category: str, enhanced_fields: List[str]):
    """Create a specialized agent for financial analysis."""
    
    # Create agent using Symphony builder pattern
    financial_agent_builder = symphony.build_agent()
    financial_agent_builder.create(
        name="FinancialAnalysisAgent",
        role="Financial compliance cost analysis expert",
        instruction_template=(
            f"Analyze the financial compliance implications for {category}. "
            f"Estimate compliance costs, ongoing reporting expenses, and technology requirements. "
            f"Provide detailed cost breakdowns and regulatory fee structures where applicable. "
            f"Focus especially on fields: {', '.join(['compliance_costs', 'regulatory_bodies'])}."
        )
    )
    
    # Build and save the agent
    financial_agent = financial_agent_builder.build()
    financial_agent_id = await symphony.agents.save_agent(financial_agent)
    
    return {
        "agent": financial_agent,
        "id": financial_agent_id
    }
```

### 2. Create a Task for the Agent

```python
async def create_financial_analysis_task(symphony, category: str):
    """Create a task for financial analysis."""
    
    task_builder = symphony.build_task()
    task = task_builder.create(
        name="FinancialAnalysis",
        description=f"Analyze financial compliance implications for {category}"
    ).with_query(
        "Analyze the financial compliance implications for the taxonomy below. "
        "Provide detailed cost estimates and regulatory fee structures where applicable. "
        "Taxonomy: {{enhanced_taxonomy}}"
    ).build()
    
    task_id = await symphony.tasks.save_task(task)
    return task_id
```

### 3. Add the Agent to the Workflow

```python
# Create the financial analysis agent and task
financial_agent_data = await create_financial_analysis_agent(symphony, category, enhanced_fields)
financial_task_id = await create_financial_analysis_task(symphony, category)

# Add financial analysis step to workflow
financial_step = (workflow_builder.build_step()
    .name("FinancialAnalysis")
    .description("Analyze financial compliance implications")
    .agent(financial_agent_data["agent"])
    .task({"id": financial_task_id})
    .depends_on("ExpandTaxonomy")  # This step should run after taxonomy expansion
    .output_key("financial_analysis")
    .build()
)

workflow_builder.add_step(financial_step)
```

### 4. Process the Agent's Output

```python
# Extract financial analysis from workflow results
context = result.metadata.get("context", {})
financial_analysis = context.get("financial_analysis", "")

# Add financial analysis to taxonomy output
final_taxonomy = {
    "raw_agent_output": enhanced_taxonomy_text,
    "financial_analysis": financial_analysis,
    "structured_taxonomy": taxonomy
}
```

## Implementing New Search Capabilities

Extend the search capabilities to include domain-specific knowledge sources.

### 1. Add a New Search Method in `search_tools.py`

```python
def search_regulatory_database(category: str, jurisdiction: str, config: TaxonomyConfig = None) -> Dict[str, Any]:
    """Search regulatory databases for information about a category.
    
    Args:
        category: The category to search for
        jurisdiction: The jurisdiction to search within
        config: Taxonomy configuration
        
    Returns:
        Regulatory information from databases
    """
    logger.debug(f"search_regulatory_database called for '{category}' in '{jurisdiction}'")
    
    if not config or not config.search_config.get("enable_search", True):
        logger.warning(f"search_regulatory_database: Search disabled for '{category}'")
        return {"category": category, "results": [], "error": "Search disabled"}
    
    # Construct API endpoint for regulatory database (example)
    api_key = config.search_config.get("regulatory_api_key", "")
    if not api_key:
        logger.warning(f"search_regulatory_database: No regulatory API key configured")
        return {"category": category, "results": [], "error": "No API key"}
    
    # Implement the actual search logic here
    # This could be a REST API call, database query, etc.
    # Example:
    endpoint = f"https://api.regulatorydb.example/search?q={category}&jurisdiction={jurisdiction}&key={api_key}"
    
    try:
        # Make HTTP request (using requests, aiohttp, or similar)
        # response = requests.get(endpoint)
        # data = response.json()
        
        # For demonstration, return simulated data
        data = {
            "regulations": [
                {"id": "REG123", "title": f"{category} Regulation Act", "year": 2022},
                {"id": "REG456", "title": f"{jurisdiction} {category} Standards", "year": 2021}
            ],
            "regulatory_bodies": [
                {"name": f"{jurisdiction} {category} Authority", "website": "https://example.com"},
                {"name": "International {category} Commission", "website": "https://example.org"}
            ]
        }
        
        return {
            "category": category,
            "jurisdiction": jurisdiction,
            "results": data
        }
        
    except Exception as e:
        logger.error(f"Error searching regulatory database: {e}")
        return {"category": category, "results": [], "error": str(e)}
```

### 2. Add Configuration Options

Update `TaxonomyConfig` to support the new search capabilities:

```python
# In config.py
def __init__(self):
    """Initialize taxonomy configuration."""
    # ... existing code ...
    
    # Add regulatory database search configuration
    self.search_config.update({
        "enable_regulatory_search": True,
        "regulatory_api_key": os.environ.get("REGULATORY_API_KEY", ""),
        "regulatory_search_depth": 2
    })
```

### 3. Integrate the New Search in the Exploration Pattern

```python
# In patterns.py or a suitable location
async def enhanced_exploration_with_regulatory_search(category: str, jurisdiction: str, config: TaxonomyConfig):
    """Enhanced exploration that includes regulatory database search."""
    # Standard subcategory search
    subcategories = search_subcategories(category, config)
    
    # Add regulatory search if enabled
    if config.search_config.get("enable_regulatory_search", False):
        regulatory_data = search_regulatory_database(category, jurisdiction, config)
        
        # Extract additional subcategories or metadata from regulatory data
        if regulatory_data and "results" in regulatory_data:
            # Process regulatory data to enhance the taxonomy
            regulations = regulatory_data.get("results", {}).get("regulations", [])
            for reg in regulations:
                # Add relevant information to the results
                # This could be new subcategories, metadata, etc.
                if "title" in reg:
                    # Extract potential subcategory from regulation title
                    potential_subcategory = extract_subcategory_from_title(reg["title"], category)
                    if potential_subcategory and potential_subcategory not in subcategories:
                        subcategories.append(potential_subcategory)
    
    return subcategories
```

## Customizing Exploration Patterns

Create specialized exploration patterns for different taxonomy domains.

### 1. Create a New Pattern Class

```python
# In patterns.py or a new file
from symphony.patterns.base import BasePattern

class DomainSpecificExplorationPattern(BasePattern):
    """A specialized exploration pattern for a specific domain."""
    
    def __init__(self, domain: str, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.domain = domain
        self.max_depth = config.get("max_depth", 3)
        self.breadth_limit = config.get("breadth_limit", 10)
        
    async def apply(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the pattern to the given context."""
        category = context.get("category", "")
        if not category:
            return context
            
        logger.info(f"Applying domain-specific exploration for {category} in {self.domain}")
        
        # Domain-specific processing logic
        if self.domain == "Financial":
            # Financial domain specialization
            context = await self._process_financial_domain(context)
        elif self.domain == "Healthcare":
            # Healthcare domain specialization
            context = await self._process_healthcare_domain(context)
        else:
            # Generic domain processing
            context = await self._process_generic_domain(context)
            
        return context
    
    async def _process_financial_domain(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process context for financial domain."""
        # Domain-specific implementation
        category = context.get("category", "")
        
        # Get financial regulations
        financial_regs = await self._get_financial_regulations(category)
        context["domain_regulations"] = financial_regs
        
        # Financial-specific subcategory organization
        # ...
        
        return context
    
    async def _process_healthcare_domain(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process context for healthcare domain."""
        # Healthcare-specific implementation
        # ...
        return context
    
    async def _process_generic_domain(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process context for other domains."""
        # Generic implementation
        # ...
        return context
        
    async def _get_financial_regulations(self, category: str) -> List[Dict[str, Any]]:
        """Get financial regulations for a category."""
        # Implementation details
        # ...
        return [
            {"id": "REG1", "name": f"Financial {category} Regulation"},
            {"id": "REG2", "name": f"International {category} Standard"}
        ]
```

### 2. Integrate the Pattern with Symphony

```python
# In main.py or where you configure Symphony
async def setup_domain_specific_workflow(symphony, category: str, domain: str, config: TaxonomyConfig):
    """Set up a domain-specific workflow."""
    
    # Create pattern instance
    pattern_config = {
        "max_depth": config.max_depth,
        "breadth_limit": config.breadth_limit,
        "domain_specific_params": {
            "financial": {
                "include_international_standards": True
            },
            "healthcare": {
                "include_clinical_guidelines": True
            }
        }
    }
    
    domain_pattern = DomainSpecificExplorationPattern(domain, pattern_config)
    
    # Register pattern with Symphony (if needed)
    pattern_registry = symphony.get_component("pattern_registry")
    if pattern_registry:
        pattern_registry.register_pattern(f"{domain.lower()}_exploration", domain_pattern)
    
    # Create agent with pattern
    explorer_agent_builder = symphony.build_agent()
    explorer_agent_builder.create(
        name=f"{domain}ExplorerAgent",
        role=f"Specialized {domain} domain explorer",
        instruction_template=(
            f"Explore the given taxonomy category with {domain}-specific expertise: {{{{category}}}}. "
            f"Consider domain-specific regulations, standards, and best practices."
        )
    ).with_pattern(domain_pattern)  # Apply the pattern to the agent
    
    explorer_agent = explorer_agent_builder.build()
    explorer_agent_id = await symphony.agents.save_agent(explorer_agent)
    
    # Continue with workflow setup as usual
    # ...
    
    return explorer_agent
```

## Adding New Jurisdictions

Extend the system to support additional jurisdictions for compliance mapping.

### 1. Update Jurisdiction Handling

```python
# In config.py or a suitable location
SUPPORTED_JURISDICTIONS = {
    "USA": {
        "name": "United States",
        "code": "US",
        "supported_domains": ["Alcohol", "Weapons", "Pharmaceuticals", "Gambling"],
        "regulatory_bodies": ["FDA", "ATF", "DEA"]
    },
    "EU": {
        "name": "European Union",
        "code": "EU",
        "supported_domains": ["Alcohol", "Weapons", "Pharmaceuticals", "Gambling"],
        "regulatory_bodies": ["EMA", "EFSA"]
    },
    "UK": {  # New jurisdiction
        "name": "United Kingdom",
        "code": "GB",
        "supported_domains": ["Alcohol", "Weapons", "Pharmaceuticals", "Gambling"],
        "regulatory_bodies": ["MHRA", "FSA", "Gambling Commission"]
    },
    "CA": {  # New jurisdiction
        "name": "Canada",
        "code": "CA",
        "supported_domains": ["Alcohol", "Weapons", "Pharmaceuticals", "Gambling"],
        "regulatory_bodies": ["Health Canada", "RCMP"]
    }
}

def get_jurisdiction_metadata(jurisdiction_code: str) -> Dict[str, Any]:
    """Get metadata for a specific jurisdiction."""
    return SUPPORTED_JURISDICTIONS.get(jurisdiction_code, {})
```

### 2. Update CLI to Support New Jurisdictions

```python
# In generate_taxonomy.py or relevant CLI file
parser.add_argument(
    "--jurisdictions",
    help="Comma-separated list of jurisdictions (supported: USA,EU,UK,CA)",
    default="USA"
)
```

### 3. Add Jurisdiction-Specific Processing

```python
async def process_jurisdiction_specific_requirements(category: str, jurisdiction: str, config: TaxonomyConfig):
    """Process jurisdiction-specific requirements for a category."""
    
    jurisdiction_metadata = get_jurisdiction_metadata(jurisdiction)
    if not jurisdiction_metadata:
        logger.warning(f"Jurisdiction {jurisdiction} not recognized, using generic processing")
        return generic_jurisdiction_processing(category)
    
    # Check if this domain is supported for the jurisdiction
    if category not in jurisdiction_metadata.get("supported_domains", []):
        logger.warning(f"Domain {category} not specifically supported for {jurisdiction}")
    
    # Get regulatory bodies for this jurisdiction
    regulatory_bodies = jurisdiction_metadata.get("regulatory_bodies", [])
    
    # Jurisdiction-specific processing
    if jurisdiction == "USA":
        return process_usa_requirements(category, regulatory_bodies)
    elif jurisdiction == "EU":
        return process_eu_requirements(category, regulatory_bodies)
    elif jurisdiction == "UK":
        return process_uk_requirements(category, regulatory_bodies)
    elif jurisdiction == "CA":
        return process_canada_requirements(category, regulatory_bodies)
    else:
        return generic_jurisdiction_processing(category)
```

## Implementing Custom Output Formats

Add support for different output formats beyond JSON.

### 1. Create Format Converter Interface

```python
# In a new file, e.g., formats.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class TaxonomyFormatter(ABC):
    """Base class for taxonomy formatters."""
    
    @abstractmethod
    def format(self, taxonomy: Dict[str, Any]) -> str:
        """Convert taxonomy to the target format."""
        pass
        
    @abstractmethod
    def get_file_extension(self) -> str:
        """Get the file extension for this format."""
        pass

class JSONFormatter(TaxonomyFormatter):
    """Format taxonomy as JSON."""
    
    def __init__(self, indent: int = 2):
        self.indent = indent
    
    def format(self, taxonomy: Dict[str, Any]) -> str:
        """Convert taxonomy to JSON."""
        import json
        return json.dumps(taxonomy, indent=self.indent, cls=DateTimeEncoder)
    
    def get_file_extension(self) -> str:
        """Get the file extension for JSON."""
        return "json"

class XMLFormatter(TaxonomyFormatter):
    """Format taxonomy as XML."""
    
    def format(self, taxonomy: Dict[str, Any]) -> str:
        """Convert taxonomy to XML."""
        import xml.etree.ElementTree as ET
        from xml.dom import minidom
        
        def _dict_to_xml(parent_elem, data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        sub_elem = ET.SubElement(parent_elem, key)
                        _dict_to_xml(sub_elem, value)
                    else:
                        sub_elem = ET.SubElement(parent_elem, key)
                        sub_elem.text = str(value)
            elif isinstance(data, list):
                for item in data:
                    _dict_to_xml(parent_elem, item)
            else:
                parent_elem.text = str(data)
        
        root = ET.Element("Taxonomy")
        _dict_to_xml(root, taxonomy)
        
        # Convert to pretty-printed XML
        xml_str = ET.tostring(root, encoding='utf-8')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")
    
    def get_file_extension(self) -> str:
        """Get the file extension for XML."""
        return "xml"

class CSVFormatter(TaxonomyFormatter):
    """Format taxonomy as CSV (flattened)."""
    
    def format(self, taxonomy: Dict[str, Any]) -> str:
        """Convert taxonomy to CSV."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["Category", "Parent", "Level", "Description", "Risk Level"])
        
        # Flatten and write taxonomy
        self._write_category(writer, taxonomy, "", 0)
        
        return output.getvalue()
    
    def _write_category(self, writer, category, parent, level):
        """Write a category and its subcategories to CSV."""
        name = category.get("name", "")
        description = category.get("description", "")
        risk_level = category.get("risk_level", "")
        
        writer.writerow([name, parent, level, description, risk_level])
        
        # Process subcategories
        for subcategory in category.get("subcategories", []):
            self._write_category(writer, subcategory, name, level + 1)
    
    def get_file_extension(self) -> str:
        """Get the file extension for CSV."""
        return "csv"
```

### 2. Add Format Selection to CLI

```python
# In generate_taxonomy.py
parser.add_argument(
    "--format",
    help="Output format (json, xml, csv)",
    choices=["json", "xml", "csv"],
    default="json"
)
```

### 3. Implement Format Selection Logic

```python
# In generate_taxonomy.py or main function
def get_formatter(format_name: str) -> TaxonomyFormatter:
    """Get the appropriate formatter based on format name."""
    if format_name == "xml":
        return XMLFormatter()
    elif format_name == "csv":
        return CSVFormatter()
    else:  # Default to JSON
        return JSONFormatter()

# In the main function where you save output
formatter = get_formatter(args.format)
output_path = os.path.join(args.output_dir, f"{category.lower().replace(' ', '_')}_taxonomy.{formatter.get_file_extension()}")

# Format and save the taxonomy
formatted_output = formatter.format(taxonomy)
with open(output_path, 'w') as f:
    f.write(formatted_output)
```

## Advanced Symphony Integration

Implement advanced Symphony features for more sophisticated workflows.

### 1. Implement Multi-Agent Collaboration Pattern

```python
from symphony.patterns.multi_agent.expert_panel import ExpertPanelPattern

async def setup_expert_panel_workflow(symphony, category: str, domain: str, config: TaxonomyConfig):
    """Set up an expert panel workflow for domain expertise."""
    
    # Create multiple expert agents
    legal_expert = await create_expert_agent(symphony, "Legal", category, domain)
    regulatory_expert = await create_expert_agent(symphony, "Regulatory", category, domain)
    industry_expert = await create_expert_agent(symphony, "Industry", category, domain)
    
    # Create expert panel pattern
    expert_panel = ExpertPanelPattern(
        experts=[legal_expert, regulatory_expert, industry_expert],
        config={
            "voting_method": "consensus",  # Other options: majority, weighted
            "max_rounds": 3,
            "aggregation_strategy": "hierarchical"
        }
    )
    
    # Create moderator agent with expert panel pattern
    moderator_agent_builder = symphony.build_agent()
    moderator_agent_builder.create(
        name="ExpertPanelModerator",
        role="Moderator for expert panel taxonomy discussion",
        instruction_template=(
            f"Moderate an expert panel discussion on {category} taxonomy in {domain}. "
            f"Synthesize insights from legal, regulatory, and industry experts."
        )
    ).with_pattern(expert_panel)
    
    moderator_agent = moderator_agent_builder.build()
    moderator_agent_id = await symphony.agents.save_agent(moderator_agent)
    
    # Create task and workflow steps
    # ...
    
    return moderator_agent
```

### 2. Implement State Management for Long-Running Workflows

```python
from symphony.core.state.checkpoint import CheckpointManager

async def setup_checkpointed_workflow(symphony, category: str, config: TaxonomyConfig):
    """Set up a workflow with checkpointing for long-running operations."""
    
    # Create and configure the CheckpointManager
    checkpoint_manager = CheckpointManager(
        storage_dir=os.path.join(config.storage_dir, ".symphony", "checkpoints"),
        checkpoint_interval=5 * 60,  # Checkpoint every 5 minutes
        max_checkpoints=5  # Keep 5 most recent checkpoints
    )
    
    # Register the checkpoint manager with Symphony
    symphony.register_component("checkpoint_manager", checkpoint_manager)
    
    # Create workflow with checkpointing
    workflow_builder = symphony.build_workflow()
    workflow_builder.create(
        name=f"CheckpointedTaxonomyGeneration_{category}",
        description=f"Generate taxonomy for {category} with checkpointing"
    ).with_checkpoint_manager(checkpoint_manager)
    
    # Create steps, agents, and tasks as usual
    # ...
    
    # Build workflow
    workflow = workflow_builder.build()
    
    # Execute with checkpoint restoration if available
    checkpoint_id = config.get("restore_checkpoint_id")
    if checkpoint_id:
        result = await symphony.workflows.execute_workflow(
            workflow=workflow,
            initial_context={"category": category},
            restore_from_checkpoint=checkpoint_id
        )
    else:
        result = await symphony.workflows.execute_workflow(
            workflow=workflow,
            initial_context={"category": category}
        )
    
    return result
```

### 3. Implement Custom Symphony Plugins

```python
from symphony.core.plugin import SymphonyPlugin

class TaxonomyMetricsPlugin(SymphonyPlugin):
    """Plugin for collecting and analyzing taxonomy generation metrics."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.metrics = {
            "taxonomies_generated": 0,
            "categories_processed": 0,
            "agent_execution_times": {},
            "total_tokens_used": 0,
            "errors_encountered": 0
        }
        
    def on_workflow_start(self, workflow_id: str, context: Dict[str, Any]):
        """Handler for workflow start event."""
        self.metrics["taxonomies_generated"] += 1
        
    def on_step_complete(self, step_id: str, result: Dict[str, Any]):
        """Handler for step completion event."""
        step_name = result.get("step_name", "unknown")
        execution_time = result.get("execution_time", 0)
        tokens_used = result.get("tokens_used", 0)
        
        self.metrics["categories_processed"] += len(result.get("categories_processed", []))
        self.metrics["total_tokens_used"] += tokens_used
        
        # Track agent execution times
        if step_name not in self.metrics["agent_execution_times"]:
            self.metrics["agent_execution_times"][step_name] = []
        self.metrics["agent_execution_times"][step_name].append(execution_time)
        
    def on_error(self, error: Exception, context: Dict[str, Any]):
        """Handler for error events."""
        self.metrics["errors_encountered"] += 1
        
    def on_workflow_complete(self, workflow_id: str, result: Dict[str, Any]):
        """Handler for workflow completion event."""
        # Generate summary report
        summary = self.generate_metrics_summary()
        
        # Save metrics
        output_dir = self.config.get("metrics_dir", "metrics")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f"taxonomy_metrics_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
        with open(output_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
            
    def generate_metrics_summary(self) -> Dict[str, Any]:
        """Generate a summary of collected metrics."""
        summary = {
            "taxonomies_generated": self.metrics["taxonomies_generated"],
            "categories_processed": self.metrics["categories_processed"],
            "average_tokens_per_taxonomy": self.metrics["total_tokens_used"] / max(1, self.metrics["taxonomies_generated"]),
            "error_rate": self.metrics["errors_encountered"] / max(1, self.metrics["taxonomies_generated"]),
            "average_execution_times": {}
        }
        
        # Calculate average execution times
        for step, times in self.metrics["agent_execution_times"].items():
            if times:
                summary["average_execution_times"][step] = sum(times) / len(times)
        
        return summary
```

## Conclusion

This extension guide demonstrates the flexibility and extensibility of the Taxonomy Planner. By following these patterns, you can customize the system for specific domains, add new functionality, and integrate with other systems.

Remember to:
- Maintain the core workflow architecture when extending
- Follow Symphony's agent execution pattern for compatibility
- Add comprehensive tests for new functionality
- Document your extensions thoroughly

For more information on Symphony integration, refer to the [Symphony API documentation](https://docs.symphony.example/api).