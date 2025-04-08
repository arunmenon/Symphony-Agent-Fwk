"""Example demonstrating automatic checkpointing during workflow execution.

This example shows how Symphony automatically creates checkpoints during
workflow execution, enabling resumption of workflows from failure points.
"""

import os
import asyncio
import tempfile
import shutil
from typing import Dict, List, Any, Optional

from symphony import Symphony
from symphony.core.agent_config import AgentConfig
from symphony.llm.base import MockLLMClient


async def run_example():
    """Run the workflow state management example."""
    print("\n=== Symphony Workflow State Management Example ===\n")
    
    # Create a temporary directory for state
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a Symphony instance with persistence enabled
        print("Creating Symphony instance with persistence enabled...")
        symphony = Symphony(persistence_enabled=True)
        await symphony.setup(state_dir=os.path.join(temp_dir, "state"))
        
        # Create a mock LLM client
        llm_client = MockLLMClient()
        
        # Create an agent
        print("Creating agent...")
        agent_config = AgentConfig(
            name="WorkflowAgent",
            description="Agent for workflow example",
            agent_type="reactive"
        )
        agent = await symphony.agents.create_agent(agent_config, llm_client=llm_client)
        
        # Create a workflow with multiple steps to demonstrate checkpointing
        print("Creating multi-step workflow...")
        workflow = (symphony.build_workflow()
                   .create("CheckpointWorkflow", "Workflow demonstrating automatic checkpoints")
                   .add_task("Step1", "First step", {"agent_id": agent.id})
                   .add_task("Step2", "Second step", {"agent_id": agent.id})
                   .add_task("Step3", "Third step", {"agent_id": agent.id})
                   .add_task("Step4", "Fourth step", {"agent_id": agent.id})
                   .add_task("Step5", "Fifth step", {"agent_id": agent.id})
                   .add_task("Step6", "Sixth step", {"agent_id": agent.id})
                   .build())
        
        workflow_id = await symphony.workflows.save_workflow_definition(workflow)
        
        # Execute workflow - this will automatically create checkpoints
        print("\nExecuting workflow (automatic checkpoints will be created)...")
        workflow_result = await symphony.workflows.execute_workflow_by_id(workflow_id)
        
        print(f"Workflow completed with status: {workflow_result.status}")
        
        # List checkpoints
        checkpoints = await symphony.list_checkpoints()
        print(f"\nNumber of checkpoints created: {len(checkpoints)}")
        print("Checkpoint details:")
        for i, cp in enumerate(checkpoints, 1):
            print(f"  {i}. {cp['name']} (created at {cp['created_at']})")
        
        # Create a new workflow that will simulate failure
        print("\nCreating workflow that will simulate failure...")
        failing_workflow = (symphony.build_workflow()
                         .create("FailingWorkflow", "Workflow that simulates failure")
                         .add_task("Step1", "First step", {"agent_id": agent.id})
                         .add_task("Step2", "Second step", {"agent_id": agent.id})
                         .add_task("FailingStep", "Step that will fail",
                                  {"agent_id": agent.id, "should_fail": True})
                         .add_task("Step4", "Never executed", {"agent_id": agent.id})
                         .build())
        
        failing_workflow_id = await symphony.workflows.save_workflow_definition(failing_workflow)
        
        # Execute the failing workflow - this will create checkpoints including an error checkpoint
        print("\nExecuting failing workflow...")
        try:
            failing_result = await symphony.workflows.execute_workflow_by_id(failing_workflow_id)
            print(f"Workflow completed with status: {failing_result.status}")
        except Exception as e:
            print(f"Workflow execution failed as expected: {e}")
        
        # List checkpoints again
        checkpoints = await symphony.list_checkpoints()
        print(f"\nNumber of checkpoints after failed workflow: {len(checkpoints)}")
        print("Latest checkpoints (showing new checkpoints):")
        for i, cp in enumerate(checkpoints[:3], 1):
            print(f"  {i}. {cp['name']} (created at {cp['created_at']})")
            
        # The real power would be to resume from a checkpoint, but that requires
        # implementing full state restoration which is a larger task
            
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)
        print("\nTemporary directory cleaned up.")


if __name__ == "__main__":
    asyncio.run(run_example())