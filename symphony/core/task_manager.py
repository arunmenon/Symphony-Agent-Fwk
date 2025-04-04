"""Task manager for executing tasks with agents.

This module provides a task manager that can execute tasks with agents
and track their status through the task lifecycle.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from symphony.core.task import Task, TaskStatus
from symphony.persistence.repository import Repository
from symphony.agents.base import Agent

class TaskManager:
    """Manages task execution with persistence.
    
    The task manager provides methods for creating, executing, and tracking
    tasks. It persists task status and results to storage, allowing for
    asynchronous execution and status tracking.
    """
    
    def __init__(self, repository: Repository[Task]):
        """Initialize task manager with repository.
        
        Args:
            repository: Repository for task storage
        """
        self.repository = repository
    
    async def create_task(self, name: str, **kwargs) -> Task:
        """Create a new task.
        
        Args:
            name: Name of the task
            **kwargs: Additional task parameters
            
        Returns:
            The created task
        """
        task = Task(name=name, **kwargs)
        await self.repository.save(task)
        return task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID.
        
        Args:
            task_id: ID of the task to retrieve
            
        Returns:
            The task if found, None otherwise
        """
        return await self.repository.find_by_id(task_id)
    
    async def execute_task(self, task_id: str, agent: Agent) -> Task:
        """Execute a task with an agent.
        
        Args:
            task_id: ID of the task to execute
            agent: Agent to execute the task
            
        Returns:
            The updated task with results
            
        Raises:
            ValueError: If task is not found
        """
        # Get task
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Update task status
        task.mark_running()
        await self.repository.update(task)
        
        try:
            # Execute with agent
            input_query = task.get_input("query", "")
            result = await agent.run(input_query)
            
            # Update task with result
            task.set_output("result", result)
            task.mark_completed()
        except Exception as e:
            # Handle failure
            task.mark_failed(str(e))
        
        # Save updated task
        await self.repository.update(task)
        return task
    
    async def find_tasks(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Task]:
        """Find tasks matching filter criteria.
        
        Args:
            filter_criteria: Dictionary of field-value pairs to match
            
        Returns:
            List of matching tasks
        """
        return await self.repository.find_all(filter_criteria)