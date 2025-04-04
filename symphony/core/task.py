"""Task domain model for Symphony.

This module provides a Task class that can be used to represent work to be
performed by agents. Tasks can be persisted to storage and have a lifecycle
with different states.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator
import uuid
from pydantic.config import ConfigDict

class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Task(BaseModel):
    """Task definition with persistence support.
    
    A task represents a unit of work that can be executed by an agent.
    It has a lifecycle that starts in PENDING, transitions to RUNNING
    during execution, and ends in either COMPLETED or FAILED.
    
    Tasks can be persisted to storage and retrieved later, allowing for
    asynchronous execution and status tracking.
    """
    model_config = ConfigDict(extra="allow")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    
    # Status
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Data
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    agent_id: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: Optional[datetime] = None
    parent_task_id: Optional[str] = None
    workflow_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def get_input(self, key: str, default: Any = None) -> Any:
        """Get input by key with optional default."""
        return self.input_data.get(key, default)
    
    def set_output(self, key: str, value: Any) -> None:
        """Set output by key."""
        if self.output_data is None:
            self.output_data = {}
        self.output_data[key] = value
    
    def mark_running(self) -> None:
        """Mark task as running."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
    
    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
    
    def mark_failed(self, error: str) -> None:
        """Mark task as failed with error."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary.
        
        This method is provided for backward compatibility with existing code
        that might expect a dictionary representation of a task.
        """
        return self.model_dump()