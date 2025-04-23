"""Minimal DAG Example for Symphony.

This example demonstrates a minimal workflow using Symphony to:
1. Create two agents
2. Register a tool
3. Create a 2-step DAG
4. Execute the workflow
5. Check the results

This example serves as both a minimal usage guide and a contract test
of Symphony's core functionality.
"""

import asyncio
import sys
from typing import Dict, Any

from symphony import Symphony


# Define a simple tool for demonstration
def simple_search_tool(query: str) -> str:
    """A simple mock search tool."""
    return f"Search results for: {query}"


async def run_minimal_dag():
    """Run a minimal DAG workflow."""
    # Step 1: Initialize Symphony
    symphony = Symphony(persistence_enabled=True)
    await symphony.setup(state_dir=".symphony_minimal_dag_state")
    
    # Step 2: Register a tool
    tool_register = {
        "search": simple_search_tool
    }
    symphony._custom_tools = tool_register
    
    # Step 3: Create two agents
    planner_agent = (symphony.build_agent()
        .name("Planner")
        .description("Plans tasks")
        .with_model("gpt-3.5-turbo")
        .build()
    )
    
    executor_agent = (symphony.build_agent()
        .name("Executor")
        .description("Executes tasks")
        .with_model("gpt-3.5-turbo")
        .with_tools(["search"])
        .build()
    )
    
    # Step 4: Build a workflow
    workflow_builder = symphony.build_workflow()
    workflow = (workflow_builder.create(
        name="Minimal DAG",
        description="A minimal DAG workflow"
    ))
    
    # Step 5: Create step 1 - Planning
    planning_step = (workflow_builder.build_step()
        .name("Planning")
        .description("Plan the task")
        .agent(planner_agent)
        .task("Create a plan to research Symphony orchestration frameworks")
        .context_data({})
        .output_key("plan")
        .build()
    )
    workflow_builder.add_step(planning_step)
    
    # Step 6: Create step 2 - Execution
    execution_step = (workflow_builder.build_step()
        .name("Execution")
        .description("Execute the plan")
        .agent(executor_agent)
        .task("Execute this plan: {{plan}}")
        .context_data({
            "plan": "{{plan}}",
            "tools": ["search"]
        })
        .output_key("result")
        .build()
    )
    workflow_builder.add_step(execution_step)
    
    # Step 7: Build and execute the workflow
    workflow_definition = workflow_builder.build()
    result = await symphony.workflows.execute_workflow(
        workflow=workflow_definition,
        initial_context={},
        auto_checkpoint=True
    )
    
    # Step 8: Check the results
    context = result.metadata.get("context", {})
    final_result = context.get("result", "No result")
    return final_result


if __name__ == "__main__":
    result = asyncio.run(run_minimal_dag())
    print("\n--- Final Result ---")
    print(result)
    print("-------------------\n")
    
    # Report success
    print("Minimal DAG example completed successfully!")
    sys.exit(0)