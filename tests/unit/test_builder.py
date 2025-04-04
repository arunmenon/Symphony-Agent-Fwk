"""Tests for Symphony Builder classes.

This module contains tests for the Symphony Builder classes that provide
fluent interfaces for creating Symphony components.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from symphony.core.registry import ServiceRegistry
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.core.task import Task, TaskStatus, TaskPriority
from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.orchestration.steps import TaskStep, ConditionalStep, ParallelStep, LoopStep
from symphony.execution.workflow_tracker import Workflow, WorkflowStatus

from symphony.builder.agent_builder import AgentBuilder
from symphony.builder.task_builder import TaskBuilder
from symphony.builder.workflow_builder import WorkflowBuilder


@pytest.fixture
def mock_registry():
    """Create a mock registry for testing."""
    registry = MagicMock(spec=ServiceRegistry)
    registry.repositories = {}
    return registry


class TestAgentBuilder:
    """Tests for the AgentBuilder class."""
    
    @pytest.fixture
    def agent_builder(self, mock_registry):
        """Create an AgentBuilder instance for testing."""
        return AgentBuilder(registry=mock_registry)
    
    def test_create_agent(self, agent_builder):
        """Test creating an agent with builder."""
        builder = agent_builder.create(
            name="TestAgent", 
            role="Test Role", 
            instruction_template="Test instructions"
        )
        
        assert builder is agent_builder  # Method chaining
        assert builder.agent_config is not None
        assert builder.agent_config.name == "TestAgent"
        assert builder.agent_config.role == "Test Role"
        assert builder.agent_config.instruction_template == "Test instructions"
    
    def test_with_capability(self, agent_builder):
        """Test adding a capability."""
        builder = agent_builder.create(
            name="TestAgent", 
            role="Test Role", 
            instruction_template="Test instructions"
        )
        
        builder.with_capability("test-capability")
        
        assert "test-capability" in builder.agent_config.capabilities.expertise
        assert len(builder.agent_config.capabilities.expertise) == 1
    
    def test_with_capabilities(self, agent_builder):
        """Test adding multiple capabilities."""
        builder = agent_builder.create(
            name="TestAgent", 
            role="Test Role", 
            instruction_template="Test instructions"
        )
        
        builder.with_capabilities(["test1", "test2", "test3"])
        
        assert "test1" in builder.agent_config.capabilities.expertise
        assert "test2" in builder.agent_config.capabilities.expertise
        assert "test3" in builder.agent_config.capabilities.expertise
        assert len(builder.agent_config.capabilities.expertise) == 3
    
    def test_with_model(self, agent_builder):
        """Test setting model."""
        builder = agent_builder.create(
            name="TestAgent", 
            role="Test Role", 
            instruction_template="Test instructions"
        )
        
        builder.with_model("gpt-4")
        
        assert builder.agent_config.model == "gpt-4"
    
    def test_with_metadata(self, agent_builder):
        """Test adding metadata."""
        builder = agent_builder.create(
            name="TestAgent", 
            role="Test Role", 
            instruction_template="Test instructions"
        )
        
        builder.with_metadata("key1", "value1")
        builder.with_metadata("key2", "value2")
        
        assert builder.agent_config.metadata["key1"] == "value1"
        assert builder.agent_config.metadata["key2"] == "value2"
    
    def test_build(self, agent_builder):
        """Test building the agent."""
        agent = (agent_builder
                .create("TestAgent", "Test Role", "Test instructions")
                .with_capability("test-capability")
                .with_model("gpt-4")
                .with_metadata("key", "value")
                .build())
        
        assert isinstance(agent, AgentConfig)
        assert agent.name == "TestAgent"
        assert agent.role == "Test Role"
        assert agent.instruction_template == "Test instructions"
        assert "test-capability" in agent.capabilities.expertise
        assert agent.model == "gpt-4"
        assert agent.metadata["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_save(self, agent_builder, mock_registry):
        """Test saving the agent."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.save.return_value = "test-id"
        mock_registry.get_repository.return_value = mock_repo
        
        # Build and save agent
        agent_id = await (agent_builder
                         .create("TestAgent", "Test Role", "Test instructions")
                         .with_capability("test-capability")
                         .save())
        
        assert agent_id == "test-id"
        mock_registry.get_repository.assert_called_once_with("agent_config")
        mock_repo.save.assert_called_once()


class TestTaskBuilder:
    """Tests for the TaskBuilder class."""
    
    @pytest.fixture
    def task_builder(self, mock_registry):
        """Create a TaskBuilder instance for testing."""
        return TaskBuilder(registry=mock_registry)
    
    def test_create_task(self, task_builder):
        """Test creating a task with builder."""
        builder = task_builder.create(
            name="TestTask", 
            description="Test description"
        )
        
        assert builder is task_builder  # Method chaining
        assert builder.task is not None
        assert builder.task.name == "TestTask"
        assert builder.task.description == "Test description"
    
    def test_with_input(self, task_builder):
        """Test adding input data."""
        builder = task_builder.create(
            name="TestTask", 
            description="Test description"
        )
        
        builder.with_input("key1", "value1")
        builder.with_input("key2", "value2")
        
        assert builder.task.input_data["key1"] == "value1"
        assert builder.task.input_data["key2"] == "value2"
    
    def test_with_query(self, task_builder):
        """Test setting query."""
        builder = task_builder.create(
            name="TestTask", 
            description="Test description"
        )
        
        builder.with_query("Test query")
        
        assert builder.task.input_data["query"] == "Test query"
    
    def test_for_agent(self, task_builder):
        """Test assigning to agent."""
        builder = task_builder.create(
            name="TestTask", 
            description="Test description"
        )
        
        builder.for_agent("test-agent-id")
        
        assert builder.task.agent_id == "test-agent-id"
    
    def test_with_priority(self, task_builder):
        """Test setting priority."""
        builder = task_builder.create(
            name="TestTask", 
            description="Test description"
        )
        
        builder.with_priority(TaskPriority.HIGH)
        
        assert builder.task.priority == TaskPriority.HIGH
    
    def test_build(self, task_builder):
        """Test building the task."""
        task = (task_builder
               .create("TestTask", "Test description")
               .with_query("Test query")
               .for_agent("test-agent-id")
               .with_priority(TaskPriority.HIGH)
               .build())
        
        assert isinstance(task, Task)
        assert task.name == "TestTask"
        assert task.description == "Test description"
        assert task.input_data["query"] == "Test query"
        assert task.agent_id == "test-agent-id"
        assert task.priority == TaskPriority.HIGH
    
    @pytest.mark.asyncio
    async def test_save(self, task_builder, mock_registry):
        """Test saving the task."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.save.return_value = "test-id"
        mock_registry.get_repository.return_value = mock_repo
        
        # Build and save task
        task_id = await (task_builder
                        .create("TestTask", "Test description")
                        .with_query("Test query")
                        .save())
        
        assert task_id == "test-id"
        mock_registry.get_repository.assert_called_once_with("task")
        mock_repo.save.assert_called_once()


class TestWorkflowBuilder:
    """Tests for the WorkflowBuilder class."""
    
    @pytest.fixture
    def workflow_builder(self, mock_registry):
        """Create a WorkflowBuilder instance for testing."""
        return WorkflowBuilder(registry=mock_registry)
    
    def test_create_workflow(self, workflow_builder):
        """Test creating a workflow with builder."""
        builder = workflow_builder.create(
            name="TestWorkflow", 
            description="Test description"
        )
        
        assert builder is workflow_builder  # Method chaining
        assert builder.workflow_def is not None
        assert builder.workflow_def.name == "TestWorkflow"
        assert builder.workflow_def.description == "Test description"
    
    def test_add_task(self, workflow_builder):
        """Test adding a task step."""
        builder = workflow_builder.create(
            name="TestWorkflow", 
            description="Test description"
        )
        
        builder.add_task(
            name="Step 1",
            description="First step",
            task_template={
                "name": "Task 1",
                "description": "First task",
                "input_data": {"query": "Test query"}
            }
        )
        
        assert len(builder.workflow_def.steps) == 1
        step_data = builder.workflow_def.steps[0]
        assert step_data["name"] == "Step 1"
        assert step_data["description"] == "First step"
    
    def test_with_context(self, workflow_builder):
        """Test setting initial context."""
        builder = workflow_builder.create(
            name="TestWorkflow", 
            description="Test description"
        )
        
        builder.with_context({"key": "value"})
        
        assert builder.initial_context == {"key": "value"}
    
    def test_build(self, workflow_builder):
        """Test building the workflow."""
        workflow = (workflow_builder
                   .create("TestWorkflow", "Test description")
                   .add_task(
                       name="Step 1",
                       description="First step",
                       task_template={
                           "name": "Task 1",
                           "description": "First task",
                           "input_data": {"query": "Test query"}
                       }
                   )
                   .build())
        
        assert isinstance(workflow, WorkflowDefinition)
        assert workflow.name == "TestWorkflow"
        assert workflow.description == "Test description"
        assert len(workflow.steps) == 1
    
    @pytest.mark.asyncio
    async def test_save(self, workflow_builder, mock_registry):
        """Test saving the workflow."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.save.return_value = "test-id"
        mock_registry.get_repository.return_value = mock_repo
        
        # Build and save workflow
        workflow_id = await (workflow_builder
                            .create("TestWorkflow", "Test description")
                            .add_task(
                                name="Step 1",
                                description="First step",
                                task_template={
                                    "name": "Task 1",
                                    "description": "First task",
                                    "input_data": {"query": "Test query"}
                                }
                            )
                            .save())
        
        assert workflow_id == "test-id"
        mock_registry.get_repository.assert_called_once_with("workflow_definition")
        mock_repo.save.assert_called_once()