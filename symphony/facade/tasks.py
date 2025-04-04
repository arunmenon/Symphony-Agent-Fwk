"""Task facade module for Symphony.

This module provides a clean, domain-specific interface for working with
Symphony tasks, abstracting away the details of the registry pattern
and other implementation details.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from symphony.core.registry import ServiceRegistry
from symphony.core.task import Task, TaskStatus, TaskPriority

class TaskFacade:
    """Facade for working with Symphony tasks.
    
    This class provides a clean interface for creating and managing tasks,
    abstracting away the details of the registry pattern.
    """
    
    def __init__(self, registry: ServiceRegistry = None):
        """Initialize task facade.
        
        Args:
            registry: Service registry instance (optional)
        """
        self.registry = registry or ServiceRegistry.get_instance()
    
    async def create_task(self, 
                         name: str, 
                         description: str, 
                         input_data: Dict[str, Any],
                         agent_id: Optional[str] = None,
                         priority: TaskPriority = TaskPriority.MEDIUM,
                         deadline: Optional[datetime] = None,
                         parent_task_id: Optional[str] = None,
                         workflow_id: Optional[str] = None,
                         metadata: Dict[str, Any] = None) -> Task:
        """Create a new task.
        
        Args:
            name: Task name
            description: Task description
            input_data: Task input data
            agent_id: Agent ID (optional)
            priority: Task priority
            deadline: Task deadline (optional)
            parent_task_id: Parent task ID for subtasks (optional)
            workflow_id: Workflow ID for tracking (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            New task
        """
        task = Task(
            name=name,
            description=description,
            input_data=input_data,
            agent_id=agent_id,
            priority=priority,
            deadline=deadline,
            parent_task_id=parent_task_id,
            workflow_id=workflow_id,
            metadata=metadata or {}
        )
        
        return task
    
    async def save_task(self, task: Task) -> str:
        """Save a task.
        
        Args:
            task: Task to save
            
        Returns:
            Task ID
        """
        try:
            task_repo = self.registry.get_repository("task")
            return await task_repo.save(task)
        except ValueError:
            # Repository might not be registered yet
            from symphony.persistence.memory_repository import InMemoryRepository
            task_repo = InMemoryRepository(Task)
            self.registry.register_repository("task", task_repo)
            return await task_repo.save(task)
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task or None if not found
        """
        try:
            task_repo = self.registry.get_repository("task")
            return await task_repo.find_by_id(task_id)
        except ValueError:
            return None
    
    async def execute_task(self, task: Task) -> Task:
        """Execute a task.
        
        Args:
            task: Task to execute
            
        Returns:
            Executed task
        """
        # Make sure task is saved first
        if not task.id:
            await self.save_task(task)
        
        # Get executor
        try:
            executor = self.registry.get_enhanced_executor()
        except ValueError:
            # Register required dependencies
            if "task" not in self.registry.repositories:
                from symphony.persistence.memory_repository import InMemoryRepository
                task_repo = InMemoryRepository(Task)
                self.registry.register_repository("task", task_repo)
            
            # Get or create executor
            executor = self.registry.get_enhanced_executor()
        
        # Execute task
        await executor.execute_task(task.id)
        
        # Return updated task
        return await self.get_task(task.id)
    
    async def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status.
        
        Args:
            status: Task status
            
        Returns:
            List of matching tasks
        """
        try:
            task_repo = self.registry.get_repository("task")
            all_tasks = await task_repo.find_all()
            return [task for task in all_tasks if task.status == status]
        except ValueError:
            return []
    
    async def get_tasks_by_agent(self, agent_id: str) -> List[Task]:
        """Get tasks assigned to an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of matching tasks
        """
        try:
            task_repo = self.registry.get_repository("task")
            all_tasks = await task_repo.find_all()
            return [task for task in all_tasks if task.agent_id == agent_id]
        except ValueError:
            return []
    
    async def get_tasks_by_workflow(self, workflow_id: str) -> List[Task]:
        """Get tasks associated with a workflow.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            List of matching tasks
        """
        try:
            task_repo = self.registry.get_repository("task")
            all_tasks = await task_repo.find_all()
            return [task for task in all_tasks if task.workflow_id == workflow_id]
        except ValueError:
            return []
    
    async def update_task_status(self, task_id: str, status: TaskStatus, result: Any = None, error: str = None) -> bool:
        """Update task status.
        
        Args:
            task_id: Task ID
            status: New status
            result: Task result (optional)
            error: Error message (optional)
            
        Returns:
            True if the update was successful
        """
        task = await self.get_task(task_id)
        if not task:
            return False
        
        # Update task
        task.status = status
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        
        # Save updated task
        try:
            task_repo = self.registry.get_repository("task")
            await task_repo.update(task)
            return True
        except ValueError:
            return False