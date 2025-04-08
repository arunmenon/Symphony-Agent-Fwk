"""Step builder for Symphony workflows.

This module provides a fluent interface for building workflow steps.
"""

from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, Type
import inspect

from symphony.core.registry import ServiceRegistry
from symphony.orchestration.workflow_definition import WorkflowStep
from symphony.orchestration.steps import TaskStep, ConditionalStep, ParallelStep, LoopStep, ProcessingStep


class StepBuilder:
    """Builder for workflow steps.
    
    This class provides a fluent interface for building workflow steps,
    making it easier to create complex steps with a clean, readable syntax.
    """
    
    def __init__(self, registry: ServiceRegistry = None):
        """Initialize step builder.
        
        Args:
            registry: Service registry instance (optional)
        """
        self.registry = registry or ServiceRegistry.get_instance()
        self.name = None
        self.description = ""
        self.step_type = None
        
        # TaskStep specific
        self.agent = None
        self.task_text = None
        self.pattern = None
        self.output_key = None
        
        # ProcessingStep specific
        self.processing_function = None
        self.context_data = {}
        
        # ConditionalStep specific
        self.condition = None
        self.if_branch = None
        self.else_branch = None
        
        # ParallelStep specific
        self.steps = []
        self.max_concurrency = 5
        
        # LoopStep specific
        self.loop_step = None
        self.exit_condition = "False"
        self.max_iterations = 10
    
    def name(self, name: str) -> 'StepBuilder':
        """Set the name of the step.
        
        Args:
            name: Step name
            
        Returns:
            Self for chaining
        """
        self.name = name
        return self
    
    def description(self, description: str) -> 'StepBuilder':
        """Set the description of the step.
        
        Args:
            description: Step description
            
        Returns:
            Self for chaining
        """
        self.description = description
        return self
    
    def agent(self, agent: Any) -> 'StepBuilder':
        """Set the agent for a task step.
        
        Args:
            agent: Agent to use
            
        Returns:
            Self for chaining
        """
        self.agent = agent
        self.step_type = "task"
        return self
    
    def task(self, task_text: str) -> 'StepBuilder':
        """Set the task text for a task step.
        
        Args:
            task_text: Task description or template
            
        Returns:
            Self for chaining
        """
        self.task_text = task_text
        self.step_type = "task"
        return self
    
    def pattern(self, pattern: Any) -> 'StepBuilder':
        """Set the pattern for a task step.
        
        Args:
            pattern: Pattern to apply
            
        Returns:
            Self for chaining
        """
        self.pattern = pattern
        return self
    
    def output_key(self, key: str) -> 'StepBuilder':
        """Set the output key for storing step results in context.
        
        Args:
            key: Key to store results under
            
        Returns:
            Self for chaining
        """
        self.output_key = key
        return self
    
    def processing_function(self, func: Callable[[Dict[str, Any]], Any]) -> 'StepBuilder':
        """Set the processing function for a processing step.
        
        Args:
            func: Function to process data
            
        Returns:
            Self for chaining
        """
        self.processing_function = func
        self.step_type = "processing"
        return self
    
    def context_data(self, data: Dict[str, Any]) -> 'StepBuilder':
        """Set context data for a step.
        
        Args:
            data: Context data
            
        Returns:
            Self for chaining
        """
        self.context_data = data
        return self
    
    def condition(self, condition: str) -> 'StepBuilder':
        """Set the condition for a conditional step.
        
        Args:
            condition: Condition expression
            
        Returns:
            Self for chaining
        """
        self.condition = condition
        self.step_type = "conditional"
        return self
    
    def if_branch(self, step: WorkflowStep) -> 'StepBuilder':
        """Set the if branch for a conditional step.
        
        Args:
            step: Step to execute if condition is true
            
        Returns:
            Self for chaining
        """
        self.if_branch = step
        return self
    
    def else_branch(self, step: Optional[WorkflowStep]) -> 'StepBuilder':
        """Set the else branch for a conditional step.
        
        Args:
            step: Step to execute if condition is false
            
        Returns:
            Self for chaining
        """
        self.else_branch = step
        return self
    
    def add_step(self, step: WorkflowStep) -> 'StepBuilder':
        """Add a step to a parallel step.
        
        Args:
            step: Step to add
            
        Returns:
            Self for chaining
        """
        self.steps.append(step)
        self.step_type = "parallel"
        return self
    
    def add_steps(self, steps: List[WorkflowStep]) -> 'StepBuilder':
        """Add multiple steps to a parallel step.
        
        Args:
            steps: Steps to add
            
        Returns:
            Self for chaining
        """
        self.steps.extend(steps)
        self.step_type = "parallel"
        return self
    
    def max_concurrency(self, max_concurrency: int) -> 'StepBuilder':
        """Set the maximum concurrency for a parallel step.
        
        Args:
            max_concurrency: Maximum number of concurrent executions
            
        Returns:
            Self for chaining
        """
        self.max_concurrency = max_concurrency
        return self
    
    def loop_step(self, step: WorkflowStep) -> 'StepBuilder':
        """Set the step to loop for a loop step.
        
        Args:
            step: Step to repeat
            
        Returns:
            Self for chaining
        """
        self.loop_step = step
        self.step_type = "loop"
        return self
    
    def exit_condition(self, condition: str) -> 'StepBuilder':
        """Set the exit condition for a loop step.
        
        Args:
            condition: Exit condition expression
            
        Returns:
            Self for chaining
        """
        self.exit_condition = condition
        return self
    
    def max_iterations(self, max_iterations: int) -> 'StepBuilder':
        """Set the maximum iterations for a loop step.
        
        Args:
            max_iterations: Maximum number of iterations
            
        Returns:
            Self for chaining
        """
        self.max_iterations = max_iterations
        return self
    
    def build(self) -> WorkflowStep:
        """Build the workflow step.
        
        Returns:
            Built workflow step
            
        Raises:
            ValueError: If step type is not set or required parameters are missing
        """
        if not self.name:
            raise ValueError("Step name is required")
        
        if self.step_type == "task":
            if not self.task_text:
                raise ValueError("Task text is required for task step")
            
            agent_id = self.agent.id if hasattr(self.agent, "id") else None
            
            # Create task template
            task_template = {
                "description": self.task_text
            }
            
            # Add pattern if specified
            if self.pattern:
                pattern_name = getattr(self.pattern, "name", str(self.pattern))
                task_template["pattern"] = pattern_name
            
            # Add output key if specified
            if self.output_key:
                task_template["output_key"] = self.output_key
            
            # Add context data if any
            if self.context_data:
                task_template["context_data"] = self.context_data
            
            return TaskStep(
                name=self.name,
                description=self.description,
                task_template=task_template,
                agent_id=agent_id
            )
        
        elif self.step_type == "processing":
            if not self.processing_function:
                raise ValueError("Processing function is required for processing step")
            
            return ProcessingStep(
                name=self.name,
                description=self.description,
                processing_function=self.processing_function,
                context_data=self.context_data
            )
        
        elif self.step_type == "conditional":
            if not self.condition:
                raise ValueError("Condition is required for conditional step")
            if not self.if_branch:
                raise ValueError("If branch is required for conditional step")
            
            return ConditionalStep(
                name=self.name,
                description=self.description,
                condition=self.condition,
                if_branch=self.if_branch,
                else_branch=self.else_branch
            )
        
        elif self.step_type == "parallel":
            if not self.steps:
                raise ValueError("At least one step is required for parallel step")
            
            return ParallelStep(
                name=self.name,
                description=self.description,
                steps=self.steps,
                max_concurrency=self.max_concurrency
            )
        
        elif self.step_type == "loop":
            if not self.loop_step:
                raise ValueError("Loop step is required for loop step")
            
            return LoopStep(
                name=self.name,
                description=self.description,
                step=self.loop_step,
                exit_condition=self.exit_condition,
                max_iterations=self.max_iterations
            )
        
        else:
            raise ValueError("Step type not set. Use one of: agent(), processing_function(), condition(), add_step(), or loop_step()")