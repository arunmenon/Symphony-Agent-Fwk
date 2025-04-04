"""Unit tests for TaskManager."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from symphony.core.task_manager import TaskManager
from symphony.core.task import Task, TaskStatus
from symphony.agents.base import Agent
from symphony.persistence.repository import Repository


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = AsyncMock(spec=Repository)
    
    # Setup find_by_id to return a task
    test_task = Task(
        id="test_task_id",
        name="Test Task",
        description="A test task",
        input_data={"query": "Test query"}
    )
    
    async def mock_find_by_id(id):
        if id == "test_task_id":
            return test_task
        return None
        
    repo.find_by_id.side_effect = mock_find_by_id
    
    # Setup save to return the ID
    async def mock_save(task):
        return task.id
        
    repo.save.side_effect = mock_save
    
    # Setup find_all to return a list of tasks
    async def mock_find_all(filter_criteria=None):
        if not filter_criteria:
            return [test_task]
        return []
        
    repo.find_all.side_effect = mock_find_all
    
    return repo, test_task


@pytest.fixture
def task_manager(mock_repository):
    """Create a task manager with mock repository."""
    repo, _ = mock_repository
    return TaskManager(repo)


@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = AsyncMock(spec=Agent)
    
    # Mock run method
    async def mock_run(query):
        if query == "fail":
            raise Exception("Test failure")
        return f"Response to: {query}"
        
    agent.run.side_effect = mock_run
    
    return agent


@pytest.mark.asyncio
async def test_create_task(task_manager, mock_repository):
    """Test creating a task."""
    repo, _ = mock_repository
    
    # Create task
    task = await task_manager.create_task(
        name="New Task",
        description="A new task",
        input_data={"query": "New query"}
    )
    
    # Verify repository was called
    repo.save.assert_called_once()
    
    # Verify task properties
    assert task.name == "New Task"
    assert task.description == "A new task"
    assert task.input_data["query"] == "New query"
    assert task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_get_task_existing(task_manager, mock_repository):
    """Test getting an existing task."""
    repo, task = mock_repository
    
    # Get task
    found_task = await task_manager.get_task("test_task_id")
    
    # Verify repository was called
    repo.find_by_id.assert_called_once_with("test_task_id")
    
    # Verify task
    assert found_task is task


@pytest.mark.asyncio
async def test_get_task_nonexistent(task_manager):
    """Test getting a non-existent task."""
    # Get non-existent task
    found_task = await task_manager.get_task("nonexistent_id")
    
    # Verify task is None
    assert found_task is None


@pytest.mark.asyncio
async def test_execute_task_success(task_manager, mock_repository, mock_agent):
    """Test executing a task successfully."""
    repo, task = mock_repository
    
    # Execute task
    result_task = await task_manager.execute_task("test_task_id", mock_agent)
    
    # Verify repository was called
    repo.find_by_id.assert_called_with("test_task_id")
    
    # Verify agent was called
    mock_agent.run.assert_called_once_with("Test query")
    
    # Verify task status was updated
    assert result_task.status == TaskStatus.COMPLETED
    assert result_task.output_data["result"] == "Response to: Test query"
    
    # Verify task was updated in repository
    repo.update.assert_called_with(task)


@pytest.mark.asyncio
async def test_execute_task_failure(task_manager, mock_repository, mock_agent):
    """Test executing a task with a failure."""
    repo, task = mock_repository
    
    # Modify task to cause failure
    task.input_data["query"] = "fail"
    
    # Execute task
    result_task = await task_manager.execute_task("test_task_id", mock_agent)
    
    # Verify task status was updated
    assert result_task.status == TaskStatus.FAILED
    assert result_task.error is not None
    assert "Test failure" in result_task.error
    
    # Verify task was updated in repository
    repo.update.assert_called_with(task)


@pytest.mark.asyncio
async def test_execute_task_not_found(task_manager, mock_agent):
    """Test executing a non-existent task."""
    # Execute non-existent task
    with pytest.raises(ValueError, match="Task nonexistent_id not found"):
        await task_manager.execute_task("nonexistent_id", mock_agent)


@pytest.mark.asyncio
async def test_find_tasks(task_manager, mock_repository):
    """Test finding tasks."""
    repo, task = mock_repository
    
    # Find all tasks
    tasks = await task_manager.find_tasks()
    
    # Verify repository was called
    repo.find_all.assert_called_once_with(None)
    
    # Verify tasks
    assert len(tasks) == 1
    assert tasks[0] is task
    
    # Find tasks with filter
    filter_criteria = {"status": TaskStatus.PENDING}
    await task_manager.find_tasks(filter_criteria)
    
    # Verify repository was called with filter
    repo.find_all.assert_called_with(filter_criteria)