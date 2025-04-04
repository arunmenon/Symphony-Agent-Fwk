"""Enhanced agent execution for Symphony.

This module provides enhanced execution capabilities for agents, including
persistence integration, monitoring, and error handling.
"""

import asyncio
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, Callable

from symphony.agents.base import Agent
from symphony.core.task import Task, TaskStatus
from symphony.persistence.repository import Repository
from symphony.execution.workflow_tracker import WorkflowTracker, Workflow, WorkflowStatus


class EnhancedExecutor:
    """Enhanced agent execution with persistence.
    
    The enhanced executor provides advanced execution capabilities for agents,
    including persistence integration, monitoring, and error handling.
    """
    
    def __init__(self, 
                 task_repository: Repository[Task],
                 workflow_tracker: Optional[WorkflowTracker] = None):
        """Initialize enhanced executor with repositories.
        
        Args:
            task_repository: Repository for task storage
            workflow_tracker: Optional workflow tracker for workflow integration
        """
        self.task_repository = task_repository
        self.workflow_tracker = workflow_tracker
    
    async def execute_task(self, 
                          task_id: str, 
                          agent: Agent, 
                          workflow_id: Optional[str] = None,
                          context: Optional[Dict[str, Any]] = None,
                          pre_execution_hook: Optional[Callable[[Task, Agent], None]] = None,
                          post_execution_hook: Optional[Callable[[Task, Agent, Any], None]] = None) -> Task:
        """Execute a task with an agent and advanced features.
        
        Args:
            task_id: ID of the task to execute
            agent: Agent to execute the task
            workflow_id: Optional workflow ID to associate with task
            context: Optional context data for execution
            pre_execution_hook: Optional function to call before execution
            post_execution_hook: Optional function to call after execution
            
        Returns:
            The updated task with results
            
        Raises:
            ValueError: If task is not found
        """
        # Get task
        task = await self.task_repository.find_by_id(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Add to workflow if provided
        if workflow_id and self.workflow_tracker:
            await self.workflow_tracker.add_task_to_workflow(workflow_id, task_id)
            workflow = await self.workflow_tracker.get_workflow(workflow_id)
            if workflow and workflow.status == WorkflowStatus.PENDING:
                await self.workflow_tracker.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)
        
        # Update task status
        task.mark_running()
        await self.task_repository.update(task)
        
        # Save workflow status
        if workflow_id and self.workflow_tracker:
            await self.workflow_tracker.sync_workflow_status(workflow_id)
        
        # Execute pre-execution hook if provided
        if pre_execution_hook:
            try:
                pre_execution_hook(task, agent)
            except Exception as e:
                print(f"Pre-execution hook error: {e}")
        
        try:
            # Prepare context
            execution_context = context or {}
            input_query = task.get_input("query", "")
            
            # Add additional task metadata to context
            execution_context["task_id"] = task.id
            execution_context["task_name"] = task.name
            if workflow_id:
                execution_context["workflow_id"] = workflow_id
            
            # Execute with agent
            result = await agent.run(input_query)
            
            # Update task with result
            task.set_output("result", result)
            task.set_output("context", execution_context)
            task.mark_completed()
            
            # Execute post-execution hook if provided
            if post_execution_hook:
                try:
                    post_execution_hook(task, agent, result)
                except Exception as e:
                    print(f"Post-execution hook error: {e}")
                    
        except Exception as e:
            # Handle failure with detailed error information
            error_details = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            }
            task.set_output("error_details", error_details)
            task.mark_failed(str(e))
        
        # Save updated task
        await self.task_repository.update(task)
        
        # Update workflow status if needed
        if workflow_id and self.workflow_tracker:
            await self.workflow_tracker.sync_workflow_status(workflow_id)
        
        return task
    
    async def batch_execute(self, 
                           tasks: List[Tuple[str, Agent]], 
                           workflow_id: Optional[str] = None,
                           max_concurrent: int = 5) -> List[Task]:
        """Execute multiple tasks concurrently.
        
        Args:
            tasks: List of (task_id, agent) tuples to execute
            workflow_id: Optional workflow ID to associate with tasks
            max_concurrent: Maximum number of concurrent executions
            
        Returns:
            List of completed tasks
        """
        if not tasks:
            return []
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(task_id: str, agent: Agent) -> Task:
            async with semaphore:
                return await self.execute_task(task_id, agent, workflow_id)
        
        # Execute all tasks concurrently with semaphore
        results = await asyncio.gather(*[
            execute_with_semaphore(task_id, agent) for task_id, agent in tasks
        ])
        
        return results
    
    async def execute_with_retry(self, 
                                task_id: str, 
                                agent: Agent, 
                                max_retries: int = 3,
                                retry_delay: float = 1.0,
                                workflow_id: Optional[str] = None) -> Task:
        """Execute a task with automatic retry on failure.
        
        Args:
            task_id: ID of the task to execute
            agent: Agent to execute the task
            max_retries: Maximum number of retry attempts
            retry_delay: Delay in seconds between retries
            workflow_id: Optional workflow ID to associate with task
            
        Returns:
            The updated task with results
        """
        retries = 0
        last_error = None
        
        while retries <= max_retries:
            try:
                # Execute task
                result_task = await self.execute_task(task_id, agent, workflow_id)
                
                # If successful, return result
                if result_task.status == TaskStatus.COMPLETED:
                    return result_task
                    
                # If failed, prepare for retry
                last_error = result_task.error
                retries += 1
                
                # Wait before retry
                if retries <= max_retries:
                    await asyncio.sleep(retry_delay)
                    
            except Exception as e:
                last_error = str(e)
                retries += 1
                
                # Wait before retry
                if retries <= max_retries:
                    await asyncio.sleep(retry_delay)
        
        # If all retries failed, get and update the task
        task = await self.task_repository.find_by_id(task_id)
        if task:
            task.mark_failed(f"Failed after {max_retries} retries. Last error: {last_error}")
            await self.task_repository.update(task)
        
        return task