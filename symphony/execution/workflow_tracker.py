"""Workflow tracking for Symphony execution.

This module provides components for tracking the execution of workflows,
including individual tasks, agent activities, and overall workflow status.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict

from symphony.core.task import Task, TaskStatus
from symphony.persistence.repository import Repository


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class Workflow(BaseModel):
    """Workflow definition with persistence support.
    
    A workflow represents a collection of related tasks that are executed
    in a specific order or pattern. It has a lifecycle similar to tasks,
    but encompasses multiple tasks and potentially multiple agents.
    """
    model_config = ConfigDict(extra="allow")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    
    # Status
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Relationships
    task_ids: List[str] = Field(default_factory=list)
    parent_workflow_id: Optional[str] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    
    def mark_running(self) -> None:
        """Mark workflow as running."""
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.now()
    
    def mark_completed(self) -> None:
        """Mark workflow as completed."""
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = datetime.now()
    
    def mark_failed(self, error: str) -> None:
        """Mark workflow as failed with error."""
        self.status = WorkflowStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()
    
    def mark_paused(self) -> None:
        """Mark workflow as paused."""
        self.status = WorkflowStatus.PAUSED
    
    def add_task(self, task_id: str) -> None:
        """Add a task to the workflow."""
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)


class WorkflowTracker:
    """Tracks and manages workflow execution.
    
    The workflow tracker is responsible for creating, updating, and querying
    workflows and their tasks. It provides methods for tracking workflow
    status, adding tasks to workflows, and retrieving workflow information.
    """
    
    def __init__(self, 
                 workflow_repository: Repository[Workflow],
                 task_repository: Repository[Task]):
        """Initialize workflow tracker with repositories.
        
        Args:
            workflow_repository: Repository for workflow storage
            task_repository: Repository for task storage
        """
        self.workflow_repository = workflow_repository
        self.task_repository = task_repository
    
    async def create_workflow(self, name: str, **kwargs) -> Workflow:
        """Create a new workflow.
        
        Args:
            name: Name of the workflow
            **kwargs: Additional workflow parameters
            
        Returns:
            The created workflow
        """
        workflow = Workflow(name=name, **kwargs)
        await self.workflow_repository.save(workflow)
        return workflow
    
    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID.
        
        Args:
            workflow_id: ID of the workflow to retrieve
            
        Returns:
            The workflow if found, None otherwise
        """
        return await self.workflow_repository.find_by_id(workflow_id)
    
    async def add_task_to_workflow(self, workflow_id: str, task_id: str) -> bool:
        """Add a task to a workflow.
        
        Args:
            workflow_id: ID of the workflow
            task_id: ID of the task to add
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If workflow is not found
        """
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow.add_task(task_id)
        await self.workflow_repository.update(workflow)
        return True
    
    async def update_workflow_status(self, workflow_id: str, status: WorkflowStatus, error: Optional[str] = None) -> Workflow:
        """Update workflow status.
        
        Args:
            workflow_id: ID of the workflow
            status: New status
            error: Optional error message (for FAILED status)
            
        Returns:
            Updated workflow
            
        Raises:
            ValueError: If workflow is not found
        """
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if status == WorkflowStatus.RUNNING:
            workflow.mark_running()
        elif status == WorkflowStatus.COMPLETED:
            workflow.mark_completed()
        elif status == WorkflowStatus.FAILED:
            workflow.mark_failed(error or "Unknown error")
        elif status == WorkflowStatus.PAUSED:
            workflow.mark_paused()
        else:
            # Just set the status directly for other cases
            workflow.status = status
        
        await self.workflow_repository.update(workflow)
        return workflow
    
    async def get_workflow_tasks(self, workflow_id: str) -> List[Task]:
        """Get all tasks in a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            List of tasks in the workflow
            
        Raises:
            ValueError: If workflow is not found
        """
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        tasks = []
        for task_id in workflow.task_ids:
            task = await self.task_repository.find_by_id(task_id)
            if task:
                tasks.append(task)
        
        return tasks
    
    async def compute_workflow_status(self, workflow_id: str) -> WorkflowStatus:
        """Compute workflow status based on task statuses.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Computed workflow status
            
        Raises:
            ValueError: If workflow is not found
        """
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        tasks = await self.get_workflow_tasks(workflow_id)
        
        if not tasks:
            # No tasks means workflow is still pending
            return WorkflowStatus.PENDING
        
        # Count tasks by status
        status_counts = {status: 0 for status in TaskStatus}
        for task in tasks:
            status_counts[task.status] += 1
        
        # Determine workflow status
        if status_counts[TaskStatus.FAILED] > 0:
            # Any failed task means workflow is failed
            return WorkflowStatus.FAILED
        elif status_counts[TaskStatus.RUNNING] > 0:
            # Any running task means workflow is running
            return WorkflowStatus.RUNNING
        elif status_counts[TaskStatus.PENDING] > 0:
            # If no failures or running tasks, but some pending tasks, workflow is still running
            return WorkflowStatus.RUNNING
        else:
            # All tasks are completed
            return WorkflowStatus.COMPLETED
    
    async def sync_workflow_status(self, workflow_id: str) -> Workflow:
        """Sync workflow status with task statuses.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Updated workflow
            
        Raises:
            ValueError: If workflow is not found
        """
        status = await self.compute_workflow_status(workflow_id)
        return await self.update_workflow_status(workflow_id, status)