"""Task builder for Symphony.

This module provides a fluent interface for building Symphony tasks.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.core.task import Task, TaskStatus, TaskPriority

class TaskBuilder:
    """Builder for Symphony tasks.
    
    This class provides a fluent interface for building tasks, making it
    easier to create complex task configurations with a clean, readable syntax.
    """
    
    def __init__(self, registry: ServiceRegistry = None):
        """Initialize task builder.
        
        Args:
            registry: Service registry instance (optional)
        """
        self.registry = registry or ServiceRegistry.get_instance()
        self.task: Optional[Task] = None
        self.task_input: Dict[str, Any] = {}
        self.metadata_dict: Dict[str, Any] = {}
        
    def create(self, name: str, description: str) -> 'TaskBuilder':
        """Create a new task.
        
        Args:
            name: Task name
            description: Task description
            
        Returns:
            Self for chaining
        """
        self.task = Task(
            name=name,
            description=description,
            input_data={},
            metadata={}
        )
        return self
    
    def with_input(self, key: str, value: Any) -> 'TaskBuilder':
        """Add input data to the task.
        
        Args:
            key: Input key
            value: Input value
            
        Returns:
            Self for chaining
        """
        self.task_input[key] = value
        
        # Update task if it exists
        if self.task:
            self.task.input_data[key] = value
        
        return self
    
    def with_query(self, query: str) -> 'TaskBuilder':
        """Set the query input for the task.
        
        Args:
            query: Task query
            
        Returns:
            Self for chaining
        """
        self.task_input["query"] = query
        
        # Update task if it exists
        if self.task:
            self.task.input_data["query"] = query
        
        return self
    
    def for_agent(self, agent_id: str) -> 'TaskBuilder':
        """Assign task to a specific agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Self for chaining
        """
        if self.task:
            self.task.agent_id = agent_id
        
        return self
    
    def with_priority(self, priority: TaskPriority) -> 'TaskBuilder':
        """Set task priority.
        
        Args:
            priority: Task priority
            
        Returns:
            Self for chaining
        """
        if self.task:
            self.task.priority = priority
        
        return self
    
    def with_deadline(self, deadline: datetime) -> 'TaskBuilder':
        """Set task deadline.
        
        Args:
            deadline: Task deadline
            
        Returns:
            Self for chaining
        """
        if self.task:
            self.task.deadline = deadline
        
        return self
    
    def in_workflow(self, workflow_id: str) -> 'TaskBuilder':
        """Associate task with a workflow.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Self for chaining
        """
        if self.task:
            self.task.workflow_id = workflow_id
        
        return self
    
    def as_subtask_of(self, parent_task_id: str) -> 'TaskBuilder':
        """Set parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            Self for chaining
        """
        if self.task:
            self.task.parent_task_id = parent_task_id
        
        return self
    
    def with_metadata(self, key: str, value: Any) -> 'TaskBuilder':
        """Add metadata to the task.
        
        Args:
            key: Metadata key
            value: Metadata value
            
        Returns:
            Self for chaining
        """
        self.metadata_dict[key] = value
        
        # Update task if it exists
        if self.task:
            self.task.metadata[key] = value
        
        return self
    
    def build(self) -> Task:
        """Build the task.
        
        Returns:
            Task
        """
        if not self.task:
            raise ValueError("Task not created. Call create() first.")
        
        # Apply all accumulated settings to ensure they're all set
        self.task.input_data = self.task_input
        self.task.metadata = self.metadata_dict
        
        return self.task
    
    async def save(self) -> str:
        """Save the task.
        
        Returns:
            Task ID
        """
        if not self.task:
            raise ValueError("Task not created. Call create() first.")
        
        try:
            task_repo = self.registry.get_repository("task")
            return await task_repo.save(self.task)
        except ValueError:
            # Repository might not be registered yet
            from symphony.persistence.memory_repository import InMemoryRepository
            task_repo = InMemoryRepository(Task)
            self.registry.register_repository("task", task_repo)
            return await task_repo.save(self.task)
    
    async def execute(self) -> Task:
        """Execute the task.
        
        Returns:
            Executed task
        """
        if not self.task:
            raise ValueError("Task not created. Call create() first.")
        
        # Save task if not already saved
        if not self.task.id:
            await self.save()
        
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
        await executor.execute_task(self.task.id)
        
        # Return updated task
        task_repo = self.registry.get_repository("task")
        return await task_repo.find_by_id(self.task.id)