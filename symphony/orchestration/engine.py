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

# Import state management components (conditionally to avoid import errors)
try:
    from symphony.core.state import CheckpointManager
except ImportError:
    CheckpointManager = None


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
                             initial_context: Dict[str, Any] = None,
                             auto_checkpoint: bool = True,
                             resume_from_checkpoint: bool = True,
                             model_assignments: Optional[Dict[str, str]] = None) -> Workflow:
        """Execute a workflow from its definition.
        
        Args:
            workflow_def: Workflow definition to execute
            initial_context: Initial context data for workflow execution
            auto_checkpoint: Whether to automatically create checkpoints during execution
            resume_from_checkpoint: Whether to try resuming from a checkpoint if available
            
        Returns:
            The executed workflow instance
        """
        # Check if state management is available and enabled
        checkpoint_manager = None
        if (auto_checkpoint or resume_from_checkpoint) and CheckpointManager is not None:
            checkpoint_manager = self.service_registry.get("checkpoint_manager")
        
        # Check for existing workflow checkpoint to resume
        resumed_workflow = None
        if resume_from_checkpoint and checkpoint_manager:
            try:
                # Look for checkpoints related to this workflow definition
                checkpoint_pattern = f"workflow_*_{workflow_def.name.replace(' ', '_').lower()}"
                checkpoints = await self._find_matching_checkpoints(checkpoint_pattern)
                
                if checkpoints:
                    # Sort by creation time (newest first)
                    latest_checkpoint = sorted(checkpoints, key=lambda c: c.get("created_at", ""), reverse=True)[0]
                    
                    # Restore from checkpoint
                    await checkpoint_manager.restore_checkpoint(
                        self.service_registry.get("symphony_instance"),
                        latest_checkpoint["id"]
                    )
                    
                    # Extract workflow ID from checkpoint name
                    # Format: workflow_{workflow_id}_{stage}
                    checkpoint_name = latest_checkpoint.get("name", "")
                    if checkpoint_name.startswith("workflow_"):
                        parts = checkpoint_name.split("_")
                        if len(parts) > 1:
                            workflow_id = parts[1]
                            
                            # Try to get the workflow
                            resumed_workflow = await self.workflow_tracker.get_workflow(workflow_id)
                            
                            if resumed_workflow and resumed_workflow.status != WorkflowStatus.COMPLETED:
                                # We found a workflow in progress, so we'll resume it
                                print(f"Resuming workflow {workflow_id} from checkpoint {latest_checkpoint['id']}")
                                
                                # TODO: Implement full workflow resumption logic
                                # For now, we'll just return the resumed workflow
                                # In the future, we should continue execution from where it left off
                                return resumed_workflow
            except Exception as e:
                # Log resumption error but continue with fresh execution
                print(f"Warning: Failed to resume workflow from checkpoint: {e}")
        
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
        context_data = initial_context.copy() if initial_context else {}
        
        # Add model assignments to context if provided
        if model_assignments:
            context_data["model_assignments"] = model_assignments
        elif "model_assignments" in workflow_def.metadata:
            # Use model assignments from workflow metadata
            context_data["model_assignments"] = workflow_def.metadata["model_assignments"]
            
        # Add default model to context if present in workflow metadata
        if "default_model" in workflow_def.metadata:
            context_data["default_model"] = workflow_def.metadata["default_model"]
            
        context = WorkflowContext(
            workflow_id=workflow.id,
            data=context_data,
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
        
        # Create initial checkpoint if enabled
        if checkpoint_manager:
            try:
                checkpoint_id = await checkpoint_manager.create_checkpoint(
                    self.service_registry.get("symphony_instance"),
                    name=f"workflow_{workflow.id}_start",
                    metadata={
                        "workflow_id": workflow.id,
                        "workflow_name": workflow_def.name,
                        "stage": "start",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                context.set("initial_checkpoint_id", checkpoint_id)
            except Exception as e:
                # Log checkpoint error but continue execution
                print(f"Warning: Failed to create initial checkpoint: {e}")
        
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
                
                # Create checkpoint after step if enabled
                if checkpoint_manager and (i > 0 and i % 3 == 0):  # Checkpoint every 3 steps
                    try:
                        checkpoint_id = await checkpoint_manager.create_checkpoint(
                            self.service_registry.get("symphony_instance"),
                            name=f"workflow_{workflow.id}_step_{i}",
                            metadata={
                                "workflow_id": workflow.id,
                                "workflow_name": workflow_def.name,
                                "step_index": i,
                                "step_name": step.name,
                                "stage": "mid_execution",
                                "timestamp": datetime.now().isoformat()
                            }
                        )
                        context.set(f"checkpoint_after_step_{i}", checkpoint_id)
                    except Exception as e:
                        # Log checkpoint error but continue execution
                        print(f"Warning: Failed to create checkpoint after step {i}: {e}")
                
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
                    
                    # Create error checkpoint if enabled
                    if checkpoint_manager:
                        try:
                            checkpoint_id = await checkpoint_manager.create_checkpoint(
                                self.service_registry.get("symphony_instance"),
                                name=f"workflow_{workflow.id}_error",
                                metadata={
                                    "workflow_id": workflow.id,
                                    "workflow_name": workflow_def.name,
                                    "error_step_index": i,
                                    "error_step_name": step.name,
                                    "error_message": error_message,
                                    "stage": "error",
                                    "timestamp": datetime.now().isoformat()
                                }
                            )
                            context.set("error_checkpoint_id", checkpoint_id)
                        except Exception as e:
                            # Log checkpoint error
                            print(f"Warning: Failed to create error checkpoint: {e}")
                    
                    break
            
            # If all steps completed successfully, mark workflow as completed
            else:
                await self.workflow_tracker.update_workflow_status(
                    workflow.id, WorkflowStatus.COMPLETED
                )
                context.set("workflow_completed", True)
                context.set("workflow_end_time", datetime.now().isoformat())
                
                # Create completion checkpoint if enabled
                if checkpoint_manager:
                    try:
                        checkpoint_id = await checkpoint_manager.create_checkpoint(
                            self.service_registry.get("symphony_instance"),
                            name=f"workflow_{workflow.id}_complete",
                            metadata={
                                "workflow_id": workflow.id,
                                "workflow_name": workflow_def.name,
                                "stage": "complete",
                                "timestamp": datetime.now().isoformat()
                            }
                        )
                        context.set("completion_checkpoint_id", checkpoint_id)
                    except Exception as e:
                        # Log checkpoint error
                        print(f"Warning: Failed to create completion checkpoint: {e}")
        
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
            
            # Create error checkpoint if enabled
            if checkpoint_manager:
                try:
                    checkpoint_id = await checkpoint_manager.create_checkpoint(
                        self.service_registry.get("symphony_instance"),
                        name=f"workflow_{workflow.id}_exception",
                        metadata={
                            "workflow_id": workflow.id,
                            "workflow_name": workflow_def.name,
                            "exception": str(e),
                            "stage": "exception",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    context.set("exception_checkpoint_id", checkpoint_id)
                except Exception as checkpoint_error:
                    # Log checkpoint error
                    print(f"Warning: Failed to create exception checkpoint: {checkpoint_error}")
            
        finally:
            # Store final context in workflow metadata
            workflow = await self.workflow_tracker.get_workflow(workflow.id)
            if workflow:
                workflow.metadata["context"] = context.data
                await self.workflow_tracker.workflow_repository.update(workflow)
            
        # Return the updated workflow
        return await self.workflow_tracker.get_workflow(workflow.id)
        
    async def _find_matching_checkpoints(self, name_pattern: str) -> List[Dict[str, Any]]:
        """Find checkpoints matching a name pattern.
        
        Args:
            name_pattern: Pattern to match checkpoint names against
            
        Returns:
            List of matching checkpoints
        """
        if CheckpointManager is None:
            return []
            
        checkpoint_manager = self.service_registry.get("checkpoint_manager")
        if not checkpoint_manager:
            return []
            
        try:
            # List all checkpoints
            checkpoints = await checkpoint_manager.list_checkpoints()
            
            # Filter by name pattern
            import fnmatch
            matching = []
            for checkpoint in checkpoints:
                if fnmatch.fnmatch(checkpoint.get("name", ""), name_pattern):
                    matching.append(checkpoint)
                    
            return matching
            
        except Exception as e:
            print(f"Error finding matching checkpoints: {e}")
            return []