"""Test fixtures for Taxonomy Planner tests."""

import os
import pytest
import tempfile
import asyncio
from unittest.mock import MagicMock, AsyncMock

from applications.taxonomy_planner.persistence import TaxonomyStore
from applications.taxonomy_planner.config import TaxonomyConfig
from applications.taxonomy_planner.patterns import SearchEnhancedExplorationPattern


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_storage_path():
    """Create a temporary file for storage testing."""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def empty_taxonomy_store(temp_storage_path):
    """Create an empty taxonomy store for testing."""
    return TaxonomyStore(storage_path=temp_storage_path)


@pytest.fixture
def populated_taxonomy_store(empty_taxonomy_store):
    """Create a pre-populated taxonomy store for testing."""
    store = empty_taxonomy_store
    
    # Add nodes to create a simple taxonomy
    store.add_node("Technology")  # Root
    
    # Level 1 categories
    store.add_node("Hardware", parent="Technology")
    store.add_node("Software", parent="Technology")
    store.add_node("Networks", parent="Technology")
    
    # Level 2 categories
    store.add_node("Computers", parent="Hardware")
    store.add_node("Mobile Devices", parent="Hardware")
    store.add_node("Operating Systems", parent="Software")
    store.add_node("Applications", parent="Software")
    
    # Add some compliance mappings
    store.add_compliance_mapping("Computers", "USA", {
        "regulations": ["FCC Part 15", "UL Certification"],
        "standards": ["ENERGY STAR"]
    })
    
    # Add some legal mappings
    store.add_legal_mapping("Software", "EU", {
        "regulations": ["GDPR", "EU Copyright Directive"],
        "licenses": ["Proprietary", "Open Source"]
    })
    
    store.save()
    return store


@pytest.fixture
def default_config():
    """Create a default TaxonomyConfig for testing."""
    config = TaxonomyConfig()
    return config


@pytest.fixture
def custom_config():
    """Create a custom TaxonomyConfig for testing."""
    config = TaxonomyConfig()
    
    # Override some defaults
    config.max_depth = 4
    config.default_jurisdictions = ["USA", "EU", "Japan", "International"]
    
    # Set model assignments
    config.set_model_for_agent("planner", "openai/gpt-4o")
    config.set_model_for_agent("explorer", "anthropic/claude-3-sonnet")
    config.set_model_for_agent("compliance", "openai/gpt-4o-mini")
    config.set_model_for_agent("legal", "openai/gpt-4o-mini")
    
    # Adjust pattern configs
    config.pattern_configs["recursive_exploration"] = {
        "max_depth": 4,
        "breadth_limit": 8
    }
    
    return config


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = MagicMock()
    
    # Configure agent.execute to return appropriate test responses
    async def mock_execute(prompt, use_tools=None):
        """Mock agent execution with predefined responses."""
        if "internal knowledge" in prompt and "Technology" in prompt:
            return """
            Subcategories from knowledge base:
            - Hardware
            - Software
            - Networks
            """
        elif "search for subcategories" in prompt and "Technology" in prompt:
            return """
            Subcategories from search:
            - Hardware
            - Software
            - Data Science
            - Artificial Intelligence
            """
        elif "validate and filter" in prompt and "Technology" in prompt:
            return """
            Validated subcategories:
            - Hardware
            - Software
            - Networks
            - Data Science
            - Artificial Intelligence
            """
        elif "select" in prompt and "important" in prompt:
            # Simulate prioritization for breadth limiting
            categories = prompt.split(":")[1].strip().split(",")
            selected = categories[:3]  # Just take the first 3 for simplicity
            return "- " + "\n- ".join(selected)
        
        return "No relevant subcategories found."
    
    agent.execute = mock_execute
    return agent


@pytest.fixture
def exploration_pattern():
    """Create a search-enhanced exploration pattern for testing."""
    return SearchEnhancedExplorationPattern()


class MockSymphony:
    """Mock Symphony instance for testing."""
    
    def __init__(self):
        self.setup_called = False
        self.workflows = MagicMock()
        self.workflows.get_engine.return_value = MagicMock()
        
        # Mock workflow engine
        engine = self.workflows.get_engine.return_value
        engine.execute_workflow = AsyncMock()
        engine.execute_workflow.return_value.metadata = {"context": {"taxonomy": {"category": "Test"}}}
        
        # Mock build_workflow
        self.build_workflow = MagicMock()
        workflow_builder = MagicMock()
        workflow_builder.name = MagicMock(return_value=workflow_builder)
        workflow_builder.description = MagicMock(return_value=workflow_builder)
        workflow_builder.add_step = MagicMock(return_value=workflow_builder)
        workflow_builder.build.return_value = MagicMock()
        self.build_workflow.return_value = workflow_builder
        
        # Mock build_step
        self.build_step = MagicMock()
        step_builder = MagicMock()
        step_builder.name.return_value = step_builder
        step_builder.description.return_value = step_builder
        step_builder.agent.return_value = step_builder
        step_builder.task.return_value = step_builder
        step_builder.pattern.return_value = step_builder
        step_builder.context_data.return_value = step_builder
        step_builder.output_key.return_value = step_builder
        step_builder.processing_function.return_value = step_builder
        step_builder.build.return_value = MagicMock()
        self.build_step.return_value = step_builder
        
        # Mock create_agent
        self.create_agent = AsyncMock()
        self.create_agent.return_value = MagicMock()
        
        # Mock create_memory
        self.create_memory = MagicMock()
        self.create_memory.return_value = MagicMock()
    
    async def setup(self, **kwargs):
        """Mock setup method."""
        self.setup_called = True
        self.setup_kwargs = kwargs
        return None


@pytest.fixture
def mock_symphony():
    """Create a mock Symphony instance."""
    return MockSymphony()