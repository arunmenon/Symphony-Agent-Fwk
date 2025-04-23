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
        self._name = None
        self._description = ""
        self.step_type = None
        
        # TaskStep specific
        self._agent = None
        self._agent_type = None  # New: For agent creation by type
        self._model = None  # New: Model identifier for the agent
        self._task_text = None
        self._pattern = None
        self._output_key = None
        
        # ProcessingStep specific
        self._processing_function = None
        self._context_data = {}
        
        # ConditionalStep specific
        self._condition = None
        self._if_branch = None
        self._else_branch = None
        
        # ParallelStep specific
        self._steps = []
        self._max_concurrency = 5
        
        # LoopStep specific
        self._loop_step = None
        self._exit_condition = "False"
        self._max_iterations = 10
    
    def name(self, name: str) -> 'StepBuilder':
        """Set the name of the step.
        
        Args:
            name: Step name
            
        Returns:
            Self for chaining
        """
        self._name = name
        return self
    
    def description(self, description: str) -> 'StepBuilder':
        """Set the description of the step.
        
        Args:
            description: Step description
            
        Returns:
            Self for chaining
        """
        self._description = description
        return self
    
    def agent(self, agent: Any) -> 'StepBuilder':
        """Set the agent for a task step.
        
        Args:
            agent: Agent to use
            
        Returns:
            Self for chaining
        """
        self._agent = agent
        self.step_type = "task"
        return self
        
    def agent_type(self, agent_type: str) -> 'StepBuilder':
        """Set the agent type for a task step.
        
        Instead of providing a specific agent instance, this allows specifying
        an agent type that will be created with the specified model when the
        workflow is executed.
        
        Args:
            agent_type: Type of agent to create (e.g., "planner", "explorer")
            
        Returns:
            Self for chaining
        """
        self._agent_type = agent_type
        self.step_type = "task"
        return self
        
    def model(self, model: str) -> 'StepBuilder':
        """Set the model to use for the agent in this step.
        
        The model can be specified in LiteLLM format: "provider/model_name"
        (e.g., "openai/gpt-4o", "anthropic/claude-3-opus").
        
        Args:
            model: Model identifier to use
            
        Returns:
            Self for chaining
        """
        self._model = model
        return self
    
    def task(self, task_text: str) -> 'StepBuilder':
        """Set the task text for a task step.
        
        Args:
            task_text: Task description or template
            
        Returns:
            Self for chaining
        """
        self._task_text = task_text
        self.step_type = "task"
        return self
    
    def pattern(self, pattern: Any) -> 'StepBuilder':
        """Set the pattern for a task step.
        
        Args:
            pattern: Pattern to apply
            
        Returns:
            Self for chaining
        """
        self._pattern = pattern
        return self
    
    def output_key(self, key: str) -> 'StepBuilder':
        """Set the output key for storing step results in context.
        
        Args:
            key: Key to store results under
            
        Returns:
            Self for chaining
        """
        self._output_key = key
        return self
    
    def processing_function(self, func: Callable[[Dict[str, Any]], Any]) -> 'StepBuilder':
        """Set the processing function for a processing step.
        
        Args:
            func: Function to process data
            
        Returns:
            Self for chaining
        """
        self._processing_function = func
        self.step_type = "processing"
        return self
    
    def context_data(self, data: Dict[str, Any]) -> 'StepBuilder':
        """Set context data for a step.
        
        Args:
            data: Context data
            
        Returns:
            Self for chaining
        """
        self._context_data = data
        return self
    
    def condition(self, condition: str) -> 'StepBuilder':
        """Set the condition for a conditional step.
        
        Args:
            condition: Condition expression
            
        Returns:
            Self for chaining
        """
        self._condition = condition
        self.step_type = "conditional"
        return self
    
    def if_branch(self, step: WorkflowStep) -> 'StepBuilder':
        """Set the if branch for a conditional step.
        
        Args:
            step: Step to execute if condition is true
            
        Returns:
            Self for chaining
        """
        self._if_branch = step
        return self
    
    def else_branch(self, step: Optional[WorkflowStep]) -> 'StepBuilder':
        """Set the else branch for a conditional step.
        
        Args:
            step: Step to execute if condition is false
            
        Returns:
            Self for chaining
        """
        self._else_branch = step
        return self
    
    def add_step(self, step: WorkflowStep) -> 'StepBuilder':
        """Add a step to a parallel step.
        
        Args:
            step: Step to add
            
        Returns:
            Self for chaining
        """
        self._steps.append(step)
        self.step_type = "parallel"
        return self
    
    def add_steps(self, steps: List[WorkflowStep]) -> 'StepBuilder':
        """Add multiple steps to a parallel step.
        
        Args:
            steps: Steps to add
            
        Returns:
            Self for chaining
        """
        self._steps.extend(steps)
        self.step_type = "parallel"
        return self
    
    def max_concurrency(self, max_concurrency: int) -> 'StepBuilder':
        """Set the maximum concurrency for a parallel step.
        
        Args:
            max_concurrency: Maximum number of concurrent executions
            
        Returns:
            Self for chaining
        """
        self._max_concurrency = max_concurrency
        return self
    
    def loop_step(self, step: WorkflowStep) -> 'StepBuilder':
        """Set the step to loop for a loop step.
        
        Args:
            step: Step to repeat
            
        Returns:
            Self for chaining
        """
        self._loop_step = step
        self.step_type = "loop"
        return self
    
    def exit_condition(self, condition: str) -> 'StepBuilder':
        """Set the exit condition for a loop step.
        
        Args:
            condition: Exit condition expression
            
        Returns:
            Self for chaining
        """
        self._exit_condition = condition
        return self
    
    def max_iterations(self, max_iterations: int) -> 'StepBuilder':
        """Set the maximum iterations for a loop step.
        
        Args:
            max_iterations: Maximum number of iterations
            
        Returns:
            Self for chaining
        """
        self._max_iterations = max_iterations
        return self
    
    def build(self) -> WorkflowStep:
        """Build the workflow step.
        
        Returns:
            Built workflow step
            
        Raises:
            ValueError: If step type is not set or required parameters are missing
        """
        if not self._name:
            raise ValueError("Step name is required")
        
        if self.step_type == "task":
            if not self._task_text:
                raise ValueError("Task text is required for task step")
            
            # Create task template
            task_template = {
                "description": self._task_text
            }
            
            # Add pattern if specified
            if self._pattern:
                pattern_name = getattr(self._pattern, "name", str(self._pattern))
                task_template["pattern"] = pattern_name
            
            # Add output key if specified
            if self._output_key:
                task_template["output_key"] = self._output_key
            
            # Add context data if any
            if self._context_data:
                task_template["context_data"] = self._context_data
            
            # Add model information if specified
            if self._model:
                task_template["model"] = self._model
            
            # Handle agent information
            agent_id = None
            if self._agent:
                agent_id = self._agent.id if hasattr(self._agent, "id") else None
                
                # If both agent instance and model are specified, also add model to template
                # This allows overriding the agent's default model
                if self._model and hasattr(self._agent, "model"):
                    task_template["model"] = self._model
                    
            # Add agent_type information if provided
            if self._agent_type:
                task_template["agent_type"] = self._agent_type
                
            # If no agent provided but agent_type and model are specified,
            # these will be used to create an agent instance during execution
            
            return TaskStep(
                name=self._name,
                description=self._description,
                task_template=task_template,
                agent_id=agent_id
            )
        
        elif self.step_type == "processing":
            if not self._processing_function:
                raise ValueError("Processing function is required for processing step")
            
            return ProcessingStep(
                name=self._name,
                description=self._description,
                processing_function=self._processing_function,
                context_data=self._context_data
            )
        
        elif self.step_type == "conditional":
            if not self._condition:
                raise ValueError("Condition is required for conditional step")
            if not self._if_branch:
                raise ValueError("If branch is required for conditional step")
            
            return ConditionalStep(
                name=self._name,
                description=self._description,
                condition=self._condition,
                if_branch=self._if_branch,
                else_branch=self._else_branch
            )
        
        elif self.step_type == "parallel":
            if not self._steps:
                raise ValueError("At least one step is required for parallel step")
            
            return ParallelStep(
                name=self._name,
                description=self._description,
                steps=self._steps,
                max_concurrency=self._max_concurrency
            )
        
        elif self.step_type == "loop":
            if not self._loop_step:
                raise ValueError("Loop step is required for loop step")
            
            return LoopStep(
                name=self._name,
                description=self._description,
                step=self._loop_step,
                exit_condition=self._exit_condition,
                max_iterations=self._max_iterations
            )
        
        else:
            raise ValueError("Step type not set. Use one of: agent(), processing_function(), condition(), add_step(), or loop_step()")


# Create a proper class instead of an alias for API compatibility
class WorkflowStepBuilder(StepBuilder):
    """Builder for workflow steps.
    
    This class provides a fluent interface for building workflow steps,
    making it easier to create complex steps with a clean, readable syntax.
    
    This is an alias of StepBuilder for backward compatibility.
    """
    pass