"""Unit tests for the workflow definition components."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from symphony.orchestration.workflow_definition import (
    WorkflowDefinition, 
    WorkflowStep, 
    WorkflowContext, 
    StepResult
)


class MockStep(WorkflowStep):
    """Mock step implementation for testing."""
    
    def __init__(self, name, description="", should_succeed=True):
        super().__init__(name, description)
        self.should_succeed = should_succeed
        self.execute_called = False
        
    async def execute(self, context):
        """Mock execution that returns success or failure based on should_succeed."""
        self.execute_called = True
        if self.should_succeed:
            return StepResult(success=True, output={"result": f"Result from {self.name}"})
        else:
            return StepResult(success=False, output={}, error=f"Error from {self.name}")
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data["should_succeed"] = self.should_succeed
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            should_succeed=data.get("should_succeed", True)
        )


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition class."""
    
    def test_create_workflow_definition(self):
        """Test creating a workflow definition."""
        workflow = WorkflowDefinition(
            name="Test Workflow",
            description="Test description"
        )
        
        assert workflow.name == "Test Workflow"
        assert workflow.description == "Test description"
        assert workflow.steps == []
        assert isinstance(workflow.created_at, datetime)
        
    def test_add_step(self):
        """Test adding a step to the workflow."""
        workflow = WorkflowDefinition(
            name="Test Workflow",
            description="Test description"
        )
        
        step = MockStep("Test Step")
        updated_workflow = workflow.add_step(step)
        
        # Original workflow should be unchanged
        assert len(workflow.steps) == 0
        
        # Updated workflow should have the step
        assert len(updated_workflow.steps) == 1
        assert updated_workflow.steps[0]["type"] == "MockStep"
        assert updated_workflow.steps[0]["name"] == "Test Step"
        
    def test_get_steps(self):
        """Test getting instantiated steps."""
        workflow = WorkflowDefinition(
            name="Test Workflow",
            description="Test description"
        )
        
        step1 = MockStep("Step 1")
        step2 = MockStep("Step 2")
        
        workflow = workflow.add_step(step1)
        workflow = workflow.add_step(step2)
        
        steps = workflow.get_steps()
        
        assert len(steps) == 2
        assert isinstance(steps[0], MockStep)
        assert isinstance(steps[1], MockStep)
        assert steps[0].name == "Step 1"
        assert steps[1].name == "Step 2"


class TestWorkflowContext:
    """Tests for WorkflowContext class."""
    
    def test_context_get_set(self):
        """Test getting and setting context values."""
        context = WorkflowContext(
            workflow_id="test_workflow",
            data={"initial_key": "initial_value"}
        )
        
        # Get existing value
        assert context.get("initial_key") == "initial_value"
        
        # Get with default
        assert context.get("nonexistent", "default") == "default"
        
        # Set value
        context.set("new_key", "new_value")
        assert context.get("new_key") == "new_value"
        
    def test_get_service(self):
        """Test getting a service from registry."""
        mock_registry = MagicMock()
        mock_registry.get_service.return_value = "test_service"
        
        context = WorkflowContext(
            workflow_id="test_workflow",
            service_registry=mock_registry
        )
        
        # Get service
        service = context.get_service("test_service_name")
        
        assert service == "test_service"
        mock_registry.get_service.assert_called_once_with("test_service_name")
        
    def test_get_service_no_registry(self):
        """Test error when getting service with no registry."""
        context = WorkflowContext(workflow_id="test_workflow")
        
        with pytest.raises(ValueError, match="Service registry not available in context"):
            context.get_service("test_service_name")
            
    def test_resolve_template_string(self):
        """Test resolving template strings."""
        context = WorkflowContext(
            workflow_id="test_workflow",
            data={
                "name": "John",
                "count": 42,
                "nested": {"value": "nested_value"}
            }
        )
        
        # Simple template
        template = "Hello, {{name}}!"
        resolved = context.resolve_template(template)
        assert resolved == "Hello, John!"
        
        # Template with number
        template = "Count: {{count}}"
        resolved = context.resolve_template(template)
        assert resolved == "Count: 42"
        
        # Template that doesn't match any context value
        template = "Missing: {{missing}}"
        resolved = context.resolve_template(template)
        assert resolved == "Missing: {{missing}}"
        
        # Multiple replacements
        template = "{{name}} has {{count}} items"
        resolved = context.resolve_template(template)
        assert resolved == "John has 42 items"
        
    def test_resolve_template_complex(self):
        """Test resolving templates in complex structures."""
        context = WorkflowContext(
            workflow_id="test_workflow",
            data={
                "name": "John",
                "count": 42
            }
        )
        
        # Template in dictionary
        template = {
            "user": "{{name}}",
            "items": "{{count}}",
            "nested": {
                "greeting": "Hello, {{name}}!"
            }
        }
        
        resolved = context.resolve_template(template)
        assert resolved["user"] == "John"
        assert resolved["items"] == "42"
        assert resolved["nested"]["greeting"] == "Hello, John!"
        
        # Template in list
        template = ["{{name}}", "has", "{{count}}", "items"]
        resolved = context.resolve_template(template)
        assert resolved == ["John", "has", "42", "items"]
        
    def test_evaluate_condition(self):
        """Test evaluating conditions."""
        context = WorkflowContext(
            workflow_id="test_workflow",
            data={
                "count": 42,
                "name": "John",
                "is_admin": True
            }
        )
        
        # Simple condition
        assert context.evaluate_condition("count > 40") is True
        assert context.evaluate_condition("count < 40") is False
        
        # Condition with string
        assert context.evaluate_condition("name == 'John'") is True
        assert context.evaluate_condition("name == 'Jane'") is False
        
        # Condition with boolean
        assert context.evaluate_condition("is_admin") is True
        
        # Complex condition
        assert context.evaluate_condition("count > 40 and name == 'John'") is True
        
        # Condition with template variables
        assert context.evaluate_condition("count > {{count}} - 10") is True
        
    def test_create_sub_context(self):
        """Test creating a sub-context."""
        mock_registry = MagicMock()
        context = WorkflowContext(
            workflow_id="test_workflow",
            data={"key": "value"},
            service_registry=mock_registry
        )
        
        # Create sub-context
        sub_context = context.create_sub_context()
        
        # Should have same workflow ID and registry
        assert sub_context.workflow_id == context.workflow_id
        assert sub_context.service_registry is context.service_registry
        
        # Should have a copy of the data
        assert sub_context.data == context.data
        assert sub_context.data is not context.data  # Should be a copy
        
        # Modifying sub-context should not affect parent
        sub_context.set("new_key", "new_value")
        assert sub_context.get("new_key") == "new_value"
        assert context.get("new_key", None) is None


class TestStepResult:
    """Tests for StepResult class."""
    
    def test_create_success_result(self):
        """Test creating a successful result."""
        result = StepResult(
            success=True,
            output={"result": "test result"},
            task_id="test_task_id"
        )
        
        assert result.success is True
        assert result.output == {"result": "test result"}
        assert result.task_id == "test_task_id"
        assert result.error is None
        
    def test_create_failure_result(self):
        """Test creating a failure result."""
        result = StepResult(
            success=False,
            output={},
            error="Test error message"
        )
        
        assert result.success is False
        assert result.output == {}
        assert result.error == "Test error message"
        assert result.task_id is None