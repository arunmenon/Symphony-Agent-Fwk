"""Integration tests for the Taxonomy Planner application."""

import os
import pytest
import asyncio
import tempfile
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any, List, Optional

from applications.taxonomy_planner.main import TaxonomyPlanner, generate_taxonomy
from applications.taxonomy_planner.config import TaxonomyConfig
from applications.taxonomy_planner.persistence import TaxonomyStore


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


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def patched_planner(mock_symphony):
    """Create a taxonomy planner with mocked Symphony."""
    with patch('applications.taxonomy_planner.main.Symphony', return_value=mock_symphony):
        config = TaxonomyConfig()
        planner = TaxonomyPlanner(config)
        return planner


class TestTaxonomyPlannerIntegration:
    """Integration tests for Taxonomy Planner."""
    
    @pytest.mark.asyncio
    async def test_setup_initializes_components(self, patched_planner, mock_symphony):
        """Test that setup initializes all components correctly."""
        # Patch the TaxonomyStore
        with patch('applications.taxonomy_planner.main.TaxonomyStore') as mock_store:
            # Setup the planner
            await patched_planner.setup()
            
            # Verify Symphony was initialized
            assert mock_symphony.setup_called
            
            # Verify TaxonomyStore was created
            assert mock_store.called
            
            # Verify workflow definition was created
            assert patched_planner.workflow_definition is not None
            
            # Verify agents were created
            assert mock_symphony.create_agent.called
            
            # Verify planner is marked as initialized
            assert patched_planner.initialized
    
    @pytest.mark.asyncio
    async def test_process_plan_extracts_categories(self, patched_planner):
        """Test that _process_plan extracts categories correctly."""
        # Mock TaxonomyStore
        mock_store = MagicMock()
        
        # Sample plan output
        plan = """
        # Taxonomy for Technology
        
        * Hardware
        * Software
        * Networks
        """
        
        # Create context
        context = {
            "plan": plan,
            "root_category": "Technology",
            "store": mock_store
        }
        
        # Process the plan
        result = await patched_planner._process_plan(context)
        
        # Verify categories were extracted
        assert len(result) >= 3
        assert "Hardware" in result
        assert "Software" in result
        assert "Networks" in result
        
        # Verify store methods were called
        assert mock_store.add_node.called
        assert mock_store.save.called
    
    @pytest.mark.asyncio
    async def test_generate_taxonomy_workflow(self, patched_planner, mock_symphony):
        """Test the generate_taxonomy method executes the workflow correctly."""
        # Setup the planner
        await patched_planner.setup()
        
        # Generate a taxonomy
        result = await patched_planner.generate_taxonomy(
            root_category="Technology",
            jurisdictions=["USA", "EU"],
            max_depth=3,
            breadth_limit=10,
            strategy="parallel"
        )
        
        # Verify workflow was executed
        engine = mock_symphony.workflows.get_engine.return_value
        assert engine.execute_workflow.called
        
        # Verify parameters were passed correctly
        call_args = engine.execute_workflow.call_args[1]
        initial_context = call_args["initial_context"]
        
        assert initial_context["root_category"] == "Technology"
        assert initial_context["jurisdictions"] == ["USA", "EU"]
        assert initial_context["max_depth"] == 3
        assert initial_context["breadth_limit"] == 10
        assert initial_context["strategy"] == "parallel"
        
        # Verify auto-checkpoint was enabled
        assert call_args["auto_checkpoint"] is True
        assert call_args["resume_from_checkpoint"] is True
    
    @pytest.mark.asyncio
    async def test_workflow_definition_includes_plan_processing(self, patched_planner):
        """Test that the workflow definition includes the plan processing step."""
        # Setup the planner
        await patched_planner.setup()
        
        # Mock method to count steps in workflow definition
        step_count = 0
        steps_by_name = {}
        
        # Access the mock add_step calls
        workflow_builder = patched_planner.symphony.build_workflow()
        for call in workflow_builder.add_step.call_args_list:
            step = call[0][0]
            step_name = step.name.call_args[0][0]
            steps_by_name[step_name] = step
            step_count += 1
        
        # Verify PlanProcessing step exists
        assert "PlanProcessing" in steps_by_name
        
        # Verify it comes after Planning and before Exploration
        assert "Planning" in steps_by_name
        assert "Exploration" in steps_by_name
        
        # Verify all necessary steps are included
        assert "ComplianceMapping" in steps_by_name
        assert "LegalMapping" in steps_by_name
        assert "TreeBuilding" in steps_by_name
        assert "SaveOutput" in steps_by_name
    
    @pytest.mark.asyncio
    async def test_build_taxonomy_tree_uses_store(self, patched_planner):
        """Test that _build_taxonomy_tree uses TaxonomyStore correctly."""
        # Mock TaxonomyStore
        mock_store = MagicMock()
        mock_store.get_taxonomy_tree.return_value = {
            "category": "Technology",
            "subcategories": [
                {"category": "Hardware", "subcategories": []},
                {"category": "Software", "subcategories": []}
            ]
        }
        
        # Create context
        context = {
            "root_category": "Technology",
            "store": mock_store,
            "max_depth": 3,
            "jurisdictions": ["USA", "EU"]
        }
        
        # Build taxonomy tree
        result = await patched_planner._build_taxonomy_tree(context)
        
        # Verify store method was called
        assert mock_store.get_taxonomy_tree.called
        assert mock_store.get_taxonomy_tree.call_args[0][0] == "Technology"
        
        # Verify result is properly structured
        assert result["category"] == "Technology"
        assert "subcategories" in result
        assert len(result["subcategories"]) == 2
        assert "metadata" in result
        assert "generated_at" in result["metadata"]
        assert result["metadata"]["max_depth"] == 3
        assert result["metadata"]["jurisdictions"] == ["USA", "EU"]
    
    @pytest.mark.asyncio
    async def test_model_assignments(self, patched_planner, mock_symphony):
        """Test that model assignments are properly handled."""
        # Setup the planner with custom config
        config = TaxonomyConfig()
        config.set_model_for_agent("planner", "openai/gpt-4o")
        config.set_model_for_agent("explorer", "anthropic/claude-3-sonnet")
        
        with patch('applications.taxonomy_planner.main.Symphony', return_value=mock_symphony):
            patched_planner = TaxonomyPlanner(config)
            await patched_planner.setup()
        
        # Verify model is passed to agent creation
        create_agent_calls = mock_symphony.create_agent.call_args_list
        
        # Check for planner agent call
        planner_call = [call for call in create_agent_calls 
                        if call[1].get('name') == 'TaxonomyPlanner']
        assert len(planner_call) > 0
        assert planner_call[0][1].get('model') == 'openai/gpt-4o'
        
        # Check for explorer agent call
        explorer_call = [call for call in create_agent_calls 
                         if call[1].get('name') == 'CategoryExplorer']
        assert len(explorer_call) > 0
        assert explorer_call[0][1].get('model') == 'anthropic/claude-3-sonnet'
    
    @pytest.mark.asyncio
    async def test_high_level_api_function(self, mock_symphony, temp_dir):
        """Test the high-level generate_taxonomy API function."""
        # Patch TaxonomyPlanner to avoid actual execution
        with patch('applications.taxonomy_planner.main.TaxonomyPlanner') as mock_planner_class, \
             patch('applications.taxonomy_planner.main.Symphony', return_value=mock_symphony):
            
            # Setup mocks
            mock_planner_instance = AsyncMock()
            mock_planner_class.return_value = mock_planner_instance
            mock_planner_instance.setup = AsyncMock()
            mock_planner_instance.generate_taxonomy = AsyncMock()
            mock_planner_instance.generate_taxonomy.return_value = {"category": "Test"}
            
            # Create output path
            output_path = os.path.join(temp_dir, "taxonomy.json")
            
            # Define model assignments
            models = {
                "planner": "openai/gpt-4o",
                "explorer": "anthropic/claude-3-sonnet"
            }
            
            # Call the high-level API
            result = await generate_taxonomy(
                root_category="Technology",
                jurisdictions=["USA", "EU"],
                max_depth=3,
                breadth_limit=5,
                strategy="breadth_first",
                output_path=output_path,
                storage_path=os.path.join(temp_dir, "store.json"),
                models=models
            )
            
            # Verify planner was created with config
            mock_planner_class.assert_called_once()
            config = mock_planner_class.call_args[1]["config"]
            assert config is not None
            
            # Verify model assignments were applied
            for agent, model in models.items():
                assert config.get_model_for_agent(agent) == model
            
            # Verify setup and generate_taxonomy were called with correct args
            mock_planner_instance.setup.assert_called_once()
            mock_planner_instance.generate_taxonomy.assert_called_once()
            
            # Verify parameters were passed correctly
            call_args = mock_planner_instance.generate_taxonomy.call_args[1]
            assert call_args["root_category"] == "Technology"
            assert call_args["jurisdictions"] == ["USA", "EU"]
            assert call_args["max_depth"] == 3
            assert call_args["breadth_limit"] == 5
            assert call_args["strategy"] == "breadth_first"
            assert call_args["output_path"] == output_path