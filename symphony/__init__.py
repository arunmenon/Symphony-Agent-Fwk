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

__version__ = "0.1.0"

from symphony.api import Symphony
from symphony.core.task import Task, TaskStatus, TaskPriority
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.execution.workflow_tracker import Workflow, WorkflowStatus

# Expose key facades directly
from symphony.facade.agents import AgentFacade
from symphony.facade.tasks import TaskFacade
from symphony.facade.workflows import WorkflowFacade

# Expose key builders directly
from symphony.builder.agent_builder import AgentBuilder
from symphony.builder.task_builder import TaskBuilder
from symphony.builder.workflow_builder import WorkflowBuilder