"""Symphony Orchestration Layer.

This package provides components for orchestrating complex workflows of tasks and agents,
enabling advanced patterns of agent interaction, control flow, and state management.
"""

from symphony.orchestration.workflow_definition import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowContext,
    StepResult
)

from symphony.orchestration.steps import (
    TaskStep,
    ConditionalStep,
    ParallelStep,
    LoopStep
)

from symphony.orchestration.engine import WorkflowEngine
from symphony.orchestration.templates import WorkflowTemplates

# Update Symphony's core registry to support orchestration components
from symphony.core.registry import ServiceRegistry


def register_orchestration_components(
    registry: ServiceRegistry,
    workflow_definition_repository=None,
    symphony_instance=None
) -> None:
    """Register orchestration components in the service registry.
    
    Args:
        registry: Service registry to update
        workflow_definition_repository: Optional repository for workflow definitions
        symphony_instance: Optional Symphony instance for state management
    """
    # Register workflow definition repository if provided
    if workflow_definition_repository:
        registry.register_repository("workflow_definition", workflow_definition_repository)
    
    # Register Symphony instance if provided (needed for state management)
    if symphony_instance:
        registry.register_service("symphony_instance", symphony_instance)
    
    # Check if required repositories exist
    try:
        # Get or create required components
        workflow_tracker = registry.get_workflow_tracker()
        
        # Get workflow definition repository if not provided
        if not workflow_definition_repository:
            workflow_definition_repository = registry.get_repository("workflow_definition")
        
        # Create and register workflow engine
        workflow_engine = WorkflowEngine(
            service_registry=registry,
            workflow_definition_repository=workflow_definition_repository,
            workflow_tracker=workflow_tracker
        )
        registry.register_service("workflow_engine", workflow_engine)
        
        # Register workflow templates
        registry.register_service("workflow_templates", WorkflowTemplates())
        
        return True
    except ValueError as e:
        # Some required component is missing
        print(f"Could not register orchestration components: {e}")
        return False