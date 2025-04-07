"""Symphony: Next-Generation Agentic Framework.

Symphony is a powerful orchestration framework for building complex agent-based
systems. It provides a clean, declarative API for creating and executing
workflows, managing agents, and tracking tasks.

Basic Usage:
    ```python
    import asyncio
    from symphony import Symphony
    
    async def main():
        # Initialize Symphony
        symphony = Symphony()
        await symphony.setup()
        
        # Create an agent using the builder pattern
        agent = (symphony.build_agent()
                .create("WriterAgent", "Content Writer", 
                       "You are a creative content writer who excels at generating engaging content.")
                .with_capabilities(["writing", "content", "creativity"])
                .build())
        
        # Save the agent
        agent_id = await symphony.agents.save_agent(agent)
        
        # Create a task using the builder pattern
        task = (symphony.build_task()
               .create("Write Blog Post", "Write a blog post about AI")
               .with_query("Write a short blog post about the benefits of AI assistants in daily life.")
               .for_agent(agent_id)
               .build())
        
        # Execute the task
        result = await symphony.tasks.execute_task(task)
        print(result.result)
        
        # Create a workflow using the builder pattern
        workflow = (symphony.build_workflow()
                   .create("Blog Creation", "Create and refine a blog post")
                   .add_task("Initial Draft", "Write initial draft", {
                       "name": "Draft Blog Post",
                       "description": "Create first draft",
                       "input_data": {"query": "Write about AI benefits"}
                   })
                   .build())
        
        # Execute workflow
        result = await symphony.workflows.execute_workflow(workflow)
        
    if __name__ == "__main__":
        asyncio.run(main())
    ```

For more advanced usage, refer to the documentation.
"""

# Package version
__version__ = "0.1.0"

# Explicit exports
__all__ = [
    # Main entry point
    "Symphony",
    
    # Core models
    "Task", "TaskStatus", "TaskPriority", 
    "AgentConfig", "AgentCapabilities",
    "WorkflowDefinition", "Workflow", "WorkflowStatus",
    
    # Facades
    "AgentFacade", "TaskFacade", "WorkflowFacade", "PatternsFacade",
    
    # Builders
    "AgentBuilder", "TaskBuilder", "WorkflowBuilder", "PatternBuilder",
    
    # Feature detection
    "has_feature",
]

# Feature detection utility
def has_feature(feature_name: str) -> bool:
    """Check if a particular optional feature is available.
    
    This utility helps users determine if a specific optional dependency
    is available for use in their code.
    
    Args:
        feature_name: Name of the feature to check for ("openai", "qdrant", etc.)
        
    Returns:
        True if the feature is available, False otherwise
    """
    features = {
        # Model providers
        "openai": _check_module("openai"),
        "anthropic": _check_module("anthropic"),
        "vertexai": _check_module("google.cloud.aiplatform"),
        "huggingface": _check_module("huggingface_hub"),
        
        # Vector stores
        "qdrant": _check_module("qdrant_client"),
        "chroma": _check_module("chromadb"),
        "weaviate": _check_module("weaviate"),
        
        # Knowledge graphs
        "neo4j": _check_module("neo4j"),
        "networkx": _check_module("networkx"),
        
        # Observability
        "wandb": _check_module("wandb"),
        "mlflow": _check_module("mlflow"),
        "langsmith": _check_module("langsmith"),
        
        # Visualization
        "visualization": _check_module("matplotlib") and _check_module("plotly"),
        
        # CLI tools
        "cli": _check_module("click") and _check_module("rich"),
    }
    
    return features.get(feature_name, False)


def _check_module(module_name: str) -> bool:
    """Check if a module is available.
    
    Args:
        module_name: Module name to check
        
    Returns:
        True if available, False otherwise
    """
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


# Import main entry points
from symphony.api import Symphony as CoreSymphony
from symphony.simple_api import Symphony as SimpleSymphony

# Core models
from symphony.core.task import Task, TaskStatus, TaskPriority
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.execution.workflow_tracker import Workflow, WorkflowStatus

# Expose key facades directly
from symphony.facade.agents import AgentFacade
from symphony.facade.tasks import TaskFacade
from symphony.facade.workflows import WorkflowFacade
from symphony.patterns.facade import PatternsFacade

# Expose key builders directly
from symphony.builder.agent_builder import AgentBuilder
from symphony.builder.task_builder import TaskBuilder
from symphony.builder.workflow_builder import WorkflowBuilder
from symphony.patterns.builder import PatternBuilder

# Use simplified API by default to minimize cognitive load
Symphony = SimpleSymphony

# Add sentinel file to mark installed package
import os
import tempfile
_PACKAGE_SENTINEL = os.path.join(tempfile.gettempdir(), "symphony_installed")