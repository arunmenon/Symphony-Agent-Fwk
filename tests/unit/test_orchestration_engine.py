"""Unit tests for the workflow engine."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from symphony.core.registry import ServiceRegistry
from symphony.persistence.repository import Repository
from symphony.execution.workflow_tracker import WorkflowTracker, Workflow, WorkflowStatus
from symphony.orchestration.workflow_definition import (
    WorkflowDefinition, 
    WorkflowStep, 
    WorkflowContext, 
    StepResult
)
from symphony.orchestration.engine import WorkflowEngine


class MockStep(WorkflowStep):
    """Mock step implementation for testing."""
    
    def __init__(self, name, description="", should_succeed=True, result_output=None):
        super().__init__(name, description)
        self.should_succeed = should_succeed
        self.result_output = result_output or {"result": f"Result from {name}"}
        self.execute_count = 0
        
    async def execute(self, context):
        """Mock execution that returns success or failure based on should_succeed."""
        self.execute_count += 1
        
        if self.should_succeed:
            return StepResult(success=True, output=self.result_output)
        else:
            return StepResult(success=False, output={}, error=f"Error from {self.name}")
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data["should_succeed"] = self.should_succeed
        data["result_output"] = self.result_output
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            should_succeed=data.get("should_succeed", True),
            result_output=data.get("result_output")
        )


@pytest.fixture
def mock_registry():
    """Create a mock service registry."""
    return MagicMock(spec=ServiceRegistry)


@pytest.fixture
def mock_workflow_def_repo():
    """Create a mock workflow definition repository."""
    repo = AsyncMock(spec=Repository)
    
    # Setup find_by_id to return a workflow definition
    test_workflow_def = WorkflowDefinition(
        id="test_workflow_def_id",
        name="Test Workflow Definition",
        description="Test workflow definition"
    )
    test_workflow_def.steps = [
        {
            "id": "step1_id",
            "type": "MockStep",
            "name": "Step 1",
            "should_succeed": True,
            "result_output": {"result": "Result from Step 1"}
        },
        {
            "id": "step2_id",
            "type": "MockStep",
            "name": "Step 2",
            "should_succeed": True,
            "result_output": {"result": "Result from Step 2"}
        }
    ]
    
    failing_workflow_def = WorkflowDefinition(
        id="failing_workflow_def_id",
        name="Failing Workflow Definition",
        description="Workflow definition with failing step"
    )
    failing_workflow_def.steps = [
        {
            "id": "step1_id",
            "type": "MockStep",
            "name": "Step 1",
            "should_succeed": True,
            "result_output": {"result": "Result from Step 1"}
        },
        {
            "id": "step2_id",
            "type": "MockStep",
            "name": "Step 2",
            "should_succeed": False,
            "result_output": {}
        }
    ]
    
    async def mock_find_by_id(id):
        if id == "test_workflow_def_id":
            return test_workflow_def
        elif id == "failing_workflow_def_id":
            return failing_workflow_def
        elif id == "nonexistent_id":
            return None
        return None
        
    repo.find_by_id.side_effect = mock_find_by_id
    
    return repo


@pytest.fixture
def mock_workflow_tracker():
    """Create a mock workflow tracker."""
    tracker = AsyncMock(spec=WorkflowTracker)
    
    # Setup create_workflow
    async def mock_create_workflow(**kwargs):
        return Workflow(
            id="test_workflow_id",
            name=kwargs.get("name", "Test Workflow"),
            description=kwargs.get("description", ""),
            status=WorkflowStatus.PENDING,
            metadata=kwargs.get("metadata", {}).copy()
        )
    tracker.create_workflow.side_effect = mock_create_workflow
    
    # Setup get_workflow
    async def mock_get_workflow(workflow_id):
        if workflow_id == "test_workflow_id":
            return Workflow(
                id=workflow_id,
                name="Test Workflow",
                status=WorkflowStatus.COMPLETED,
                metadata={"context": {"key": "value"}}
            )
        return None
    tracker.get_workflow.side_effect = mock_get_workflow
    
    # Setup workflow_repository
    tracker.workflow_repository = AsyncMock(spec=Repository)
    
    return tracker


@pytest.fixture
def workflow_engine(mock_registry, mock_workflow_def_repo, mock_workflow_tracker):
    """Create a workflow engine with mocks."""
    # Register MockStep for instantiation
    WorkflowStep.STEP_REGISTRY["MockStep"] = MockStep
    
    return WorkflowEngine(
        service_registry=mock_registry,
        workflow_definition_repository=mock_workflow_def_repo,
        workflow_tracker=mock_workflow_tracker
    )


class TestWorkflowEngine:
    """Tests for WorkflowEngine class."""
    
    @pytest.mark.asyncio
    async def test_execute_workflow_by_id_success(self, workflow_engine, mock_workflow_def_repo, mock_workflow_tracker):
        """Test executing a workflow by definition ID with success."""
        # Execute workflow
        workflow = await workflow_engine.execute_workflow_by_id("test_workflow_def_id")
        
        # Verify workflow definition was retrieved
        mock_workflow_def_repo.find_by_id.assert_called_once_with("test_workflow_def_id")
        
        # Verify workflow was created
        mock_workflow_tracker.create_workflow.assert_called_once()
        
        # Verify workflow status was updated to running
        mock_workflow_tracker.update_workflow_status.assert_any_call(
            workflow.id, WorkflowStatus.RUNNING
        )
        
        # Verify workflow status was updated to completed
        mock_workflow_tracker.update_workflow_status.assert_any_call(
            workflow.id, WorkflowStatus.COMPLETED
        )
        
    @pytest.mark.asyncio
    async def test_execute_workflow_by_id_nonexistent(self, workflow_engine, mock_workflow_def_repo):
        """Test executing a nonexistent workflow definition."""
        # Try to execute nonexistent workflow
        with pytest.raises(ValueError, match="Workflow definition nonexistent_id not found"):
            await workflow_engine.execute_workflow_by_id("nonexistent_id")
            
        # Verify workflow definition was looked up
        mock_workflow_def_repo.find_by_id.assert_called_once_with("nonexistent_id")
        
    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, workflow_engine, mock_workflow_tracker):
        """Test executing a workflow with success."""
        # Create workflow definition with steps
        step1 = MockStep("Step 1")
        step2 = MockStep("Step 2")
        
        workflow_def = WorkflowDefinition(
            name="Test Workflow",
            description="Test workflow"
        )
        workflow_def = workflow_def.add_step(step1)
        workflow_def = workflow_def.add_step(step2)
        
        # Execute workflow
        workflow = await workflow_engine.execute_workflow(workflow_def)
        
        # Verify steps were executed
        assert step1.execute_count == 1
        assert step2.execute_count == 1
        
        # Verify workflow status was updated correctly
        mock_workflow_tracker.update_workflow_status.assert_any_call(
            workflow.id, WorkflowStatus.RUNNING
        )
        mock_workflow_tracker.update_workflow_status.assert_any_call(
            workflow.id, WorkflowStatus.COMPLETED
        )
        
        # Verify workflow definition ID was stored in metadata
        mock_workflow_tracker.workflow_repository.update.assert_called()
        
    @pytest.mark.asyncio
    async def test_execute_workflow_with_failing_step(self, workflow_engine, mock_workflow_tracker):
        """Test executing a workflow with a failing step."""
        # Create workflow definition with steps
        step1 = MockStep("Step 1")
        step2 = MockStep("Step 2", should_succeed=False)
        step3 = MockStep("Step 3")  # Should not be executed
        
        workflow_def = WorkflowDefinition(
            name="Test Workflow",
            description="Test workflow"
        )
        workflow_def = workflow_def.add_step(step1)
        workflow_def = workflow_def.add_step(step2)
        workflow_def = workflow_def.add_step(step3)
        
        # Execute workflow
        workflow = await workflow_engine.execute_workflow(workflow_def)
        
        # Verify steps were executed correctly
        assert step1.execute_count == 1
        assert step2.execute_count == 1
        assert step3.execute_count == 0  # Step 3 should not be executed
        
        # Verify workflow status was updated to failed
        mock_workflow_tracker.update_workflow_status.assert_any_call(
            workflow.id, 
            WorkflowStatus.FAILED,
            f"Step '{step2.name}' failed: Error from {step2.name}"
        )
        
    @pytest.mark.asyncio
    async def test_execute_workflow_by_id_with_failing_step(self, workflow_engine, mock_workflow_tracker):
        """Test executing a workflow by ID with a failing step."""
        # Execute workflow
        workflow = await workflow_engine.execute_workflow_by_id("failing_workflow_def_id")
        
        # Verify workflow status was updated to failed
        mock_workflow_tracker.update_workflow_status.assert_any_call(
            workflow.id, 
            WorkflowStatus.FAILED,
            "Step 'Step 2' failed: Error from Step 2"
        )
        
    @pytest.mark.asyncio
    async def test_execute_workflow_with_exception(self, workflow_engine, mock_workflow_tracker):
        """Test handling exceptions during workflow execution."""
        # Create step that raises an exception
        step = MagicMock()  # Non-async mock will raise an error when executed
        
        workflow_def = WorkflowDefinition(
            name="Test Workflow",
            description="Test workflow"
        )
        workflow_def = workflow_def.add_step(step)
        
        # Execute workflow
        workflow = await workflow_engine.execute_workflow(workflow_def)
        
        # Verify workflow status was updated to failed
        mock_workflow_tracker.update_workflow_status.assert_any_call(
            workflow.id, 
            WorkflowStatus.FAILED,
            "Workflow execution error: 'coroutine' object is not callable"
        )
        
    @pytest.mark.asyncio
    async def test_execute_workflow_with_initial_context(self, workflow_engine, mock_workflow_tracker):
        """Test executing a workflow with initial context data."""
        # Create step that accesses context
        step = MockStep("Context Step")
        
        workflow_def = WorkflowDefinition(
            name="Test Workflow",
            description="Test workflow"
        )
        workflow_def = workflow_def.add_step(step)
        
        # Create initial context
        initial_context = {
            "user_id": "test_user",
            "session_id": "test_session"
        }
        
        # Execute workflow with initial context
        workflow = await workflow_engine.execute_workflow(workflow_def, initial_context)
        
        # Verify context was stored in workflow metadata
        calls = mock_workflow_tracker.workflow_repository.update.call_args_list
        updated_workflow = calls[-1][0][0]
        
        # Verify context contains initial data
        assert "user_id" in updated_workflow.metadata["context"]
        assert updated_workflow.metadata["context"]["user_id"] == "test_user"
        assert "session_id" in updated_workflow.metadata["context"]
        assert updated_workflow.metadata["context"]["session_id"] == "test_session"
        
    @pytest.mark.asyncio
    async def test_execute_workflow_context_updates(self, workflow_engine, mock_workflow_tracker):
        """Test that context is properly updated after each step."""
        # Create custom mock step that updates context
        class ContextUpdatingStep(MockStep):
            async def execute(self, context):
                # Update context with step-specific info
                context.set(f"step_{self.name}_executed", True)
                return await super().execute(context)
                
        # Create workflow with context-updating steps
        step1 = ContextUpdatingStep("Step1")
        step2 = ContextUpdatingStep("Step2")
        
        workflow_def = WorkflowDefinition(
            name="Context Test Workflow",
            description="Test workflow that updates context"
        )
        workflow_def = workflow_def.add_step(step1)
        workflow_def = workflow_def.add_step(step2)
        
        # Execute workflow
        workflow = await workflow_engine.execute_workflow(workflow_def)
        
        # Verify context was stored in workflow metadata
        calls = mock_workflow_tracker.workflow_repository.update.call_args_list
        updated_workflow = calls[-1][0][0]
        
        # Verify context contains updates from both steps
        assert "step_Step1_executed" in updated_workflow.metadata["context"]
        assert updated_workflow.metadata["context"]["step_Step1_executed"] is True
        assert "step_Step2_executed" in updated_workflow.metadata["context"]
        assert updated_workflow.metadata["context"]["step_Step2_executed"] is True
        
    @pytest.mark.asyncio
    async def test_execute_workflow_step_results_in_context(self, workflow_engine, mock_workflow_tracker):
        """Test that step results are properly stored in context."""
        # Create steps with specific results
        step1 = MockStep("Step1", result_output={"result": "Step 1 result", "extra": "info"})
        step2 = MockStep("Step2", result_output={"result": "Step 2 result", "data": ["a", "b", "c"]})
        
        workflow_def = WorkflowDefinition(
            name="Results Test Workflow",
            description="Test workflow with specific step results"
        )
        workflow_def = workflow_def.add_step(step1)
        workflow_def = workflow_def.add_step(step2)
        
        # Execute workflow
        workflow = await workflow_engine.execute_workflow(workflow_def)
        
        # Verify context was stored in workflow metadata
        calls = mock_workflow_tracker.workflow_repository.update.call_args_list
        updated_workflow = calls[-1][0][0]
        
        # Verify step results were stored in context
        assert f"step_results.0" in updated_workflow.metadata["context"]
        assert updated_workflow.metadata["context"][f"step_results.0"]["name"] == "Step1"
        assert updated_workflow.metadata["context"][f"step_results.0"]["output"]["result"] == "Step 1 result"
        assert updated_workflow.metadata["context"][f"step_results.0"]["output"]["extra"] == "info"
        
        assert f"step_results.1" in updated_workflow.metadata["context"]
        assert updated_workflow.metadata["context"][f"step_results.1"]["name"] == "Step2"
        assert updated_workflow.metadata["context"][f"step_results.1"]["output"]["result"] == "Step 2 result"
        assert updated_workflow.metadata["context"][f"step_results.1"]["output"]["data"] == ["a", "b", "c"]