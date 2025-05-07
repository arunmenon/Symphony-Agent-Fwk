"""End-to-end integration tests for Taxonomy Planner with Symphony 0.1.0a3."""

import os
import sys
import pytest
import asyncio
from unittest.mock import patch
import shutil
import json

# Add parent directory to path for importing application modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from applications.taxonomy_planner.config import TaxonomyConfig
from applications.taxonomy_planner.main import TaxonomyPlanner
from applications.taxonomy_planner.persistence import TaxonomyStore

# Test directory for outputs
TEST_OUTPUT_DIR = os.path.join(parent_dir, "output", "test")
TEST_STORAGE_DIR = os.path.join(parent_dir, "storage", "test")
os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
os.makedirs(TEST_STORAGE_DIR, exist_ok=True)

# Test data
TEST_CATEGORY = "Weapons"
TEST_MAX_DEPTH = 2
TEST_BREADTH_LIMIT = 3
TEST_STRATEGY = "parallel"
TEST_JURISDICTIONS = ["USA"]

class TestE2EIntegration:
    """End-to-end tests for Taxonomy Planner with Symphony 0.1.0a3."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        # Clean up any previous test files
        for file in os.listdir(TEST_OUTPUT_DIR):
            if file.endswith(".json"):
                os.remove(os.path.join(TEST_OUTPUT_DIR, file))
                
        for file in os.listdir(TEST_STORAGE_DIR):
            if file.endswith(".json"):
                os.remove(os.path.join(TEST_STORAGE_DIR, file))
        
        # Create storage directory for Symphony state
        os.makedirs(os.path.join(TEST_STORAGE_DIR, ".symphony"), exist_ok=True)
    
    @pytest.mark.asyncio
    async def test_taxonomy_planner_initialization(self):
        """Test that TaxonomyPlanner can be initialized with Symphony 0.1.0a3."""
        # Create config with test parameters
        config = TaxonomyConfig()
        # Use smaller, faster models for testing
        config.set_model_for_agent("planner", "openai/gpt-4o-mini")
        config.set_model_for_agent("explorer", "openai/gpt-4o-mini")
        config.set_model_for_agent("compliance", "openai/gpt-4o-mini")
        config.set_model_for_agent("legal", "openai/gpt-4o-mini")
        
        # Initialize planner
        planner = TaxonomyPlanner(config)
        await planner.setup(storage_path=os.path.join(TEST_STORAGE_DIR, "taxonomy_store.json"))
        
        # Check that planner was initialized correctly
        assert planner.initialized == True
        assert planner.symphony is not None
        assert len(planner.agents) == 4
        assert len(planner.patterns) > 0
        assert planner.store is not None
        assert planner.workflow_definition is not None
        assert len(planner.workflow_definition.steps) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OpenAI API key not available")
    async def test_minimal_taxonomy_generation(self):
        """Test generating a minimal taxonomy with Symphony 0.1.0a3."""
        # Create config with test parameters
        config = TaxonomyConfig()
        # Use smaller, faster models for testing
        config.set_model_for_agent("planner", "openai/gpt-4o-mini")
        config.set_model_for_agent("explorer", "openai/gpt-4o-mini")
        config.set_model_for_agent("compliance", "openai/gpt-4o-mini")
        config.set_model_for_agent("legal", "openai/gpt-4o-mini")
        
        # Set up output and storage paths
        output_path = os.path.join(TEST_OUTPUT_DIR, f"{TEST_CATEGORY.lower()}_taxonomy.json")
        storage_path = os.path.join(TEST_STORAGE_DIR, f"{TEST_CATEGORY.lower()}_store.json")
        
        # Initialize planner
        planner = TaxonomyPlanner(config)
        await planner.setup(storage_path=storage_path)
        
        # Run taxonomy generation with minimal parameters
        taxonomy = await planner.generate_taxonomy(
            root_category=TEST_CATEGORY,
            jurisdictions=TEST_JURISDICTIONS,
            max_depth=TEST_MAX_DEPTH,
            breadth_limit=TEST_BREADTH_LIMIT,
            strategy=TEST_STRATEGY,
            output_path=output_path,
            storage_path=storage_path
        )
        
        # Verify taxonomy was generated and saved
        assert taxonomy is not None
        assert "category" in taxonomy
        assert taxonomy["category"] == TEST_CATEGORY
        assert "subcategories" in taxonomy
        assert "metadata" in taxonomy
        
        # Verify that the output file was created
        assert os.path.exists(output_path)
        with open(output_path, "r") as f:
            saved_taxonomy = json.load(f)
        assert saved_taxonomy["category"] == TEST_CATEGORY
    
    @pytest.mark.asyncio
    async def test_mock_taxonomy_generation(self):
        """Test taxonomy generation with mocked Symphony to avoid API calls."""
        # Create config with test parameters
        config = TaxonomyConfig()
        
        # Mock symphony setup and agent execution
        with patch('symphony.api.Symphony') as mock_symphony:
            # Set up mock for workflow execution
            mock_result = mock_symphony.return_value.workflows.execute_workflow.return_value
            mock_result.metadata = {
                "context": {
                    "taxonomy": {
                        "category": TEST_CATEGORY,
                        "subcategories": [
                            {"category": "Firearms", "subcategories": []},
                            {"category": "Bladed Weapons", "subcategories": []},
                            {"category": "Explosives", "subcategories": []}
                        ],
                        "metadata": {
                            "generated_at": "2025-05-08T00:00:00.000000",
                            "max_depth": TEST_MAX_DEPTH,
                            "jurisdictions": TEST_JURISDICTIONS
                        }
                    }
                }
            }
            
            # Setup output paths
            output_path = os.path.join(TEST_OUTPUT_DIR, f"{TEST_CATEGORY.lower()}_mock_taxonomy.json")
            storage_path = os.path.join(TEST_STORAGE_DIR, f"{TEST_CATEGORY.lower()}_mock_store.json")
            
            # Initialize planner with mocked Symphony
            planner = TaxonomyPlanner(config)
            await planner.setup(storage_path=storage_path)
            
            # Run taxonomy generation
            taxonomy = await planner.generate_taxonomy(
                root_category=TEST_CATEGORY,
                jurisdictions=TEST_JURISDICTIONS,
                max_depth=TEST_MAX_DEPTH,
                breadth_limit=TEST_BREADTH_LIMIT,
                strategy=TEST_STRATEGY,
                output_path=output_path,
                storage_path=storage_path
            )
            
            # Verify taxonomy was generated using mock data
            assert taxonomy is not None
            assert taxonomy["category"] == TEST_CATEGORY
            assert len(taxonomy["subcategories"]) == 3
            
            # Verify mock was called correctly with API parameters
            mock_symphony.return_value.workflows.execute_workflow.assert_called_once()
            
            # Extract and check call arguments
            call_args = mock_symphony.return_value.workflows.execute_workflow.call_args
            assert call_args[1]["auto_checkpoint"] is True
            assert call_args[1]["resume_from_checkpoint"] is True
            
            # Check that initial context was passed correctly
            context = call_args[1]["initial_context"]
            assert context["root_category"] == TEST_CATEGORY
            assert context["jurisdictions"] == TEST_JURISDICTIONS
            assert context["max_depth"] == TEST_MAX_DEPTH
            assert context["breadth_limit"] == TEST_BREADTH_LIMIT
            assert context["strategy"] == TEST_STRATEGY