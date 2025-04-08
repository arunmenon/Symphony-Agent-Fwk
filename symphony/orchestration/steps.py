"""Workflow step implementations for Symphony orchestration.

This module provides concrete implementations of workflow steps for various
orchestration patterns, including task execution, conditional logic,
parallel execution, iterative processing, and custom processing functions.
"""

import asyncio
import inspect
from typing import Dict, List, Optional, Any, Callable, Union, Awaitable

from symphony.core.task import Task, TaskStatus
from symphony.core.agent_factory import AgentFactory
from symphony.core.task_manager import TaskManager
from symphony.execution.enhanced_agent import EnhancedExecutor
from symphony.execution.router import TaskRouter
from symphony.orchestration.workflow_definition import WorkflowStep, StepResult, WorkflowContext


class TaskStep(WorkflowStep):
    """Step that executes a task with an agent.
    
    This step creates and executes a task using the enhanced executor,
    with support for agent selection and context integration.
    """
    
    def __init__(self, 
                name: str, 
                task_template: Dict[str, Any], 
                agent_id: Optional[str] = None,
                description: str = ""):
        """Initialize task step.
        
        Args:
            name: Name of the step
            task_template: Template for task creation with placeholders
            agent_id: Optional agent ID to use for execution
            description: Description of the step
        """
        super().__init__(name, description)
        self.task_template = task_template
        self.agent_id = agent_id
        
    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute the task with given context.
        
        Args:
            context: Workflow context
            
        Returns:
            Result of task execution
        """
        try:
            # Resolve any template variables in the task
            resolved_task = context.resolve_template(self.task_template)
            
            # Get required services
            task_manager = context.get_service("task_manager")
            agent_factory = context.get_service("agent_factory")
            executor = context.get_service("enhanced_executor")
            
            # Create task
            task = await task_manager.create_task(**resolved_task)
            
            # Check for agent type in resolved task
            agent_type = resolved_task.get("agent_type")
            model = resolved_task.get("model")
            
            agent = None
            
            # If agent_type is specified, create agent of that type with specified model
            if agent_type:
                # First check if we have a dedicated factory method for this agent type
                agent_creator = getattr(agent_factory, f"create_{agent_type}_agent", None)
                if agent_creator and callable(agent_creator):
                    # Create agent using specialized factory method
                    agent_kwargs = {}
                    if model:
                        agent_kwargs["model"] = model
                    agent = await agent_creator(**agent_kwargs)
                else:
                    # Use generic method with type parameter
                    agent = await agent_factory.create_agent(agent_type=agent_type, model=model)
            
            # If no agent was created via agent_type, use traditional agent_id approach
            if not agent:
                agent_id = self.agent_id or context.get("default_agent_id")
                if agent_id:
                    agent = await agent_factory.create_agent_from_id(agent_id)
                    
                    # If we have a model override, we may need to adjust the agent's model
                    if model and hasattr(agent, "model"):
                        agent.model = model
                else:
                    # Use router to find appropriate agent
                    router = context.get_service("task_router")
                    agent_id = await router.route_task(task)
                    agent = await agent_factory.create_agent_from_id(agent_id)
            
            # Execute with enhanced executor
            result_task = await executor.execute_task(
                task.id, 
                agent, 
                workflow_id=context.workflow_id
            )
            
            # Update context with task result
            context.set(f"step.{self.id}.result", result_task.output_data.get("result"))
            context.set(f"step.{self.id}.task_id", result_task.id)
            
            # Return result
            return StepResult(
                success=result_task.status == TaskStatus.COMPLETED,
                output=result_task.output_data,
                task_id=task.id,
                error=result_task.error
            )
        except Exception as e:
            return StepResult(
                success=False,
                output={},
                error=f"Task execution error: {str(e)}"
            )
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for persistence."""
        data = super().to_dict()
        data.update({
            "task_template": self.task_template,
            "agent_id": self.agent_id
        })
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskStep':
        """Create step from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            task_template=data["task_template"],
            agent_id=data.get("agent_id")
        )


class ConditionalStep(WorkflowStep):
    """Step that executes different branches based on a condition.
    
    This step evaluates a condition and executes either the if_branch
    or else_branch depending on the result.
    """
    
    def __init__(self, 
                name: str, 
                condition: str, 
                if_branch: WorkflowStep, 
                else_branch: Optional[WorkflowStep] = None,
                description: str = ""):
        """Initialize conditional step.
        
        Args:
            name: Name of the step
            condition: Condition expression to evaluate
            if_branch: Step to execute if condition is true
            else_branch: Optional step to execute if condition is false
            description: Description of the step
        """
        super().__init__(name, description)
        self.condition = condition
        self.if_branch = if_branch
        self.else_branch = else_branch
        
    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute the branch based on condition evaluation.
        
        Args:
            context: Workflow context
            
        Returns:
            Result of branch execution
        """
        try:
            # Evaluate the condition
            condition_result = context.evaluate_condition(self.condition)
            
            # Store decision in context
            context.set(f"step.{self.id}.condition_result", condition_result)
            
            # Execute the appropriate branch
            if condition_result:
                context.set(f"step.{self.id}.branch_taken", "if")
                result = await self.if_branch.execute(context)
            elif self.else_branch:
                context.set(f"step.{self.id}.branch_taken", "else")
                result = await self.else_branch.execute(context)
            else:
                # No else branch, return success
                context.set(f"step.{self.id}.branch_taken", "none")
                result = StepResult(success=True, output={})
                
            return result
        except Exception as e:
            return StepResult(
                success=False,
                output={},
                error=f"Conditional execution error: {str(e)}"
            )
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for persistence."""
        data = super().to_dict()
        data.update({
            "condition": self.condition,
            "if_branch": self.if_branch.to_dict(),
            "else_branch": self.else_branch.to_dict() if self.else_branch else None
        })
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConditionalStep':
        """Create step from dictionary."""
        if_branch = WorkflowStep.from_dict(data["if_branch"])
        else_branch = None
        if data.get("else_branch"):
            else_branch = WorkflowStep.from_dict(data["else_branch"])
            
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            condition=data["condition"],
            if_branch=if_branch,
            else_branch=else_branch
        )


class ParallelStep(WorkflowStep):
    """Step that executes multiple steps in parallel.
    
    This step executes all of its child steps concurrently, with an optional
    limit on the maximum number of concurrent executions.
    """
    
    def __init__(self, 
                name: str, 
                steps: List[WorkflowStep], 
                max_concurrency: int = 5,
                description: str = ""):
        """Initialize parallel step.
        
        Args:
            name: Name of the step
            steps: List of steps to execute in parallel
            max_concurrency: Maximum number of concurrent executions
            description: Description of the step
        """
        super().__init__(name, description)
        self.steps = steps
        self.max_concurrency = max_concurrency
        
    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute all steps in parallel.
        
        Args:
            context: Workflow context
            
        Returns:
            Result of parallel execution
        """
        try:
            # Create a semaphore to limit concurrency
            semaphore = asyncio.Semaphore(self.max_concurrency)
            
            async def execute_with_semaphore(step: WorkflowStep, index: int) -> StepResult:
                async with semaphore:
                    # Create a sub-context for each parallel execution
                    sub_context = context.create_sub_context()
                    sub_context.set("parallel_index", index)
                    result = await step.execute(sub_context)
                    return result
            
            # Execute all steps concurrently
            results = await asyncio.gather(*[
                execute_with_semaphore(step, i) for i, step in enumerate(self.steps)
            ])
            
            # Store results in context
            for i, result in enumerate(results):
                context.set(f"step.{self.id}.results.{i}", result.output)
                if result.task_id:
                    context.set(f"step.{self.id}.task_ids.{i}", result.task_id)
                
            # All steps must succeed for parallel step to succeed
            success = all(result.success for result in results)
            
            # If any step failed, collect errors
            error = None
            if not success:
                errors = [r.error for r in results if not r.success and r.error]
                error = "; ".join(errors)
            
            return StepResult(
                success=success,
                output={"results": [result.output for result in results]},
                error=error
            )
        except Exception as e:
            return StepResult(
                success=False,
                output={},
                error=f"Parallel execution error: {str(e)}"
            )
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for persistence."""
        data = super().to_dict()
        data.update({
            "steps": [step.to_dict() for step in self.steps],
            "max_concurrency": self.max_concurrency
        })
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParallelStep':
        """Create step from dictionary."""
        steps = [WorkflowStep.from_dict(step) for step in data["steps"]]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            steps=steps,
            max_concurrency=data.get("max_concurrency", 5)
        )


class LoopStep(WorkflowStep):
    """Step that executes a child step repeatedly until a condition is met.
    
    This step executes its child step in a loop, either a fixed number of times
    or until a condition is met, with safeguards against infinite loops.
    """
    
    def __init__(self, 
                name: str, 
                step: WorkflowStep, 
                exit_condition: str = "False", 
                max_iterations: int = 10,
                description: str = ""):
        """Initialize loop step.
        
        Args:
            name: Name of the step
            step: Step to execute in a loop
            exit_condition: Condition for exiting the loop
            max_iterations: Maximum number of iterations
            description: Description of the step
        """
        super().__init__(name, description)
        self.step = step
        self.exit_condition = exit_condition
        self.max_iterations = max_iterations
        
    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute the step in a loop until condition is met.
        
        Args:
            context: Workflow context
            
        Returns:
            Result of loop execution
        """
        try:
            iteration = 0
            results = []
            
            # Store loop info in context
            context.set(f"step.{self.id}.max_iterations", self.max_iterations)
            
            while iteration < self.max_iterations:
                # Store current iteration in context
                context.set(f"step.{self.id}.current_iteration", iteration)
                
                # Check if we should exit the loop
                if iteration > 0 and context.evaluate_condition(self.exit_condition):
                    break
                    
                # Execute the step
                result = await self.step.execute(context)
                results.append(result)
                
                # Store result in context
                context.set(f"step.{self.id}.iterations.{iteration}", result.output)
                
                # Break if step failed
                if not result.success:
                    break
                    
                iteration += 1
                
            # Store final iteration count
            context.set(f"step.{self.id}.total_iterations", iteration)
            
            # Success if no iterations failed
            success = all(result.success for result in results)
            
            # If any iteration failed, get the error
            error = None
            if not success:
                for result in results:
                    if not result.success and result.error:
                        error = result.error
                        break
            
            return StepResult(
                success=success,
                output={
                    "iterations": iteration,
                    "results": [result.output for result in results]
                },
                error=error
            )
        except Exception as e:
            return StepResult(
                success=False,
                output={},
                error=f"Loop execution error: {str(e)}"
            )
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for persistence."""
        data = super().to_dict()
        data.update({
            "step": self.step.to_dict(),
            "exit_condition": self.exit_condition,
            "max_iterations": self.max_iterations
        })
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoopStep':
        """Create step from dictionary."""
        step = WorkflowStep.from_dict(data["step"])
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            step=step,
            exit_condition=data.get("exit_condition", "False"),
            max_iterations=data.get("max_iterations", 10)
        )


class ProcessingStep(WorkflowStep):
    """Step that executes a custom processing function.
    
    This step allows for custom data processing within a workflow,
    without requiring an agent or task. It's useful for data transformation,
    aggregation, and other processing operations.
    """
    
    def __init__(self, 
                name: str, 
                processing_function: Callable[[Dict[str, Any]], Union[Dict[str, Any], Awaitable[Dict[str, Any]]]],
                context_data: Optional[Dict[str, Any]] = None,
                description: str = ""):
        """Initialize processing step.
        
        Args:
            name: Name of the step
            processing_function: Function that processes data
            context_data: Additional context data for processing
            description: Description of the step
        """
        super().__init__(name, description)
        self.processing_function = processing_function
        self.context_data = context_data or {}
        
    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute the processing function with given context.
        
        Args:
            context: Workflow context
            
        Returns:
            Result of processing
        """
        try:
            # Prepare combined context for processing
            context_dict = context.data.copy()
            if self.context_data:
                # Add additional context data, resolving any templates
                resolved_data = context.resolve_template(self.context_data)
                context_dict.update(resolved_data)
            
            # Execute the processing function
            is_async = inspect.iscoroutinefunction(self.processing_function)
            if is_async:
                result = await self.processing_function(context_dict)
            else:
                result = self.processing_function(context_dict)
                
            # If result is None, use empty dict
            if result is None:
                result = {}
                
            # Store result in context
            context.set(f"step.{self.id}.result", result)
            
            return StepResult(
                success=True,
                output=result if isinstance(result, dict) else {"result": result},
            )
        except Exception as e:
            return StepResult(
                success=False,
                output={},
                error=f"Processing error: {str(e)}"
            )
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for persistence."""
        data = super().to_dict()
        data.update({
            "function_name": self.processing_function.__name__,
            "context_data": self.context_data
        })
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingStep':
        """Create step from dictionary.
        
        Note: This method requires the processing function to be registered separately,
        as functions cannot be serialized directly.
        """
        # In practice, processing functions need to be registered in a registry
        # and looked up by name during deserialization
        raise NotImplementedError(
            "Deserialization of ProcessingStep requires a function registry mechanism."
        )