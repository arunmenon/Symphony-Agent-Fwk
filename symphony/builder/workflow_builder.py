"""Workflow builder for Symphony.

This module provides a fluent interface for building Symphony workflows.
"""

from typing import Dict, List, Any, Optional, Union, Callable, Awaitable
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.orchestration.steps import TaskStep, ConditionalStep, ParallelStep, LoopStep, ProcessingStep
from symphony.execution.workflow_tracker import Workflow
from symphony.builder.workflow_step_builder import StepBuilder

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
        self.step_builder = None
        
        # Model configuration
        self.model_config: Dict[str, str] = {}
        self.default_model: Optional[str] = None
        
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
               step: Union[TaskStep, ConditionalStep, ParallelStep, ProcessingStep],
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
            exit_condition=convergence_condition or "False"
        )
        
        self.workflow_def = self.workflow_def.add_step(loop_step)
        return self
        
    def add_processing_step(self,
                         name: str,
                         description: str,
                         processing_function: Callable[[Dict[str, Any]], Union[Any, Dict[str, Any], Awaitable[Any]]],
                         context_data: Optional[Dict[str, Any]] = None) -> 'WorkflowBuilder':
        """Add a processing step to the workflow.
        
        Args:
            name: Step name
            description: Step description
            processing_function: Function to process data
            context_data: Additional context data (optional)
            
        Returns:
            Self for chaining
        """
        if not self.workflow_def:
            raise ValueError("Workflow not created. Call create() first.")
        
        processing_step = ProcessingStep(
            name=name,
            description=description,
            processing_function=processing_function,
            context_data=context_data
        )
        
        self.workflow_def = self.workflow_def.add_step(processing_step)
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
        
    def model_assignments(self, assignments: Dict[str, str]) -> 'WorkflowBuilder':
        """Set model assignments for different agent types in the workflow.
        
        This allows specifying which models to use for different agent types,
        rather than having to set the model for each step individually.
        
        Args:
            assignments: Dictionary mapping agent types to model identifiers
                         (e.g., {"planner": "openai/gpt-4o", "explorer": "anthropic/claude-3-sonnet"})
            
        Returns:
            Self for chaining
        """
        self.model_config = assignments
        return self
        
    def default_model(self, model: str) -> 'WorkflowBuilder':
        """Set the default model to use for all agents when not specified.
        
        Args:
            model: Default model identifier to use
            
        Returns:
            Self for chaining
        """
        self.default_model = model
        return self
        
    def build_step(self) -> StepBuilder:
        """Create a step builder.
        
        Returns:
            Step builder
        """
        self.step_builder = StepBuilder(self.registry)
        return self.step_builder
        
    def add_step(self, step: Union[WorkflowStep, StepBuilder]) -> 'WorkflowBuilder':
        """Add a step to the workflow.
        
        Args:
            step: Step to add or step builder
            
        Returns:
            Self for chaining
        """
        if not self.workflow_def:
            raise ValueError("Workflow not created. Call create() first.")
            
        # Apply model configurations to StepBuilder if needed
        if isinstance(step, StepBuilder):
            # If step has an agent_type but no model, apply model from workflow config
            if step.agent_type and not step.model:
                if step.agent_type in self.model_config:
                    step.model(self.model_config[step.agent_type])
                elif self.default_model:
                    step.model(self.default_model)
            
            # Build the step
            step = step.build()
        
        # For WorkflowStep instances, we can't modify them directly
        # But for TaskStep, we can check if the task template contains agent_type
        # and if so, apply model from workflow config
        elif isinstance(step, TaskStep):
            task_template = step.task_template
            if isinstance(task_template, dict):
                agent_type = task_template.get("agent_type")
                if agent_type and "model" not in task_template:
                    if agent_type in self.model_config:
                        # We'd need to modify the task_template, but this isn't ideal
                        # as WorkflowStep instances are meant to be immutable
                        # This is why using StepBuilder is preferred
                        pass
            
        self.workflow_def = self.workflow_def.add_step(step)
        return self
    
    def build(self) -> WorkflowDefinition:
        """Build the workflow definition.
        
        This method finalizes the workflow definition, including any model
        configurations in the workflow metadata.
        
        Returns:
            Workflow definition
        """
        if not self.workflow_def:
            raise ValueError("Workflow not created. Call create() first.")
        
        # Add model configuration to metadata if present
        if self.model_config or self.default_model:
            metadata = self.workflow_def.metadata.copy()
            
            # Store model assignments in metadata
            if self.model_config:
                metadata["model_assignments"] = self.model_config
                
            # Store default model
            if self.default_model:
                metadata["default_model"] = self.default_model
                
            # Update workflow definition with new metadata
            self.workflow_def.metadata = metadata
        
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