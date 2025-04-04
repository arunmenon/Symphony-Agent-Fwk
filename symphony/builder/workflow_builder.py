"""Workflow builder for Symphony.

This module provides a fluent interface for building Symphony workflows.
"""

from typing import Dict, List, Any, Optional, Union, Callable
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.orchestration.steps import TaskStep, ConditionalStep, ParallelStep, LoopStep
from symphony.execution.workflow_tracker import Workflow

class WorkflowBuilder:
    """Builder for Symphony workflows.
    
    This class provides a fluent interface for building workflows, making it
    easier to create complex workflows with a clean, readable syntax.
    """
    
    def __init__(self, registry: ServiceRegistry = None):
        """Initialize workflow builder.
        
        Args:
            registry: Service registry instance (optional)
        """
        self.registry = registry or ServiceRegistry.get_instance()
        self.workflow_def: Optional[WorkflowDefinition] = None
        self.initial_context: Dict[str, Any] = {}
        
    def create(self, name: str, description: str = "", metadata: Dict[str, Any] = None) -> 'WorkflowBuilder':
        """Create a new workflow definition.
        
        Args:
            name: Name of the workflow
            description: Description of the workflow
            metadata: Additional metadata
            
        Returns:
            Self for chaining
        """
        self.workflow_def = WorkflowDefinition(
            name=name,
            description=description,
            metadata=metadata or {}
        )
        return self
    
    def add_task(self, 
               name: str, 
               description: str, 
               task_template: Dict[str, Any],
               agent_id: Optional[str] = None) -> 'WorkflowBuilder':
        """Add a task step to the workflow.
        
        Args:
            name: Step name
            description: Step description
            task_template: Task template
            agent_id: Agent ID (optional)
            
        Returns:
            Self for chaining
        """
        if not self.workflow_def:
            raise ValueError("Workflow not created. Call create() first.")
        
        task_step = TaskStep(
            name=name,
            description=description,
            task_template=task_template,
            agent_id=agent_id
        )
        
        self.workflow_def = self.workflow_def.add_step(task_step)
        return self
    
    def add_conditional(self,
                      name: str,
                      description: str,
                      condition: str,
                      if_branch: Union[TaskStep, ConditionalStep, ParallelStep, LoopStep],
                      else_branch: Optional[Union[TaskStep, ConditionalStep, ParallelStep, LoopStep]] = None) -> 'WorkflowBuilder':
        """Add a conditional step to the workflow.
        
        Args:
            name: Step name
            description: Step description
            condition: Condition expression
            if_branch: Step to execute if condition is true
            else_branch: Step to execute if condition is false (optional)
            
        Returns:
            Self for chaining
        """
        if not self.workflow_def:
            raise ValueError("Workflow not created. Call create() first.")
        
        conditional_step = ConditionalStep(
            name=name,
            description=description,
            condition=condition,
            if_branch=if_branch,
            else_branch=else_branch
        )
        
        self.workflow_def = self.workflow_def.add_step(conditional_step)
        return self
    
    def add_parallel(self,
                   name: str,
                   description: str,
                   steps: List[Union[TaskStep, ConditionalStep, ParallelStep, LoopStep]]) -> 'WorkflowBuilder':
        """Add a parallel step to the workflow.
        
        Args:
            name: Step name
            description: Step description
            steps: Steps to execute in parallel
            
        Returns:
            Self for chaining
        """
        if not self.workflow_def:
            raise ValueError("Workflow not created. Call create() first.")
        
        parallel_step = ParallelStep(
            name=name,
            description=description,
            steps=steps
        )
        
        self.workflow_def = self.workflow_def.add_step(parallel_step)
        return self
    
    def add_loop(self,
               name: str,
               description: str,
               step: Union[TaskStep, ConditionalStep, ParallelStep],
               max_iterations: int,
               convergence_condition: Optional[str] = None) -> 'WorkflowBuilder':
        """Add a loop step to the workflow.
        
        Args:
            name: Step name
            description: Step description
            step: Step to repeat
            max_iterations: Maximum number of iterations
            convergence_condition: Condition for early exit (optional)
            
        Returns:
            Self for chaining
        """
        if not self.workflow_def:
            raise ValueError("Workflow not created. Call create() first.")
        
        loop_step = LoopStep(
            name=name,
            description=description,
            step=step,
            max_iterations=max_iterations,
            convergence_condition=convergence_condition
        )
        
        self.workflow_def = self.workflow_def.add_step(loop_step)
        return self
    
    def with_context(self, context: Dict[str, Any]) -> 'WorkflowBuilder':
        """Set initial context for workflow execution.
        
        Args:
            context: Initial context data
            
        Returns:
            Self for chaining
        """
        self.initial_context = context
        return self
    
    def build(self) -> WorkflowDefinition:
        """Build the workflow definition.
        
        Returns:
            Workflow definition
        """
        if not self.workflow_def:
            raise ValueError("Workflow not created. Call create() first.")
        
        return self.workflow_def
    
    async def save(self) -> str:
        """Save the workflow definition.
        
        Returns:
            Workflow definition ID
        """
        if not self.workflow_def:
            raise ValueError("Workflow not created. Call create() first.")
        
        try:
            workflow_def_repo = self.registry.get_repository("workflow_definition")
            return await workflow_def_repo.save(self.workflow_def)
        except ValueError:
            # Repository might not be registered yet
            from symphony.persistence.memory_repository import InMemoryRepository
            workflow_def_repo = InMemoryRepository(WorkflowDefinition)
            self.registry.register_repository("workflow_definition", workflow_def_repo)
            return await workflow_def_repo.save(self.workflow_def)
    
    async def execute(self) -> Workflow:
        """Execute the workflow.
        
        Returns:
            Executed workflow
        """
        if not self.workflow_def:
            raise ValueError("Workflow not created. Call create() first.")
        
        # Save workflow if not already saved
        if not self.workflow_def.id:
            await self.save()
        
        # Get workflow engine
        try:
            workflow_engine = self.registry.get_service("workflow_engine")
        except ValueError:
            # Engine might not be registered yet
            # Register required dependencies
            if "workflow_definition" not in self.registry.repositories:
                from symphony.persistence.memory_repository import InMemoryRepository
                self.registry.register_repository(
                    "workflow_definition", InMemoryRepository(WorkflowDefinition)
                )
            
            if "workflow" not in self.registry.repositories:
                from symphony.execution.workflow_tracker import Workflow
                from symphony.persistence.memory_repository import InMemoryRepository
                self.registry.register_repository(
                    "workflow", InMemoryRepository(Workflow)
                )
            
            if "task" not in self.registry.repositories:
                from symphony.core.task import Task
                from symphony.persistence.memory_repository import InMemoryRepository
                self.registry.register_repository(
                    "task", InMemoryRepository(Task)
                )
            
            # Register remaining orchestration components
            from symphony.orchestration import register_orchestration_components
            register_orchestration_components(self.registry)
            
            # Get the now-registered engine
            workflow_engine = self.registry.get_service("workflow_engine")
        
        # Execute workflow
        return await workflow_engine.execute_workflow(self.workflow_def, self.initial_context)