"""Unit tests for the workflow step implementations."""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from symphony.core.task import Task, TaskStatus
from symphony.core.agent_factory import AgentFactory
from symphony.core.task_manager import TaskManager
from symphony.execution.enhanced_agent import EnhancedExecutor
from symphony.execution.router import TaskRouter
from symphony.orchestration.workflow_definition import WorkflowContext, StepResult
from symphony.orchestration.steps import (
    TaskStep, 
    ConditionalStep,
    ParallelStep,
    LoopStep
)


@pytest.fixture
def context():
    """Create a workflow context for testing."""
    # Create mock services
    mock_task_manager = AsyncMock(spec=TaskManager)
    mock_agent_factory = AsyncMock(spec=AgentFactory)
    mock_executor = AsyncMock(spec=EnhancedExecutor)
    mock_router = AsyncMock(spec=TaskRouter)
    
    # Create mock registry
    mock_registry = MagicMock()
    mock_registry.get_service.side_effect = lambda name: {
        "task_manager": mock_task_manager,
        "agent_factory": mock_agent_factory,
        "enhanced_executor": mock_executor,
        "task_router": mock_router,
    }.get(name)
    
    # Create context
    context = WorkflowContext(
        workflow_id="test_workflow_id",
        data={
            "test_key": "test_value",
            "condition_true": True,
            "condition_false": False
        },
        service_registry=mock_registry
    )
    
    # Setup mock task_manager.create_task
    async def mock_create_task(**kwargs):
        return Task(
            id="test_task_id",
            name=kwargs.get("name", "Test Task"),
            description=kwargs.get("description", ""),
            input_data=kwargs.get("input_data", {})
        )
    mock_task_manager.create_task.side_effect = mock_create_task
    
    # Setup mock agent_factory.create_agent_from_id
    async def mock_create_agent(**kwargs):
        mock_agent = AsyncMock()
        mock_agent.name = "Test Agent"
        mock_agent.run.return_value = "Test result"
        return mock_agent
    mock_agent_factory.create_agent_from_id.side_effect = mock_create_agent
    
    # Setup mock router.route_task
    mock_router.route_task.return_value = asyncio.Future()
    mock_router.route_task.return_value.set_result("routed_agent_id")
    
    # Setup mock executor.execute_task
    async def mock_execute_task(task_id, agent, **kwargs):
        task = Task(
            id=task_id,
            name="Executed Task",
            status=TaskStatus.COMPLETED,
            output_data={"result": "Test execution result"}
        )
        if task_id == "fail_task_id":
            task.status = TaskStatus.FAILED
            task.error = "Task execution failed"
        return task
    mock_executor.execute_task.side_effect = mock_execute_task
    
    return context


class TestTaskStep:
    """Tests for TaskStep class."""
    
    def test_task_step_init(self):
        """Test initializing a task step."""
        step = TaskStep(
            name="Test Step",
            description="Test description",
            task_template={
                "name": "Test Task",
                "input_data": {"query": "Test query"}
            },
            agent_id="test_agent_id"
        )
        
        assert step.name == "Test Step"
        assert step.description == "Test description"
        assert step.task_template == {
            "name": "Test Task",
            "input_data": {"query": "Test query"}
        }
        assert step.agent_id == "test_agent_id"
        
    def test_task_step_to_dict(self):
        """Test converting task step to dictionary."""
        step = TaskStep(
            name="Test Step",
            description="Test description",
            task_template={
                "name": "Test Task",
                "input_data": {"query": "Test query"}
            },
            agent_id="test_agent_id"
        )
        
        data = step.to_dict()
        
        assert data["type"] == "TaskStep"
        assert data["name"] == "Test Step"
        assert data["description"] == "Test description"
        assert data["task_template"] == {
            "name": "Test Task",
            "input_data": {"query": "Test query"}
        }
        assert data["agent_id"] == "test_agent_id"
        
    def test_task_step_from_dict(self):
        """Test creating task step from dictionary."""
        data = {
            "id": "test_id",
            "name": "Test Step",
            "description": "Test description",
            "task_template": {
                "name": "Test Task",
                "input_data": {"query": "Test query"}
            },
            "agent_id": "test_agent_id"
        }
        
        step = TaskStep.from_dict(data)
        
        assert step.name == "Test Step"
        assert step.description == "Test description"
        assert step.task_template == {
            "name": "Test Task",
            "input_data": {"query": "Test query"}
        }
        assert step.agent_id == "test_agent_id"
        
    @pytest.mark.asyncio
    async def test_task_step_execute_with_agent_id(self, context):
        """Test executing task step with agent ID."""
        # Create step
        step = TaskStep(
            name="Test Step",
            task_template={
                "name": "Test Task",
                "input_data": {"query": "Test query"}
            },
            agent_id="test_agent_id"
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify services were called correctly
        task_manager = context.get_service("task_manager")
        agent_factory = context.get_service("agent_factory")
        executor = context.get_service("enhanced_executor")
        
        task_manager.create_task.assert_called_once()
        agent_factory.create_agent_from_id.assert_called_once_with("test_agent_id")
        executor.execute_task.assert_called_once()
        
        # Verify result
        assert result.success is True
        assert result.task_id == "test_task_id"
        assert "result" in result.output
        
        # Verify context was updated
        assert context.get(f"step.{step.id}.result") == "Test execution result"
        assert context.get(f"step.{step.id}.task_id") == "test_task_id"
        
    @pytest.mark.asyncio
    async def test_task_step_execute_with_router(self, context):
        """Test executing task step with router for agent selection."""
        # Create step
        step = TaskStep(
            name="Test Step",
            task_template={
                "name": "Test Task",
                "input_data": {"query": "Test query"}
            }
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify router was called
        router = context.get_service("task_router")
        router.route_task.assert_called_once()
        
        # Verify agent was created from routed ID
        agent_factory = context.get_service("agent_factory")
        agent_factory.create_agent_from_id.assert_called_once_with("routed_agent_id")
        
        # Verify result
        assert result.success is True
        
    @pytest.mark.asyncio
    async def test_task_step_execute_failure(self, context):
        """Test handling task execution failure."""
        # Create step
        step = TaskStep(
            name="Test Step",
            task_template={
                "name": "Test Task",
                "input_data": {"query": "Test query"}
            },
            agent_id="test_agent_id"
        )
        
        # Make execute_task return a failed task
        executor = context.get_service("enhanced_executor")
        
        original_execute_task = executor.execute_task
        
        async def failing_execute_task(*args, **kwargs):
            task = await original_execute_task(*args, **kwargs)
            task.status = TaskStatus.FAILED
            task.error = "Test failure"
            return task
            
        executor.execute_task.side_effect = failing_execute_task
        
        # Execute step
        result = await step.execute(context)
        
        # Verify result
        assert result.success is False
        assert result.error == "Test failure"
        
    @pytest.mark.asyncio
    async def test_task_step_execute_exception(self, context):
        """Test handling exceptions during execution."""
        # Create step
        step = TaskStep(
            name="Test Step",
            task_template={
                "name": "Test Task",
                "input_data": {"query": "Test query"}
            },
            agent_id="test_agent_id"
        )
        
        # Make create_task raise an exception
        task_manager = context.get_service("task_manager")
        task_manager.create_task.side_effect = Exception("Test exception")
        
        # Execute step
        result = await step.execute(context)
        
        # Verify result
        assert result.success is False
        assert "Task execution error" in result.error
        assert "Test exception" in result.error


class TestConditionalStep:
    """Tests for ConditionalStep class."""
    
    def test_conditional_step_init(self):
        """Test initializing a conditional step."""
        if_branch = TaskStep(
            name="If Branch",
            task_template={"name": "If Task"}
        )
        else_branch = TaskStep(
            name="Else Branch",
            task_template={"name": "Else Task"}
        )
        
        step = ConditionalStep(
            name="Conditional Step",
            description="Test conditional",
            condition="test_condition",
            if_branch=if_branch,
            else_branch=else_branch
        )
        
        assert step.name == "Conditional Step"
        assert step.description == "Test conditional"
        assert step.condition == "test_condition"
        assert step.if_branch is if_branch
        assert step.else_branch is else_branch
        
    def test_conditional_step_to_dict(self):
        """Test converting conditional step to dictionary."""
        if_branch = TaskStep(
            name="If Branch",
            task_template={"name": "If Task"}
        )
        else_branch = TaskStep(
            name="Else Branch",
            task_template={"name": "Else Task"}
        )
        
        step = ConditionalStep(
            name="Conditional Step",
            description="Test conditional",
            condition="test_condition",
            if_branch=if_branch,
            else_branch=else_branch
        )
        
        data = step.to_dict()
        
        assert data["type"] == "ConditionalStep"
        assert data["name"] == "Conditional Step"
        assert data["description"] == "Test conditional"
        assert data["condition"] == "test_condition"
        assert data["if_branch"]["type"] == "TaskStep"
        assert data["if_branch"]["name"] == "If Branch"
        assert data["else_branch"]["type"] == "TaskStep"
        assert data["else_branch"]["name"] == "Else Branch"
        
    def test_conditional_step_from_dict(self):
        """Test creating conditional step from dictionary."""
        if_branch_data = {
            "type": "TaskStep",
            "name": "If Branch",
            "task_template": {"name": "If Task"}
        }
        else_branch_data = {
            "type": "TaskStep",
            "name": "Else Branch",
            "task_template": {"name": "Else Task"}
        }
        
        data = {
            "id": "test_id",
            "name": "Conditional Step",
            "description": "Test conditional",
            "condition": "test_condition",
            "if_branch": if_branch_data,
            "else_branch": else_branch_data
        }
        
        step = ConditionalStep.from_dict(data)
        
        assert step.name == "Conditional Step"
        assert step.description == "Test conditional"
        assert step.condition == "test_condition"
        assert isinstance(step.if_branch, TaskStep)
        assert step.if_branch.name == "If Branch"
        assert isinstance(step.else_branch, TaskStep)
        assert step.else_branch.name == "Else Branch"
        
    @pytest.mark.asyncio
    async def test_conditional_step_execute_true_condition(self, context):
        """Test executing conditional step with true condition."""
        # Create mock branches
        if_branch = AsyncMock()
        if_branch.execute.return_value = StepResult(success=True, output={"result": "If result"})
        
        else_branch = AsyncMock()
        else_branch.execute.return_value = StepResult(success=True, output={"result": "Else result"})
        
        # Create step
        step = ConditionalStep(
            name="Conditional Step",
            condition="condition_true",
            if_branch=if_branch,
            else_branch=else_branch
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify if branch was executed and else branch was not
        if_branch.execute.assert_called_once_with(context)
        else_branch.execute.assert_not_called()
        
        # Verify result came from if branch
        assert result.success is True
        assert result.output == {"result": "If result"}
        
        # Verify condition result and branch taken were stored in context
        assert context.get(f"step.{step.id}.condition_result") is True
        assert context.get(f"step.{step.id}.branch_taken") == "if"
        
    @pytest.mark.asyncio
    async def test_conditional_step_execute_false_condition(self, context):
        """Test executing conditional step with false condition."""
        # Create mock branches
        if_branch = AsyncMock()
        if_branch.execute.return_value = StepResult(success=True, output={"result": "If result"})
        
        else_branch = AsyncMock()
        else_branch.execute.return_value = StepResult(success=True, output={"result": "Else result"})
        
        # Create step
        step = ConditionalStep(
            name="Conditional Step",
            condition="condition_false",
            if_branch=if_branch,
            else_branch=else_branch
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify else branch was executed and if branch was not
        if_branch.execute.assert_not_called()
        else_branch.execute.assert_called_once_with(context)
        
        # Verify result came from else branch
        assert result.success is True
        assert result.output == {"result": "Else result"}
        
        # Verify condition result and branch taken were stored in context
        assert context.get(f"step.{step.id}.condition_result") is False
        assert context.get(f"step.{step.id}.branch_taken") == "else"
        
    @pytest.mark.asyncio
    async def test_conditional_step_no_else_branch(self, context):
        """Test executing conditional step with no else branch."""
        # Create mock if branch
        if_branch = AsyncMock()
        if_branch.execute.return_value = StepResult(success=True, output={"result": "If result"})
        
        # Create step with no else branch
        step = ConditionalStep(
            name="Conditional Step",
            condition="condition_false",
            if_branch=if_branch,
            else_branch=None
        )
        
        # Execute step with false condition
        result = await step.execute(context)
        
        # Verify if branch was not executed
        if_branch.execute.assert_not_called()
        
        # Verify result is a success with empty output
        assert result.success is True
        assert result.output == {}
        
        # Verify condition result and branch taken were stored in context
        assert context.get(f"step.{step.id}.condition_result") is False
        assert context.get(f"step.{step.id}.branch_taken") == "none"
        
    @pytest.mark.asyncio
    async def test_conditional_step_execute_exception(self, context):
        """Test handling exceptions during condition evaluation."""
        # Create mock branches
        if_branch = AsyncMock()
        else_branch = AsyncMock()
        
        # Create step with invalid condition
        step = ConditionalStep(
            name="Conditional Step",
            condition="invalid_condition()",
            if_branch=if_branch,
            else_branch=else_branch
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify neither branch was executed
        if_branch.execute.assert_not_called()
        else_branch.execute.assert_not_called()
        
        # Verify result is a failure
        assert result.success is False
        assert "Conditional execution error" in result.error


class TestParallelStep:
    """Tests for ParallelStep class."""
    
    def test_parallel_step_init(self):
        """Test initializing a parallel step."""
        steps = [
            TaskStep(name="Step 1", task_template={"name": "Task 1"}),
            TaskStep(name="Step 2", task_template={"name": "Task 2"}),
            TaskStep(name="Step 3", task_template={"name": "Task 3"})
        ]
        
        step = ParallelStep(
            name="Parallel Step",
            description="Test parallel",
            steps=steps,
            max_concurrency=2
        )
        
        assert step.name == "Parallel Step"
        assert step.description == "Test parallel"
        assert step.steps == steps
        assert step.max_concurrency == 2
        
    def test_parallel_step_to_dict(self):
        """Test converting parallel step to dictionary."""
        steps = [
            TaskStep(name="Step 1", task_template={"name": "Task 1"}),
            TaskStep(name="Step 2", task_template={"name": "Task 2"})
        ]
        
        step = ParallelStep(
            name="Parallel Step",
            description="Test parallel",
            steps=steps,
            max_concurrency=2
        )
        
        data = step.to_dict()
        
        assert data["type"] == "ParallelStep"
        assert data["name"] == "Parallel Step"
        assert data["description"] == "Test parallel"
        assert len(data["steps"]) == 2
        assert data["steps"][0]["type"] == "TaskStep"
        assert data["steps"][0]["name"] == "Step 1"
        assert data["steps"][1]["type"] == "TaskStep"
        assert data["steps"][1]["name"] == "Step 2"
        assert data["max_concurrency"] == 2
        
    def test_parallel_step_from_dict(self):
        """Test creating parallel step from dictionary."""
        step_data_1 = {
            "type": "TaskStep",
            "name": "Step 1",
            "task_template": {"name": "Task 1"}
        }
        step_data_2 = {
            "type": "TaskStep",
            "name": "Step 2",
            "task_template": {"name": "Task 2"}
        }
        
        data = {
            "id": "test_id",
            "name": "Parallel Step",
            "description": "Test parallel",
            "steps": [step_data_1, step_data_2],
            "max_concurrency": 2
        }
        
        step = ParallelStep.from_dict(data)
        
        assert step.name == "Parallel Step"
        assert step.description == "Test parallel"
        assert len(step.steps) == 2
        assert isinstance(step.steps[0], TaskStep)
        assert step.steps[0].name == "Step 1"
        assert isinstance(step.steps[1], TaskStep)
        assert step.steps[1].name == "Step 2"
        assert step.max_concurrency == 2
        
    @pytest.mark.asyncio
    async def test_parallel_step_execute(self, context):
        """Test executing parallel step."""
        # Create mock steps
        step1 = AsyncMock()
        step1.execute.return_value = StepResult(
            success=True, 
            output={"result": "Result 1"}, 
            task_id="task_1"
        )
        
        step2 = AsyncMock()
        step2.execute.return_value = StepResult(
            success=True, 
            output={"result": "Result 2"}, 
            task_id="task_2"
        )
        
        # Create parallel step
        step = ParallelStep(
            name="Parallel Step",
            steps=[step1, step2],
            max_concurrency=2
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify all steps were executed
        step1.execute.assert_called_once()
        step2.execute.assert_called_once()
        
        # Verify result is a success with results from all steps
        assert result.success is True
        assert len(result.output["results"]) == 2
        assert result.output["results"][0] == {"result": "Result 1"}
        assert result.output["results"][1] == {"result": "Result 2"}
        
        # Verify results and task IDs were stored in context
        assert context.get(f"step.{step.id}.results.0") == {"result": "Result 1"}
        assert context.get(f"step.{step.id}.results.1") == {"result": "Result 2"}
        assert context.get(f"step.{step.id}.task_ids.0") == "task_1"
        assert context.get(f"step.{step.id}.task_ids.1") == "task_2"
        
    @pytest.mark.asyncio
    async def test_parallel_step_execute_with_failure(self, context):
        """Test executing parallel step with one failing step."""
        # Create mock steps
        step1 = AsyncMock()
        step1.execute.return_value = StepResult(
            success=True, 
            output={"result": "Result 1"}
        )
        
        step2 = AsyncMock()
        step2.execute.return_value = StepResult(
            success=False, 
            output={}, 
            error="Step 2 failed"
        )
        
        # Create parallel step
        step = ParallelStep(
            name="Parallel Step",
            steps=[step1, step2]
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify result is a failure
        assert result.success is False
        assert "Step 2 failed" in result.error
        
    @pytest.mark.asyncio
    async def test_parallel_step_execute_exception(self, context):
        """Test handling exceptions during parallel execution."""
        # Create step
        step = ParallelStep(
            name="Parallel Step",
            steps=[MagicMock()]  # Non-async mock will raise an error
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify result is a failure
        assert result.success is False
        assert "Parallel execution error" in result.error


class TestLoopStep:
    """Tests for LoopStep class."""
    
    def test_loop_step_init(self):
        """Test initializing a loop step."""
        child_step = TaskStep(
            name="Child Step",
            task_template={"name": "Child Task"}
        )
        
        step = LoopStep(
            name="Loop Step",
            description="Test loop",
            step=child_step,
            exit_condition="iteration >= 3",
            max_iterations=5
        )
        
        assert step.name == "Loop Step"
        assert step.description == "Test loop"
        assert step.step is child_step
        assert step.exit_condition == "iteration >= 3"
        assert step.max_iterations == 5
        
    def test_loop_step_to_dict(self):
        """Test converting loop step to dictionary."""
        child_step = TaskStep(
            name="Child Step",
            task_template={"name": "Child Task"}
        )
        
        step = LoopStep(
            name="Loop Step",
            description="Test loop",
            step=child_step,
            exit_condition="iteration >= 3",
            max_iterations=5
        )
        
        data = step.to_dict()
        
        assert data["type"] == "LoopStep"
        assert data["name"] == "Loop Step"
        assert data["description"] == "Test loop"
        assert data["step"]["type"] == "TaskStep"
        assert data["step"]["name"] == "Child Step"
        assert data["exit_condition"] == "iteration >= 3"
        assert data["max_iterations"] == 5
        
    def test_loop_step_from_dict(self):
        """Test creating loop step from dictionary."""
        child_step_data = {
            "type": "TaskStep",
            "name": "Child Step",
            "task_template": {"name": "Child Task"}
        }
        
        data = {
            "id": "test_id",
            "name": "Loop Step",
            "description": "Test loop",
            "step": child_step_data,
            "exit_condition": "iteration >= 3",
            "max_iterations": 5
        }
        
        step = LoopStep.from_dict(data)
        
        assert step.name == "Loop Step"
        assert step.description == "Test loop"
        assert isinstance(step.step, TaskStep)
        assert step.step.name == "Child Step"
        assert step.exit_condition == "iteration >= 3"
        assert step.max_iterations == 5
        
    @pytest.mark.asyncio
    async def test_loop_step_execute_max_iterations(self, context):
        """Test executing loop step for maximum iterations."""
        # Create mock child step
        child_step = AsyncMock()
        child_step.execute.side_effect = [
            StepResult(success=True, output={"result": f"Result {i}"})
            for i in range(3)
        ]
        
        # Create loop step with exit condition that never triggers
        step = LoopStep(
            name="Loop Step",
            step=child_step,
            exit_condition="False",
            max_iterations=3
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify child step was executed max_iterations times
        assert child_step.execute.call_count == 3
        
        # Verify result is a success with results from all iterations
        assert result.success is True
        assert result.output["iterations"] == 3
        assert len(result.output["results"]) == 3
        
        # Verify iterations were stored in context
        assert context.get(f"step.{step.id}.total_iterations") == 3
        assert context.get(f"step.{step.id}.iterations.0") == {"result": "Result 0"}
        assert context.get(f"step.{step.id}.iterations.1") == {"result": "Result 1"}
        assert context.get(f"step.{step.id}.iterations.2") == {"result": "Result 2"}
        
    @pytest.mark.asyncio
    async def test_loop_step_execute_exit_condition(self, context):
        """Test executing loop step until exit condition is met."""
        # Create mock child step
        child_step = AsyncMock()
        child_step.execute.side_effect = [
            StepResult(success=True, output={"result": f"Result {i}"})
            for i in range(5)
        ]
        
        # Add counter to context for exit condition
        context.set("counter", 0)
        
        async def increment_counter_and_execute(ctx):
            # Increment counter
            current = ctx.get("counter", 0)
            ctx.set("counter", current + 1)
            
            # Execute with original side effect
            return child_step.execute.side_effect[current](ctx)
            
        child_step.execute.side_effect = increment_counter_and_execute
        
        # Create loop step with exit condition
        step = LoopStep(
            name="Loop Step",
            step=child_step,
            exit_condition="counter >= 3",
            max_iterations=5
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify child step was executed until exit condition (plus first iteration)
        assert child_step.execute.call_count == 4  # Initial + 3 iterations before exit
        
        # Verify result is a success with results from all iterations
        assert result.success is True
        assert result.output["iterations"] == 3
        
    @pytest.mark.asyncio
    async def test_loop_step_execute_child_failure(self, context):
        """Test executing loop step with child step failure."""
        # Create mock child step
        child_step = AsyncMock()
        child_step.execute.side_effect = [
            StepResult(success=True, output={"result": "Result 0"}),
            StepResult(success=False, output={}, error="Child step failed")
        ]
        
        # Create loop step
        step = LoopStep(
            name="Loop Step",
            step=child_step,
            max_iterations=5
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify child step was executed until failure
        assert child_step.execute.call_count == 2
        
        # Verify result is a failure
        assert result.success is False
        assert result.error == "Child step failed"
        
    @pytest.mark.asyncio
    async def test_loop_step_execute_exception(self, context):
        """Test handling exceptions during loop execution."""
        # Create loop step with invalid exit condition
        step = LoopStep(
            name="Loop Step",
            step=MagicMock(),  # Non-async mock will raise an error
            max_iterations=5
        )
        
        # Execute step
        result = await step.execute(context)
        
        # Verify result is a failure
        assert result.success is False
        assert "Loop execution error" in result.error