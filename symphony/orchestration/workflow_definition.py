"""Workflow definitions for Symphony orchestration.

This module provides components for defining workflows in a declarative way,
enabling complex orchestration patterns for agent interactions.
"""

import uuid
import copy
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, ClassVar, Set, Union

from pydantic import BaseModel, Field, ConfigDict

from symphony.core.task import Task
from symphony.execution.workflow_tracker import WorkflowStatus


class StepResult(BaseModel):
    """Result of a workflow step execution."""
    model_config = ConfigDict(extra="allow")
    
    success: bool
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    task_id: Optional[str] = None


class WorkflowContext(BaseModel):
    """Context for workflow execution.
    
    The workflow context provides a shared state across workflow execution,
    allowing steps to share data and access services.
    """
    model_config = ConfigDict(extra="allow")
    
    workflow_id: str
    data: Dict[str, Any] = Field(default_factory=dict)
    service_registry: Any = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from context data."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in context data."""
        self.data[key] = value
        
    def get_service(self, service_name: str) -> Any:
        """Get service from registry."""
        if not self.service_registry:
            raise ValueError("Service registry not available in context")
        return self.service_registry.get_service(service_name)
    
    def resolve_template(self, template: Any) -> Any:
        """Resolve templated values using context data."""
        if isinstance(template, str):
            # Replace {{variable}} with context data
            for key, value in self.data.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in template:
                    template = template.replace(placeholder, str(value))
            return template
        elif isinstance(template, dict):
            # Process dictionary values recursively
            return {k: self.resolve_template(v) for k, v in template.items()}
        elif isinstance(template, list):
            # Process list items recursively
            return [self.resolve_template(item) for item in template]
        else:
            # Return unchanged for other types
            return template
            
    def evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition expression using context data."""
        try:
            # First, resolve any templates in the condition
            resolved_condition = self.resolve_template(condition)
            
            # Create a local namespace with context data
            namespace = self.data.copy()
            
            # Evaluate the condition in the namespace
            result = eval(resolved_condition, {"__builtins__": {}}, namespace)
            return bool(result)
        except Exception as e:
            print(f"Error evaluating condition: {e}")
            return False
            
    def create_sub_context(self) -> 'WorkflowContext':
        """Create a sub-context with shared data."""
        return WorkflowContext(
            workflow_id=self.workflow_id,
            data=self.data.copy(),
            service_registry=self.service_registry
        )


class WorkflowStep(ABC):
    """Abstract base class for workflow steps.
    
    A workflow step represents an individual unit of work in a workflow.
    Different types of steps provide different functionality, such as
    executing tasks, handling conditional logic, or managing parallel execution.
    """
    
    # Class registry for step types
    STEP_REGISTRY: ClassVar[Dict[str, Type['WorkflowStep']]] = {}
    
    def __init__(self, name: str, description: str = ""):
        """Initialize workflow step.
        
        Args:
            name: Name of the step
            description: Description of the step
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        
    def __init_subclass__(cls, **kwargs):
        """Register step subclasses automatically."""
        super().__init_subclass__(**kwargs)
        if ABC not in cls.__bases__:  # Don't register abstract classes
            cls.STEP_REGISTRY[cls.__name__] = cls
        
    @abstractmethod
    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute the step with given context.
        
        Args:
            context: Workflow context for execution
            
        Returns:
            Result of step execution
        """
        pass
        
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for persistence.
        
        Returns:
            Dictionary representation of step
        """
        return {
            "id": self.id,
            "type": self.__class__.__name__,
            "name": self.name,
            "description": self.description
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Create step from dictionary.
        
        Args:
            data: Dictionary representation of step
            
        Returns:
            Instantiated step
            
        Raises:
            ValueError: If step type is unknown
        """
        step_type = data.pop("type")
        step_class = cls.STEP_REGISTRY.get(step_type)
        if not step_class:
            raise ValueError(f"Unknown step type: {step_type}")
        return step_class.from_dict(data)


class WorkflowDefinition(BaseModel):
    """Declarative workflow definition.
    
    A workflow definition describes the structure and behavior of a workflow,
    including the steps to execute, their order, and any dependencies between them.
    It is designed to be immutable, with all modifications returning new instances.
    """
    model_config = ConfigDict(extra="allow")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_step(self, step: WorkflowStep) -> 'WorkflowDefinition':
        """Add a step to the workflow.
        
        This method follows the immutable pattern, returning a new instance
        with the step added rather than modifying the current instance.
        
        Args:
            step: Step to add to the workflow
            
        Returns:
            New workflow definition with step added
        """
        # Return a new instance for immutability
        new_workflow = self.model_copy(deep=True)
        new_workflow.steps.append(step.to_dict())
        return new_workflow
    
    def get_steps(self) -> List[WorkflowStep]:
        """Get instantiated workflow steps.
        
        Returns:
            List of instantiated workflow steps
        """
        return [WorkflowStep.from_dict(step) for step in self.steps]