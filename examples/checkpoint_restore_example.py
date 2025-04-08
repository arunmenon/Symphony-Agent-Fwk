"""Example demonstrating the full checkpoint and restore capabilities.

This example shows how to create checkpoints of Symphony state and restore
from them, demonstrating resilience in Symphony applications.
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
    """Run the checkpoint and restore example."""
    print("\n=== Symphony Checkpoint and Restore Example ===\n")
    
    # Create a temporary directory for state
    temp_dir = tempfile.mkdtemp()
    state_dir = os.path.join(temp_dir, "state")
    
    try:
        # Part 1: Create Symphony state and checkpoint it
        print("Creating initial Symphony instance...")
        symphony1 = Symphony(persistence_enabled=True)
        await symphony1.setup(state_dir=state_dir)
        
        # Create a mock LLM client
        llm_client = MockLLMClient()
        
        # Create agents with different configurations
        print("Creating agents in first instance...")
        agent1 = await symphony1.agents.create_agent({
            "name": "Agent1",
            "description": "First agent example",
            "agent_type": "reactive"
        }, llm_client=llm_client)
        
        agent2 = await symphony1.agents.create_agent({
            "name": "Agent2", 
            "description": "Second agent example",
            "agent_type": "planning"
        }, llm_client=llm_client)
        
        # Create memory and assign to agent
        memory = await symphony1.agents.create_memory("conversation")
        agent1.memory = memory
        
        # Add some data to memory
        if hasattr(memory, "items"):
            memory.items["greeting"] = "Hello, world!"
            memory.items["favorite_color"] = "blue"
        
        # Create a workflow
        workflow = (symphony1.build_workflow()
                   .create("TestWorkflow", "Example workflow for checkpoint/restore")
                   .add_task("Task1", "First task", {"agent_id": agent1.id})
                   .add_task("Task2", "Second task", {"agent_id": agent2.id})
                   .build())
        workflow_id = await symphony1.workflows.save_workflow_definition(workflow)
        
        # Create a checkpoint
        print("Creating checkpoint of first instance state...")
        checkpoint_id = await symphony1.create_checkpoint("complete_state")
        print(f"Created checkpoint: {checkpoint_id}")
        
        # Part 2: Create a new Symphony instance and restore from checkpoint
        print("\nCreating second Symphony instance and restoring state...")
        symphony2 = Symphony(persistence_enabled=True)
        await symphony2.setup(state_dir=state_dir)
        
        # List available checkpoints
        checkpoints = await symphony2.list_checkpoints()
        print(f"Found {len(checkpoints)} checkpoints:")
        for i, cp in enumerate(checkpoints, 1):
            print(f"  {i}. {cp['name']} ({cp['id']}): created at {cp['created_at']}")
        
        # Restore from checkpoint
        print("\nRestoring from checkpoint...")
        await symphony2.resume_from_checkpoint(checkpoint_id)
        
        # Verify agents were restored
        agents = await symphony2.agents.get_all_agents()
        print(f"Restored {len(agents)} agents:")
        for agent in agents:
            print(f"  - {agent.config.name}: {agent.config.description}")
            if hasattr(agent, "memory") and agent.memory:
                print(f"    Memory: {agent.memory}")
                if hasattr(agent.memory, "items"):
                    print(f"    Memory items: {agent.memory.items}")
        
        # Verify workflows were restored
        workflows = await symphony2.workflows.get_all_workflows()
        print(f"\nRestored {len(workflows)} workflows:")
        for wf in workflows:
            print(f"  - {wf.name}: {wf.description}")
        
        # Part 3: Continue working with the restored state
        print("\nContinuing work with restored state...")
        
        # Add a new agent
        agent3 = await symphony2.agents.create_agent({
            "name": "Agent3",
            "description": "Added after restore",
            "agent_type": "reactive"
        }, llm_client=llm_client)
        
        # Create a new checkpoint
        print("Creating checkpoint of modified state...")
        new_checkpoint_id = await symphony2.create_checkpoint("modified_state")
        print(f"Created checkpoint: {new_checkpoint_id}")
        
        # List checkpoints again
        checkpoints = await symphony2.list_checkpoints()
        print(f"\nNow have {len(checkpoints)} checkpoints:")
        for i, cp in enumerate(checkpoints, 1):
            print(f"  {i}. {cp['name']} ({cp['id']}): created at {cp['created_at']}")
        
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)
        print("\nTemporary directory cleaned up.")


if __name__ == "__main__":
    asyncio.run(run_example())