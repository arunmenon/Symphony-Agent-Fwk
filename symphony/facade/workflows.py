"""Workflow facade module for Symphony.

This module provides a clean, domain-specific interface for working with
Symphony workflows, abstracting away the details of the registry pattern
and other implementation details.
"""

from typing import Dict, List, Any, Optional, Union
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.persistence.repository import Repository
from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.orchestration.steps import TaskStep, ConditionalStep, ParallelStep, LoopStep
from symphony.execution.workflow_tracker import Workflow, WorkflowStatus


class WorkflowFacade:
    """Facade for working with Symphony workflows.
    
    This class provides a clean interface for creating, managing, and executing
    workflows, abstracting away the details of the registry pattern.
    """
    
    def __init__(self, registry: ServiceRegistry = None):
        """Initialize workflow facade.
        
        Args:
            registry: Service registry instance (optional)
        """
        self.registry = registry or ServiceRegistry.get_instance()
        
    async def create_workflow(self, name: str, description: str = "", metadata: Dict[str, Any] = None) -> WorkflowDefinition:
        """Create a new workflow definition.
        
        Args:
            name: Name of the workflow
            description: Description of the workflow
            metadata: Additional metadata
            
        Returns:
            New workflow definition
        """
        workflow_def = WorkflowDefinition(
            name=name,
            description=description,
            metadata=metadata or {}
        )
        
        return workflow_def
    
    async def add_task_step(self, 
                          workflow: WorkflowDefinition, 
                          name: str, 
                          description: str, 
                          task_template: Dict[str, Any],
                          agent_id: Optional[str] = None) -> WorkflowDefinition:
        """Add a task step to a workflow.
        
        Args:
            workflow: Workflow definition
            name: Step name
            description: Step description
            task_template: Task template
            agent_id: Agent ID (optional)
            
        Returns:
            Updated workflow definition
        """
        task_step = TaskStep(
            name=name,
            description=description,
            task_template=task_template,
            agent_id=agent_id
        )
        
        return workflow.add_step(task_step)
    
    async def add_conditional_step(self,
                                workflow: WorkflowDefinition,
                                name: str,
                                description: str,
                                condition: str,
                                if_branch: Union[TaskStep, ConditionalStep, ParallelStep, LoopStep],
                                else_branch: Optional[Union[TaskStep, ConditionalStep, ParallelStep, LoopStep]] = None) -> WorkflowDefinition:
        """Add a conditional step to a workflow.
        
        Args:
            workflow: Workflow definition
            name: Step name
            description: Step description
            condition: Condition expression
            if_branch: Step to execute if condition is true
            else_branch: Step to execute if condition is false (optional)
            
        Returns:
            Updated workflow definition
        """
        conditional_step = ConditionalStep(
            name=name,
            description=description,
            condition=condition,
            if_branch=if_branch,
            else_branch=else_branch
        )
        
        return workflow.add_step(conditional_step)
    
    async def add_parallel_step(self,
                             workflow: WorkflowDefinition,
                             name: str,
                             description: str,
                             steps: List[Union[TaskStep, ConditionalStep, ParallelStep, LoopStep]]) -> WorkflowDefinition:
        """Add a parallel step to a workflow.
        
        Args:
            workflow: Workflow definition
            name: Step name
            description: Step description
            steps: Steps to execute in parallel
            
        Returns:
            Updated workflow definition
        """
        parallel_step = ParallelStep(
            name=name,
            description=description,
            steps=steps
        )
        
        return workflow.add_step(parallel_step)
    
    async def add_loop_step(self,
                         workflow: WorkflowDefinition,
                         name: str,
                         description: str,
                         step: Union[TaskStep, ConditionalStep, ParallelStep],
                         max_iterations: int,
                         convergence_condition: Optional[str] = None) -> WorkflowDefinition:
        """Add a loop step to a workflow.
        
        Args:
            workflow: Workflow definition
            name: Step name
            description: Step description
            step: Step to repeat
            max_iterations: Maximum number of iterations
            convergence_condition: Condition for early exit (optional)
            
        Returns:
            Updated workflow definition
        """
        loop_step = LoopStep(
            name=name,
            description=description,
            step=step,
            max_iterations=max_iterations,
            convergence_condition=convergence_condition
        )
        
        return workflow.add_step(loop_step)
    
    async def save_workflow(self, workflow: WorkflowDefinition) -> str:
        """Save a workflow definition.
        
        Args:
            workflow: Workflow definition
            
        Returns:
            Workflow definition ID
        """
        try:
            workflow_def_repo = self.registry.get_repository("workflow_definition")
            return await workflow_def_repo.save(workflow)
        except ValueError:
            # Repository might not be registered yet
            from symphony.persistence.memory_repository import InMemoryRepository
            workflow_def_repo = InMemoryRepository(WorkflowDefinition)
            self.registry.register_repository("workflow_definition", workflow_def_repo)
            return await workflow_def_repo.save(workflow)
    
    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get a workflow definition by ID.
        
        Args:
            workflow_id: Workflow definition ID
            
        Returns:
            Workflow definition or None if not found
        """
        try:
            workflow_def_repo = self.registry.get_repository("workflow_definition")
            return await workflow_def_repo.find_by_id(workflow_id)
        except ValueError:
            return None
    
    async def execute_workflow(self, 
                            workflow: WorkflowDefinition, 
                            initial_context: Dict[str, Any] = None,
                            auto_checkpoint: bool = True,
                            resume_from_checkpoint: bool = True,
                            model_assignments: Optional[Dict[str, str]] = None) -> Workflow:
        """Execute a workflow.
        
        Args:
            workflow: Workflow definition
            initial_context: Initial context data (optional)
            auto_checkpoint: Whether to automatically create checkpoints during execution
            resume_from_checkpoint: Whether to try resuming from a checkpoint if available
            model_assignments: Optional model assignments for specific steps
            
        Returns:
            Executed workflow
        """
        # Make sure workflow is saved first
        if not workflow.id:
            await self.save_workflow(workflow)
        
        # Get workflow engine
        try:
            workflow_engine = self.registry.get_service("workflow_engine")
        except ValueError:
            # Engine might not be registered yet
            # Make sure required dependencies are registered
            if "workflow_definition" not in self.registry.repositories:
                from symphony.persistence.memory_repository import InMemoryRepository
                self.registry.register_repository(
                    "workflow_definition", InMemoryRepository(WorkflowDefinition)
                )
            
            if "workflow" not in self.registry.repositories:
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
        return await workflow_engine.execute_workflow(
            workflow_def=workflow, 
            initial_context=initial_context,
            auto_checkpoint=auto_checkpoint,
            resume_from_checkpoint=resume_from_checkpoint,
            model_assignments=model_assignments
        )
    
    async def create_critic_revise_workflow(self,
                                        name: str,
                                        main_prompt: str,
                                        critique_prompt: str,
                                        revision_prompt: str,
                                        agent_id: Optional[str] = None,
                                        critic_agent_id: Optional[str] = None) -> WorkflowDefinition:
        """Create a critic-revision workflow.
        
        Args:
            name: Workflow name
            main_prompt: Initial task prompt
            critique_prompt: Critique prompt
            revision_prompt: Revision prompt
            agent_id: Agent ID for main task (optional)
            critic_agent_id: Agent ID for critic (optional)
            
        Returns:
            Workflow definition
        """
        templates = self.registry.get_service("workflow_templates")
        return templates.critic_revise(
            name=name,
            main_prompt=main_prompt,
            critique_prompt=critique_prompt,
            revision_prompt=revision_prompt,
            agent_id=agent_id,
            critic_agent_id=critic_agent_id
        )
    
    async def create_parallel_experts_workflow(self,
                                           name: str,
                                           prompt: str,
                                           expert_roles: List[str],
                                           summary_prompt: str,
                                           agent_id: Optional[str] = None) -> WorkflowDefinition:
        """Create a parallel experts workflow.
        
        Args:
            name: Workflow name
            prompt: Base prompt for all experts
            expert_roles: List of expert roles
            summary_prompt: Prompt for summary step
            agent_id: Agent ID (optional)
            
        Returns:
            Workflow definition
        """
        templates = self.registry.get_service("workflow_templates")
        return templates.parallel_experts(
            name=name,
            prompt=prompt,
            expert_roles=expert_roles,
            summary_prompt=summary_prompt,
            agent_id=agent_id
        )
    
    async def create_iterative_refinement_workflow(self,
                                               name: str,
                                               initial_prompt: str,
                                               feedback_prompt: str,
                                               max_iterations: int = 3,
                                               convergence_condition: Optional[str] = None,
                                               agent_id: Optional[str] = None,
                                               feedback_agent_id: Optional[str] = None) -> WorkflowDefinition:
        """Create an iterative refinement workflow.
        
        Args:
            name: Workflow name
            initial_prompt: Initial prompt
            feedback_prompt: Feedback prompt
            max_iterations: Maximum iterations
            convergence_condition: Condition for early exit (optional)
            agent_id: Agent ID for main task (optional)
            feedback_agent_id: Agent ID for feedback (optional)
            
        Returns:
            Workflow definition
        """
        templates = self.registry.get_service("workflow_templates")
        return templates.iterative_refinement(
            name=name,
            initial_prompt=initial_prompt,
            feedback_prompt=feedback_prompt,
            max_iterations=max_iterations,
            convergence_condition=convergence_condition,
            agent_id=agent_id,
            feedback_agent_id=feedback_agent_id
        )
    
    async def create_chain_of_thought_workflow(self,
                                           name: str,
                                           prompt: str,
                                           agent_id: Optional[str] = None) -> WorkflowDefinition:
        """Create a chain of thought workflow.
        
        Args:
            name: Workflow name
            prompt: Reasoning prompt
            agent_id: Agent ID (optional)
            
        Returns:
            Workflow definition
        """
        templates = self.registry.get_service("workflow_templates")
        return templates.chain_of_thought(
            name=name,
            prompt=prompt,
            agent_id=agent_id
        )
    
    async def get_workflow_results(self, workflow_id: str) -> Dict[str, Any]:
        """Get results from an executed workflow.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Workflow results
        """
        # Get workflow
        workflow_tracker = self.registry.get_service("workflow_tracker")
        workflow = await workflow_tracker.get_workflow(workflow_id)
        
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # Extract results from workflow context
        if "context" not in workflow.metadata:
            return {
                "status": workflow.status,
                "error": workflow.error
            }
        
        context = workflow.metadata["context"]
        
        # Organize step results
        results = {
            "status": workflow.status,
            "error": workflow.error,
            "steps": {}
        }
        
        # Extract step results
        for key, value in context.items():
            if key.startswith("step.") and ".result" in key:
                step_id = key.split(".")[1]
                step_name = context.get(f"step.{step_id}.name", f"Step {step_id}")
                results["steps"][step_name] = value
            elif key.startswith("step.") and ".results" in key:
                step_id = key.split(".")[1]
                step_name = context.get(f"step.{step_id}.name", f"Step {step_id}")
                results["steps"][step_name] = value
        
        return results