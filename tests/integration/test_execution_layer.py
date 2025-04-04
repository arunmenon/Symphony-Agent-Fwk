"""Integration tests for Symphony execution layer."""

import asyncio
import os
import pytest
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

from symphony.persistence.memory_repository import InMemoryRepository
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.core.task import Task, TaskStatus
from symphony.core.registry import ServiceRegistry
from symphony.agents.base import Agent
from symphony.execution.workflow_tracker import Workflow, WorkflowStatus
from symphony.execution.enhanced_agent import EnhancedExecutor
from symphony.execution.router import TaskRouter, RoutingStrategy


class MockAgent(Agent):
    """Mock agent for testing."""
    
    def __init__(self, name="TestAgent", system_prompt="Test prompt"):
        self.name = name
        self.system_prompt = system_prompt
        self.response_map = {}
    
    def add_response(self, query, response):
        """Add a query-response pair to the agent."""
        self.response_map[query] = response
    
    async def run(self, query):
        """Mock run method."""
        if query in self.response_map:
            return self.response_map[query]
        elif "fail" in query.lower():
            raise Exception("Mock failure")
        return f"Default response to: {query}"


@pytest.fixture
def setup_registry():
    """Set up registry with all required components."""
    # Get registry instance
    registry = ServiceRegistry.get_instance()
    
    # Clear existing registrations
    registry.repositories = {}
    registry.services = {}
    
    # Create repositories
    agent_config_repo = InMemoryRepository(AgentConfig)
    task_repo = InMemoryRepository(Task)
    workflow_repo = InMemoryRepository(Workflow)
    
    # Register repositories
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    
    # Create mock agents
    math_agent = MockAgent(name="MathAgent", system_prompt="You are a math expert")
    math_agent.add_response("Solve 2+2", "The answer is 4")
    
    writing_agent = MockAgent(name="WritingAgent", system_prompt="You are a writer")
    writing_agent.add_response("Write a poem", "Roses are red, violets are blue")
    
    # Create agent configs
    math_config = AgentConfig(
        id="math_config",
        name="MathAgent",
        role="Mathematics Expert",
        instruction_template="You are a math expert",
        capabilities=AgentCapabilities(
            expertise=["mathematics", "algebra"]
        )
    )
    
    writing_config = AgentConfig(
        id="writing_config",
        name="WritingAgent",
        role="Content Writer",
        instruction_template="You are a writer",
        capabilities=AgentCapabilities(
            expertise=["writing", "creative"]
        )
    )
    
    # Save configs
    asyncio.run(agent_config_repo.save(math_config))
    asyncio.run(agent_config_repo.save(writing_config))
    
    return registry, math_agent, writing_agent


@pytest.mark.asyncio
async def test_end_to_end_workflow(setup_registry):
    """Test end-to-end workflow with execution components."""
    registry, math_agent, writing_agent = setup_registry
    
    # Get services
    workflow_tracker = registry.get_workflow_tracker()
    executor = registry.get_enhanced_executor()
    task_manager = registry.get_task_manager()
    router = registry.get_task_router(RoutingStrategy.CAPABILITY_MATCH)
    
    # Create a workflow
    workflow = await workflow_tracker.create_workflow(
        name="Test Workflow",
        description="An integration test workflow"
    )
    
    # Create tasks
    math_task = await task_manager.create_task(
        name="Math Task",
        description="A math problem",
        input_data={"query": "Solve 2+2"},
        tags=["mathematics"]
    )
    
    writing_task = await task_manager.create_task(
        name="Writing Task",
        description="A writing assignment",
        input_data={"query": "Write a poem"},
        tags=["writing"]
    )
    
    # Add tasks to workflow
    await workflow_tracker.add_task_to_workflow(workflow.id, math_task.id)
    await workflow_tracker.add_task_to_workflow(workflow.id, writing_task.id)
    
    # Route tasks
    math_agent_id = await router.route_task(math_task)
    writing_agent_id = await router.route_task(writing_task)
    
    # Verify routing
    assert math_agent_id == "math_config"
    assert writing_agent_id == "writing_config"
    
    # Execute tasks
    math_result = await executor.execute_task(math_task.id, math_agent, workflow.id)
    writing_result = await executor.execute_task(writing_task.id, writing_agent, workflow.id)
    
    # Verify results
    assert math_result.status == TaskStatus.COMPLETED
    assert math_result.output_data.get("result") == "The answer is 4"
    
    assert writing_result.status == TaskStatus.COMPLETED
    assert writing_result.output_data.get("result") == "Roses are red, violets are blue"
    
    # Check workflow status
    workflow_status = await workflow_tracker.compute_workflow_status(workflow.id)
    assert workflow_status == WorkflowStatus.COMPLETED


@pytest.mark.asyncio
async def test_concurrent_execution(setup_registry):
    """Test concurrent execution of tasks in a workflow."""
    registry, math_agent, writing_agent = setup_registry
    
    # Get services
    workflow_tracker = registry.get_workflow_tracker()
    executor = registry.get_enhanced_executor()
    task_manager = registry.get_task_manager()
    
    # Create a workflow
    workflow = await workflow_tracker.create_workflow(
        name="Concurrent Workflow",
        description="A workflow for testing concurrent execution"
    )
    
    # Create multiple tasks
    tasks = []
    for i in range(5):
        task = await task_manager.create_task(
            name=f"Task {i+1}",
            description=f"Task {i+1} for concurrent execution",
            input_data={"query": f"Process task {i+1}"}
        )
        tasks.append(task)
        await workflow_tracker.add_task_to_workflow(workflow.id, task.id)
    
    # Execute tasks concurrently
    task_agent_pairs = [(task.id, math_agent) for task in tasks]
    results = await executor.batch_execute(
        task_agent_pairs,
        workflow_id=workflow.id,
        max_concurrent=3
    )
    
    # Verify all tasks were executed
    assert len(results) == 5
    for result in results:
        assert result.status == TaskStatus.COMPLETED
    
    # Check workflow status
    workflow_status = await workflow_tracker.compute_workflow_status(workflow.id)
    assert workflow_status == WorkflowStatus.COMPLETED


@pytest.mark.asyncio
async def test_failure_handling(setup_registry):
    """Test handling of task failures in a workflow."""
    registry, math_agent, writing_agent = setup_registry
    
    # Get services
    workflow_tracker = registry.get_workflow_tracker()
    executor = registry.get_enhanced_executor()
    task_manager = registry.get_task_manager()
    
    # Create a workflow
    workflow = await workflow_tracker.create_workflow(
        name="Failure Workflow",
        description="A workflow for testing failure handling"
    )
    
    # Create a failing task
    fail_task = await task_manager.create_task(
        name="Fail Task",
        description="A task that will fail",
        input_data={"query": "This will fail"}
    )
    
    # Add task to workflow
    await workflow_tracker.add_task_to_workflow(workflow.id, fail_task.id)
    
    # Add a special response that triggers a failure
    math_agent.add_response("This will fail", None)  # None will cause the run method to raise an exception
    
    # Execute task with retry
    result_task = await executor.execute_with_retry(
        fail_task.id,
        math_agent,
        max_retries=2,
        retry_delay=0.01,
        workflow_id=workflow.id
    )
    
    # Verify task failed after retries
    assert result_task.status == TaskStatus.FAILED
    assert "failed" in result_task.error.lower()
    
    # Check workflow status
    workflow_status = await workflow_tracker.compute_workflow_status(workflow.id)
    assert workflow_status == WorkflowStatus.FAILED


@pytest.mark.asyncio
async def test_mixed_success_workflow(setup_registry):
    """Test workflow with mix of successful and failed tasks."""
    registry, math_agent, writing_agent = setup_registry
    
    # Get services
    workflow_tracker = registry.get_workflow_tracker()
    executor = registry.get_enhanced_executor()
    task_manager = registry.get_task_manager()
    
    # Create a workflow
    workflow = await workflow_tracker.create_workflow(
        name="Mixed Workflow",
        description="A workflow with mix of success and failure"
    )
    
    # Create a successful task
    success_task = await task_manager.create_task(
        name="Success Task",
        description="A task that will succeed",
        input_data={"query": "Solve 2+2"}
    )
    
    # Create a failing task
    fail_task = await task_manager.create_task(
        name="Fail Task",
        description="A task that will fail",
        input_data={"query": "This will fail"}
    )
    
    # Add tasks to workflow
    await workflow_tracker.add_task_to_workflow(workflow.id, success_task.id)
    await workflow_tracker.add_task_to_workflow(workflow.id, fail_task.id)
    
    # Execute tasks
    success_result = await executor.execute_task(success_task.id, math_agent, workflow.id)
    fail_result = await executor.execute_task(fail_task.id, math_agent, workflow.id)
    
    # Verify individual results
    assert success_result.status == TaskStatus.COMPLETED
    assert fail_result.status == TaskStatus.FAILED
    
    # Check workflow status (should be FAILED if any task fails)
    workflow_status = await workflow_tracker.compute_workflow_status(workflow.id)
    assert workflow_status == WorkflowStatus.FAILED