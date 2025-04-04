"""Workflow engine for Symphony orchestration.

This module provides the core engine for executing workflow definitions,
managing workflow state, and handling errors during workflow execution.
"""

import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Type, Set, Union

from symphony.core.registry import ServiceRegistry
from symphony.persistence.repository import Repository
from symphony.execution.workflow_tracker import WorkflowTracker, Workflow, WorkflowStatus
from symphony.orchestration.workflow_definition import WorkflowDefinition, WorkflowContext, WorkflowStep, StepResult


class WorkflowEngine:
    """Engine for executing workflow definitions.
    
    The workflow engine is responsible for executing workflow definitions,
    managing workflow state, and handling errors during workflow execution.
    It integrates with the workflow tracker to track the status of running
    workflows and their associated tasks.
    """
    
    def __init__(self, 
                service_registry: ServiceRegistry,
                workflow_definition_repository: Repository[WorkflowDefinition],
                workflow_tracker: WorkflowTracker):
        """Initialize workflow engine.
        
        Args:
            service_registry: Registry for accessing services
            workflow_definition_repository: Repository for workflow definitions
            workflow_tracker: Tracker for workflow execution
        """
        self.service_registry = service_registry
        self.workflow_definition_repository = workflow_definition_repository
        self.workflow_tracker = workflow_tracker
        
    async def execute_workflow_by_id(self, 
                                   workflow_def_id: str, 
                                   initial_context: Dict[str, Any] = None) -> Workflow:
        """Execute a workflow by its definition ID.
        
        Args:
            workflow_def_id: ID of the workflow definition
            initial_context: Initial context data for workflow execution
            
        Returns:
            The executed workflow instance
            
        Raises:
            ValueError: If workflow definition is not found
        """
        # Load the workflow definition
        workflow_def = await self.workflow_definition_repository.find_by_id(workflow_def_id)
        if not workflow_def:
            raise ValueError(f"Workflow definition {workflow_def_id} not found")
            
        return await self.execute_workflow(workflow_def, initial_context)
            
    async def execute_workflow(self, 
                             workflow_def: WorkflowDefinition, 
                             initial_context: Dict[str, Any] = None) -> Workflow:
        """Execute a workflow from its definition.
        
        Args:
            workflow_def: Workflow definition to execute
            initial_context: Initial context data for workflow execution
            
        Returns:
            The executed workflow instance
        """
        # Create a new workflow execution
        workflow = await self.workflow_tracker.create_workflow(
            name=workflow_def.name,
            description=workflow_def.description,
            metadata=workflow_def.metadata.copy()
        )
        
        # Store workflow definition ID in metadata
        workflow.metadata["workflow_definition_id"] = workflow_def.id
        await self.workflow_tracker.workflow_repository.update(workflow)
        
        # Create workflow context
        context = WorkflowContext(
            workflow_id=workflow.id,
            data=initial_context or {},
            service_registry=self.service_registry
        )
        
        # Add workflow metadata to context
        context.set("workflow_name", workflow_def.name)
        context.set("workflow_id", workflow.id)
        context.set("workflow_start_time", datetime.now().isoformat())
        
        # Update workflow status
        await self.workflow_tracker.update_workflow_status(
            workflow.id, WorkflowStatus.RUNNING
        )
        
        try:
            # Get instantiated steps
            steps = workflow_def.get_steps()
            
            # Execute each step in sequence
            for i, step in enumerate(steps):
                # Add step metadata to context
                context.set("current_step_index", i)
                context.set("current_step_name", step.name)
                context.set("current_step_id", step.id)
                context.set("total_steps", len(steps))
                
                # Execute step
                step_result = await step.execute(context)
                
                # Store step result in context
                context.set(f"step_results.{i}", {
                    "id": step.id,
                    "name": step.name,
                    "success": step_result.success,
                    "output": step_result.output,
                    "error": step_result.error
                })
                
                # If a step fails, mark workflow as failed and break
                if not step_result.success:
                    error_message = (
                        f"Step '{step.name}' failed: {step_result.error or 'Unknown error'}"
                    )
                    await self.workflow_tracker.update_workflow_status(
                        workflow.id, 
                        WorkflowStatus.FAILED,
                        error_message
                    )
                    
                    # Store error in context
                    context.set("workflow_error", error_message)
                    break
            
            # If all steps completed successfully, mark workflow as completed
            else:
                await self.workflow_tracker.update_workflow_status(
                    workflow.id, WorkflowStatus.COMPLETED
                )
                context.set("workflow_completed", True)
                context.set("workflow_end_time", datetime.now().isoformat())
        
        except Exception as e:
            # Handle any unexpected errors
            error_message = f"Workflow execution error: {str(e)}"
            await self.workflow_tracker.update_workflow_status(
                workflow.id, 
                WorkflowStatus.FAILED,
                error_message
            )
            
            # Store error details in context
            context.set("workflow_error", error_message)
            context.set("workflow_error_details", {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            })
            
        finally:
            # Store final context in workflow metadata
            workflow = await self.workflow_tracker.get_workflow(workflow.id)
            if workflow:
                workflow.metadata["context"] = context.data
                await self.workflow_tracker.workflow_repository.update(workflow)
            
        # Return the updated workflow
        return await self.workflow_tracker.get_workflow(workflow.id)