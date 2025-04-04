"""Unit tests for EnhancedExecutor."""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

from symphony.agents.base import Agent
from symphony.core.task import Task, TaskStatus
from symphony.execution.workflow_tracker import WorkflowTracker, Workflow, WorkflowStatus
from symphony.execution.enhanced_agent import EnhancedExecutor
from symphony.persistence.repository import Repository


@pytest.fixture
def mock_task_repo():
    """Create a mock task repository."""
    repo = AsyncMock(spec=Repository)
    
    # Setup find_by_id to return a task
    task = Task(
        id="test_task_id",
        name="Test Task",
        description="Test description",
        input_data={"query": "Test query"}
    )
    
    async def mock_find_by_id(id):
        if id == "test_task_id":
            return task
        elif id == "nonexistent_task_id":
            return None
        elif id == "fail_task_id":
            return Task(
                id="fail_task_id",
                name="Fail Task",
                input_data={"query": "fail"}
            )
        return None
        
    repo.find_by_id.side_effect = mock_find_by_id
    
    return repo, task


@pytest.fixture
def mock_workflow_tracker():
    """Create a mock workflow tracker."""
    tracker = AsyncMock(spec=WorkflowTracker)
    
    # Mock add_task_to_workflow
    async def mock_add_task(workflow_id, task_id):
        return True
        
    tracker.add_task_to_workflow.side_effect = mock_add_task
    
    # Mock get_workflow
    async def mock_get_workflow(workflow_id):
        if workflow_id == "test_workflow_id":
            return Workflow(
                id="test_workflow_id",
                name="Test Workflow",
                status=WorkflowStatus.PENDING
            )
        return None
        
    tracker.get_workflow.side_effect = mock_get_workflow
    
    # Mock update_workflow_status
    async def mock_update_status(workflow_id, status, error=None):
        return Workflow(
            id=workflow_id,
            name="Test Workflow",
            status=status,
            error=error
        )
        
    tracker.update_workflow_status.side_effect = mock_update_status
    
    # Mock sync_workflow_status
    async def mock_sync_status(workflow_id):
        return Workflow(
            id=workflow_id,
            name="Test Workflow",
            status=WorkflowStatus.RUNNING
        )
        
    tracker.sync_workflow_status.side_effect = mock_sync_status
    
    return tracker


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
    agent.name = "TestAgent"
    
    return agent


@pytest.fixture
def executor(mock_task_repo, mock_workflow_tracker):
    """Create an enhanced executor with mocks."""
    repo, _ = mock_task_repo
    return EnhancedExecutor(repo, mock_workflow_tracker)


@pytest.mark.asyncio
async def test_execute_task_success(executor, mock_task_repo, mock_agent):
    """Test successful task execution."""
    repo, task = mock_task_repo
    
    # Execute task
    result_task = await executor.execute_task("test_task_id", mock_agent)
    
    # Verify task was marked as running
    repo.update.assert_any_call(task)
    assert task.status == TaskStatus.COMPLETED
    
    # Verify agent was called with correct query
    mock_agent.run.assert_called_once_with("Test query")
    
    # Verify task has correct output
    assert task.output_data.get("result") == "Response to: Test query"
    
    # Verify final task update
    repo.update.assert_called_with(task)


@pytest.mark.asyncio
async def test_execute_task_not_found(executor, mock_task_repo, mock_agent):
    """Test handling of nonexistent task."""
    repo, _ = mock_task_repo
    
    # Try to execute nonexistent task
    with pytest.raises(ValueError, match="Task nonexistent_task_id not found"):
        await executor.execute_task("nonexistent_task_id", mock_agent)
        
    # Verify find_by_id was called with correct ID
    repo.find_by_id.assert_called_with("nonexistent_task_id")


@pytest.mark.asyncio
async def test_execute_task_with_workflow(executor, mock_task_repo, mock_agent, mock_workflow_tracker):
    """Test task execution with workflow association."""
    repo, task = mock_task_repo
    
    # Execute task with workflow
    result_task = await executor.execute_task(
        "test_task_id", 
        mock_agent, 
        workflow_id="test_workflow_id"
    )
    
    # Verify task was added to workflow
    mock_workflow_tracker.add_task_to_workflow.assert_called_once_with(
        "test_workflow_id", "test_task_id"
    )
    
    # Verify workflow status was updated
    mock_workflow_tracker.update_workflow_status.assert_called_once_with(
        "test_workflow_id", WorkflowStatus.RUNNING
    )
    
    # Verify workflow status was synced after execution (called at least once)
    assert mock_workflow_tracker.sync_workflow_status.call_count >= 1
    mock_workflow_tracker.sync_workflow_status.assert_any_call("test_workflow_id")


@pytest.mark.asyncio
async def test_execute_task_with_hooks(executor, mock_task_repo, mock_agent):
    """Test task execution with pre and post hooks."""
    repo, task = mock_task_repo
    
    # Create hooks
    pre_hook_called = False
    post_hook_called = False
    
    def pre_execution_hook(task, agent):
        nonlocal pre_hook_called
        pre_hook_called = True
        assert task.id == "test_task_id"
        assert agent.name == "TestAgent"
    
    def post_execution_hook(task, agent, result):
        nonlocal post_hook_called
        post_hook_called = True
        assert task.id == "test_task_id"
        assert agent.name == "TestAgent"
        assert result == "Response to: Test query"
    
    # Execute task with hooks
    result_task = await executor.execute_task(
        "test_task_id", 
        mock_agent,
        pre_execution_hook=pre_execution_hook,
        post_execution_hook=post_execution_hook
    )
    
    # Verify hooks were called
    assert pre_hook_called
    assert post_hook_called


@pytest.mark.asyncio
async def test_execute_task_with_failing_hooks(executor, mock_task_repo, mock_agent):
    """Test task execution with hooks that raise exceptions."""
    repo, task = mock_task_repo
    
    # Create hooks that raise exceptions
    def failing_pre_hook(task, agent):
        raise Exception("Pre-hook error")
    
    def failing_post_hook(task, agent, result):
        raise Exception("Post-hook error")
    
    # Execute task with failing hooks
    result_task = await executor.execute_task(
        "test_task_id", 
        mock_agent,
        pre_execution_hook=failing_pre_hook,
        post_execution_hook=failing_post_hook
    )
    
    # Task should still complete successfully
    assert result_task.status == TaskStatus.COMPLETED
    assert result_task.output_data.get("result") == "Response to: Test query"


@pytest.mark.asyncio
async def test_execute_task_with_context(executor, mock_task_repo, mock_agent):
    """Test task execution with context data."""
    repo, task = mock_task_repo
    
    # Create context
    context = {
        "session_id": "test_session",
        "user_id": "test_user",
        "custom_data": {"key": "value"}
    }
    
    # Execute task with context
    result_task = await executor.execute_task(
        "test_task_id", 
        mock_agent,
        context=context,
        workflow_id="test_workflow_id"
    )
    
    # Verify context was included in output
    assert "context" in result_task.output_data
    assert result_task.output_data["context"]["session_id"] == "test_session"
    assert result_task.output_data["context"]["user_id"] == "test_user"
    assert result_task.output_data["context"]["custom_data"]["key"] == "value"
    
    # Verify task metadata was added to context
    assert result_task.output_data["context"]["task_id"] == "test_task_id"
    assert result_task.output_data["context"]["task_name"] == "Test Task"
    assert result_task.output_data["context"]["workflow_id"] == "test_workflow_id"


@pytest.mark.asyncio
async def test_execute_task_failure(executor, mock_task_repo, mock_agent):
    """Test task execution failure."""
    repo, _ = mock_task_repo
    
    # Execute failing task
    result_task = await executor.execute_task("fail_task_id", mock_agent)
    
    # Verify task was marked as failed
    assert result_task.status == TaskStatus.FAILED
    assert result_task.error is not None
    assert "Test failure" in result_task.error
    
    # Verify error details were captured
    assert "error_details" in result_task.output_data
    assert result_task.output_data["error_details"]["error"] == "Test failure"
    assert "traceback" in result_task.output_data["error_details"]


@pytest.mark.asyncio
async def test_batch_execute(executor, mock_task_repo, mock_agent):
    """Test batch execution of tasks."""
    repo, _ = mock_task_repo
    
    # Create a list of tasks
    tasks = [
        ("test_task_id", mock_agent),
        ("test_task_id", mock_agent),
        ("test_task_id", mock_agent)
    ]
    
    # Spy on execute_task
    original_execute_task = executor.execute_task
    execute_task_spy = AsyncMock(side_effect=original_execute_task)
    executor.execute_task = execute_task_spy
    
    # Batch execute
    results = await executor.batch_execute(tasks, max_concurrent=2)
    
    # Verify execute_task was called for each task
    assert execute_task_spy.call_count == 3
    
    # Verify correct parameters were passed
    for i, (task_id, agent) in enumerate(tasks):
        assert execute_task_spy.call_args_list[i][0][0] == task_id
        assert execute_task_spy.call_args_list[i][0][1] == agent
    
    # Verify results
    assert len(results) == 3
    for result in results:
        assert result.status == TaskStatus.COMPLETED
        
    # Test with empty tasks list
    empty_results = await executor.batch_execute([])
    assert empty_results == []
    
    # Test with workflow_id
    workflow_results = await executor.batch_execute(
        tasks, 
        workflow_id="test_workflow_id",
        max_concurrent=3
    )
    
    # Verify workflow_id was passed to execute_task
    for i in range(len(tasks)):
        assert execute_task_spy.call_args_list[3+i][0][2] == "test_workflow_id"
    
    assert len(workflow_results) == 3


@pytest.mark.asyncio
async def test_execute_with_retry_success(executor, mock_task_repo, mock_agent):
    """Test execution with retry that succeeds."""
    repo, task = mock_task_repo
    
    # Spy on execute_task
    original_execute_task = executor.execute_task
    execute_task_spy = AsyncMock(side_effect=original_execute_task)
    executor.execute_task = execute_task_spy
    
    # Execute with retry
    result_task = await executor.execute_with_retry(
        "test_task_id", 
        mock_agent,
        max_retries=3,
        retry_delay=0.01
    )
    
    # Verify execute_task was called once (since it succeeded)
    execute_task_spy.assert_called_once_with("test_task_id", mock_agent, None)
    
    # Verify result
    assert result_task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_execute_with_retry_failure(executor, mock_task_repo, mock_agent):
    """Test execution with retry that fails."""
    repo, _ = mock_task_repo
    
    # Spy on execute_task
    original_execute_task = executor.execute_task
    
    # Create a mock execute_task that fails multiple times
    fail_count = 0
    
    async def failing_execute_task(task_id, agent, workflow_id=None):
        nonlocal fail_count
        fail_count += 1
        
        task = await repo.find_by_id(task_id)
        task.mark_failed(f"Failed attempt {fail_count}")
        return task
        
    execute_task_spy = AsyncMock(side_effect=failing_execute_task)
    executor.execute_task = execute_task_spy
    
    # Execute with retry
    result_task = await executor.execute_with_retry(
        "fail_task_id", 
        mock_agent,
        max_retries=2,
        retry_delay=0.01
    )
    
    # Verify execute_task was called multiple times
    assert execute_task_spy.call_count == 3  # Initial + 2 retries
    
    # Verify result
    assert result_task.status == TaskStatus.FAILED
    assert "Failed after" in result_task.error
    
    # Test with direct exception
    async def exception_execute_task(task_id, agent, workflow_id=None):
        raise Exception("Direct exception")
        
    executor.execute_task = AsyncMock(side_effect=exception_execute_task)
    
    # Execute with retry
    result_task = await executor.execute_with_retry(
        "fail_task_id", 
        mock_agent,
        max_retries=1,
        retry_delay=0.01,
        workflow_id="test_workflow_id"
    )
    
    # Verify failed result
    assert result_task.status == TaskStatus.FAILED
    assert "Failed after" in result_task.error
    
    # Test nonexistent task in retry handler
    repo.find_by_id.return_value = None
    result_task = await executor.execute_with_retry(
        "nonexistent_task_id", 
        mock_agent,
        max_retries=1,
        retry_delay=0.01
    )
    
    # Should return None as the task wasn't found
    assert result_task is None