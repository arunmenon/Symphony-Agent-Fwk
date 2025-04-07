# Extending the Taxonomy Planner

This guide provides instructions for extending the Taxonomy Planner with custom tools, patterns, and knowledge sources.

## Adding Custom Tools

You can add custom tools to enhance the Taxonomy Planner's capabilities. Here's how:

### 1. Create a New Tool Module

Create a new Python module in the `tools` directory:

```python
# tools/custom_tool.py
from typing import List, Dict, Any, Optional

def custom_taxonomy_tool(category: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Example custom tool for taxonomy generation.
    
    Args:
        category: Category name
        parameters: Tool parameters
        
    Returns:
        Tool results
    """
    # Implement your custom tool logic here
    return {
        "category": category,
        "results": [
            {"name": "Custom Result 1", "relevance": 0.9},
            {"name": "Custom Result 2", "relevance": 0.8}
        ]
    }
```

### 2. Register the Tool in `__init__.py`

Update the `register_tools` function in `tools/__init__.py`:

```python
from .custom_tool import custom_taxonomy_tool

def register_tools(symphony: Symphony, config: TaxonomyConfig) -> None:
    """Register custom tools with Symphony."""
    # Existing tool registrations...
    
    # Register your custom tool
    symphony.register_tool("custom_taxonomy_tool", 
                          lambda category, **params: custom_taxonomy_tool(
                              category, params, config=config))
```

### 3. Use the Tool in Patterns

Update patterns to use your custom tool:

```python
# In patterns.py
async def execute(self, context: Dict[str, Any]) -> Any:
    # Existing code...
    
    # Use your custom tool
    custom_result = await agent.execute(
        f"Apply custom analysis to {category}",
        use_tools=["custom_taxonomy_tool"]
    )
    
    # Process results
    # ...
```

## Creating Custom Patterns

You can create custom patterns to implement specialized exploration strategies:

### 1. Create a New Pattern Class

```python
class CustomExplorationPattern(Pattern):
    """Pattern for custom taxonomy exploration."""
    
    @property
    def name(self) -> str:
        return "custom_exploration"
    
    @property
    def description(self) -> str:
        return "Explores taxonomy using a custom strategy"
    
    async def execute(self, context: Dict[str, Any]) -> Any:
        # Get parameters from context
        category = context.get("category")
        agent = context.get("agent")
        tools = context.get("tools", [])
        
        # Implement your custom pattern logic
        # ...
        
        return {
            "category": category,
            "results": custom_results
        }
```

### 2. Register the Pattern

Add your pattern to the `create_patterns` function:

```python
def create_patterns() -> Dict[str, Pattern]:
    """Create patterns for taxonomy generation."""
    patterns = {
        # Existing patterns...
        "custom_exploration": CustomExplorationPattern(),
    }
    
    return patterns
```

## Enhancing Knowledge Sources

You can add custom knowledge sources to improve taxonomy generation:

### 1. Extend the Knowledge Base

Update the `KNOWLEDGE_BASE` in `knowledge_base.py`:

```python
# In knowledge_base.py
KNOWLEDGE_BASE = {
    # Existing categories...
    
    "CustomDomain": ["Category1", "Category2", "Category3"],
    "Category1": ["Subcategory1", "Subcategory2"],
}
```

### 2. Add Domain-Specific Presets

Update the `domain_presets` in `config.py`:

```python
# In config.py
domain_presets: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
    # Existing presets...
    
    "custom_domain": {
        "top_level_categories": [
            "Category1", "Category2", "Category3"
        ],
        "knowledge_sources": ["Custom Database", "Domain-Specific References"]
    }
})
```

## Integrating External Services

To integrate with external services or APIs:

### 1. Create a Service Client

```python
# tools/external_service.py
import requests
from typing import Dict, Any

class ExternalServiceClient:
    """Client for external taxonomy service."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.example.com"):
        """Initialize client.
        
        Args:
            api_key: API key for service
            base_url: Base URL for API
        """
        self.api_key = api_key
        self.base_url = base_url
        
    def get_taxonomy_data(self, category: str) -> Dict[str, Any]:
        """Get taxonomy data from external service.
        
        Args:
            category: Category to query
            
        Returns:
            Taxonomy data
        """
        url = f"{self.base_url}/taxonomy"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"category": category}
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()
```

### 2. Create a Tool Using the Client

```python
from .external_service import ExternalServiceClient

def external_taxonomy_tool(category: str, config: TaxonomyConfig) -> Dict[str, Any]:
    """Get taxonomy data from external service.
    
    Args:
        category: Category name
        config: Taxonomy configuration
        
    Returns:
        External taxonomy data
    """
    api_key = config.external_service.get("api_key", "")
    if not api_key:
        return {"category": category, "error": "API key not configured"}
    
    client = ExternalServiceClient(api_key)
    
    try:
        return client.get_taxonomy_data(category)
    except Exception as e:
        return {"category": category, "error": str(e)}
```

### 3. Update Configuration

Add the external service configuration to `TaxonomyConfig`:

```python
# In config.py
@dataclass
class TaxonomyConfig:
    # Existing fields...
    
    # External service configuration
    external_service: Dict[str, Any] = field(default_factory=lambda: {
        "enable": False,
        "api_key": os.environ.get("EXTERNAL_SERVICE_API_KEY", ""),
        "base_url": "https://api.example.com"
    })
```

## Performance Optimization

To optimize performance for large taxonomies:

### 1. Implement Parallel Processing

```python
import asyncio
from typing import List, Dict, Any

async def process_categories_in_parallel(
    categories: List[str],
    agent: Any,
    tool: str,
    max_concurrency: int = 5
) -> List[Dict[str, Any]]:
    """Process categories in parallel.
    
    Args:
        categories: List of categories to process
        agent: Agent to use
        tool: Tool to use
        max_concurrency: Maximum concurrent tasks
        
    Returns:
        List of results
    """
    # Process categories in batches to limit concurrency
    results = []
    for i in range(0, len(categories), max_concurrency):
        batch = categories[i:i+max_concurrency]
        tasks = [
            agent.execute(f"Process category {category}", use_tools=[tool])
            for category in batch
        ]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
    
    return results
```

### 2. Use it in Your Patterns

```python
# In a pattern's execute method
subcategories = ["Category1", "Category2", "Category3", ...]
results = await process_categories_in_parallel(
    subcategories, 
    agent, 
    "search_category_info",
    max_concurrency=3
)
```

## Adding Visualization

To add visualization capabilities:

### 1. Create a Visualization Module

```python
# visualization.py
import json
import os
from typing import Dict, Any

def generate_html_visualization(taxonomy: Dict[str, Any], output_path: str) -> str:
    """Generate HTML visualization of taxonomy.
    
    Args:
        taxonomy: Taxonomy data
        output_path: Output file path
        
    Returns:
        Path to HTML file
    """
    # Create HTML representation of taxonomy
    html = "<html><head><title>Taxonomy Visualization</title></head><body>"
    html += "<h1>Taxonomy: " + taxonomy["category"] + "</h1>"
    
    # Add visualization code here
    # ...
    
    html += "</body></html>"
    
    # Write to file
    html_path = os.path.splitext(output_path)[0] + ".html"
    with open(html_path, "w") as f:
        f.write(html)
    
    return html_path
```

### 2. Integrate with Main Class

Add a method to `TaxonomyPlanner`:

```python
from .visualization import generate_html_visualization

class TaxonomyPlanner:
    # Existing methods...
    
    async def generate_taxonomy_with_visualization(
        self, 
        root_category: str, 
        jurisdictions: Optional[List[str]] = None,
        output_path: Optional[str] = None,
        visualize: bool = True
    ) -> Dict[str, Any]:
        """Generate taxonomy with visualization.
        
        Args:
            root_category: Root category
            jurisdictions: Jurisdictions
            output_path: Output path
            visualize: Whether to generate visualization
            
        Returns:
            Generated taxonomy
        """
        # Generate taxonomy
        taxonomy = await self.generate_taxonomy(
            root_category, 
            jurisdictions, 
            output_path
        )
        
        # Generate visualization if requested
        if visualize and output_path:
            html_path = generate_html_visualization(taxonomy, output_path)
            print(f"Visualization saved to {html_path}")
        
        return taxonomy
```