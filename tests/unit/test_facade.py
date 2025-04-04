"""Tests for Symphony Facade classes.

This module contains tests for the Symphony Facade classes that provide
domain-specific interfaces for working with Symphony components.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from symphony.core.registry import ServiceRegistry
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.core.task import Task, TaskStatus, TaskPriority
from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.execution.workflow_tracker import Workflow, WorkflowStatus

from symphony.facade.agents import AgentFacade
from symphony.facade.tasks import TaskFacade
from symphony.facade.workflows import WorkflowFacade


@pytest.fixture
def mock_registry():
    """Create a mock registry for testing."""
    registry = MagicMock(spec=ServiceRegistry)
    registry.repositories = {}
    return registry


class TestAgentFacade:
    """Tests for the AgentFacade class."""
    
    @pytest.fixture
    def agent_facade(self, mock_registry):
        """Create an AgentFacade instance for testing."""
        return AgentFacade(registry=mock_registry)
    
    @pytest.mark.asyncio
    async def test_create_agent(self, agent_facade):
        """Test creating an agent configuration."""
        agent = await agent_facade.create_agent(
            name="TestAgent",
            role="Test Role",
            instruction_template="Test instruction",
            capabilities={"expertise": ["test"]}
        )
        
        assert isinstance(agent, AgentConfig)
        assert agent.name == "TestAgent"
        assert agent.role == "Test Role"
        assert agent.instruction_template == "Test instruction"
        assert agent.capabilities.expertise == ["test"]
    
    @pytest.mark.asyncio
    async def test_save_agent(self, agent_facade, mock_registry):
        """Test saving an agent configuration."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.save.return_value = "test-id"
        mock_registry.get_repository.return_value = mock_repo
        
        # Create agent
        agent = await agent_facade.create_agent(
            name="TestAgent",
            role="Test Role",
            instruction_template="Test instruction"
        )
        
        # Save agent
        agent_id = await agent_facade.save_agent(agent)
        
        assert agent_id == "test-id"
        mock_registry.get_repository.assert_called_once_with("agent_config")
        mock_repo.save.assert_called_once_with(agent)
    
    @pytest.mark.asyncio
    async def test_get_agent(self, agent_facade, mock_registry):
        """Test getting an agent configuration."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_agent = AgentConfig(
            name="TestAgent",
            role="Test Role",
            instruction_template="Test instruction"
        )
        mock_repo.find_by_id.return_value = mock_agent
        mock_registry.get_repository.return_value = mock_repo
        
        # Get agent
        agent = await agent_facade.get_agent("test-id")
        
        assert agent is mock_agent
        mock_registry.get_repository.assert_called_once_with("agent_config")
        mock_repo.find_by_id.assert_called_once_with("test-id")


class TestTaskFacade:
    """Tests for the TaskFacade class."""
    
    @pytest.fixture
    def task_facade(self, mock_registry):
        """Create a TaskFacade instance for testing."""
        return TaskFacade(registry=mock_registry)
    
    @pytest.mark.asyncio
    async def test_create_task(self, task_facade):
        """Test creating a task."""
        task = await task_facade.create_task(
            name="TestTask",
            description="Test description",
            input_data={"query": "Test query"},
            agent_id="test-agent-id",
            priority=TaskPriority.HIGH
        )
        
        assert isinstance(task, Task)
        assert task.name == "TestTask"
        assert task.description == "Test description"
        assert task.input_data == {"query": "Test query"}
        assert task.agent_id == "test-agent-id"
        assert task.priority == TaskPriority.HIGH
    
    @pytest.mark.asyncio
    async def test_save_task(self, task_facade, mock_registry):
        """Test saving a task."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.save.return_value = "test-id"
        mock_registry.get_repository.return_value = mock_repo
        
        # Create task
        task = await task_facade.create_task(
            name="TestTask",
            description="Test description",
            input_data={"query": "Test query"}
        )
        
        # Save task
        task_id = await task_facade.save_task(task)
        
        assert task_id == "test-id"
        mock_registry.get_repository.assert_called_once_with("task")
        mock_repo.save.assert_called_once_with(task)
    
    @pytest.mark.asyncio
    async def test_execute_task(self, task_facade, mock_registry):
        """Test executing a task."""
        # Mock executor
        mock_executor = AsyncMock()
        mock_registry.get_enhanced_executor.return_value = mock_executor
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_task = Task(
            id="test-id",
            name="TestTask",
            description="Test description",
            input_data={"query": "Test query"},
            status=TaskStatus.COMPLETED
        )
        mock_repo.find_by_id.return_value = mock_task
        mock_repo.save.return_value = "test-id"
        mock_registry.get_repository.return_value = mock_repo
        
        # Create task
        task = await task_facade.create_task(
            name="TestTask",
            description="Test description",
            input_data={"query": "Test query"}
        )
        
        # Execute task
        result = await task_facade.execute_task(task)
        
        assert result is mock_task
        mock_executor.execute_task.assert_called_once()


class TestWorkflowFacade:
    """Tests for the WorkflowFacade class."""
    
    @pytest.fixture
    def workflow_facade(self, mock_registry):
        """Create a WorkflowFacade instance for testing."""
        return WorkflowFacade(registry=mock_registry)
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, workflow_facade):
        """Test creating a workflow definition."""
        workflow = await workflow_facade.create_workflow(
            name="TestWorkflow",
            description="Test description",
            metadata={"key": "value"}
        )
        
        assert isinstance(workflow, WorkflowDefinition)
        assert workflow.name == "TestWorkflow"
        assert workflow.description == "Test description"
        assert workflow.metadata == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_save_workflow(self, workflow_facade, mock_registry):
        """Test saving a workflow definition."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.save.return_value = "test-id"
        mock_registry.get_repository.return_value = mock_repo
        
        # Create workflow
        workflow = await workflow_facade.create_workflow(
            name="TestWorkflow",
            description="Test description"
        )
        
        # Save workflow
        workflow_id = await workflow_facade.save_workflow(workflow)
        
        assert workflow_id == "test-id"
        mock_registry.get_repository.assert_called_once_with("workflow_definition")
        mock_repo.save.assert_called_once_with(workflow)
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self, workflow_facade, mock_registry):
        """Test executing a workflow."""
        # Mock engine
        mock_engine = AsyncMock()
        mock_registry.get_service.return_value = mock_engine
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.save.return_value = "test-id"
        mock_registry.get_repository.return_value = mock_repo
        
        # Mock workflow result
        mock_workflow = Workflow(
            id="test-execution-id",
            name="TestWorkflow",
            status=WorkflowStatus.COMPLETED
        )
        mock_engine.execute_workflow.return_value = mock_workflow
        
        # Create workflow
        workflow = await workflow_facade.create_workflow(
            name="TestWorkflow",
            description="Test description"
        )
        
        # Execute workflow
        result = await workflow_facade.execute_workflow(workflow)
        
        assert result is mock_workflow
        mock_engine.execute_workflow.assert_called_once()