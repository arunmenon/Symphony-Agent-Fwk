"""Example demonstrating Symphony's state management capabilities.

This example shows how to use checkpoints to save and restore agent state
across different sessions or to recover from failures.
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
import shutil
import tempfile

from symphony import Symphony
from symphony.core.agent_config import AgentConfig
from symphony.llm.base import MockLLMClient


async def run_example():
    """Run the state management example."""
    print("\n=== Symphony State Management Example ===\n")
    
    # Create a temporary directory for state
    temp_dir = tempfile.mkdtemp()
    try:
        # Part 1: Create agents and checkpoint them
        print("Creating Symphony instance with persistence enabled...")
        symphony = Symphony(persistence_enabled=True)
        await symphony.setup(state_dir=os.path.join(temp_dir, "state"))
        
        # Create a mock LLM client
        llm_client = MockLLMClient()
        
        # Create some agents
        print("Creating agents...")
        agent1 = await symphony.agents.create_agent(
            name="Agent1",
            role="First test agent",
            instruction_template="You are a test agent for state management.",
            capabilities={"expertise": ["testing"]},
            model="mock/default"
        )
        
        # Save agent1 to make it discoverable
        agent1_id = await symphony.agents.save_agent(agent1)
        print(f"Saved agent1 with ID: {agent1_id}")
        
        agent2 = await symphony.agents.create_agent(
            name="Agent2",
            role="Second test agent",
            instruction_template="You are a planning agent for state management.",
            capabilities={"expertise": ["planning", "testing"]},
            model="mock/default"
        )
        
        # Save agent2 to make it discoverable
        agent2_id = await symphony.agents.save_agent(agent2)
        print(f"Saved agent2 with ID: {agent2_id}")
        
        # Verify agents were saved
        agents_after_save = await symphony.agents.get_all_agents()
        print(f"After saving: {len(agents_after_save)} agents available")
        
        # Create memory for agents - skipping for now since the API might have changed
        # memory = await symphony.agents.create_memory("conversation")
        
        # Create a simple workflow
        workflow = (symphony.build_workflow()
                   .create("TestWorkflow", "Test workflow for checkpointing")
                   .add_task("Task1", "First task", {"agent_id": agent1.id})
                   .build())
        # The API might have changed; commenting out for now
        # workflow_id = await symphony.workflows.save_workflow_definition(workflow)
        
        # Create a checkpoint
        print("Creating checkpoint...")
        checkpoint_id = await symphony.create_checkpoint("initial_state")
        print(f"Created checkpoint: {checkpoint_id}\n")
        
        # List checkpoints
        checkpoints = await symphony.list_checkpoints()
        print("Available checkpoints:")
        for cp in checkpoints:
            print(f"  - {cp['id']} ({cp['name']}): created at {cp['created_at']}")
        print()
        
        # Part 2: Create a new Symphony instance and restore from checkpoint
        print("Creating new Symphony instance and restoring from checkpoint...")
        symphony2 = Symphony(persistence_enabled=True)
        await symphony2.setup(state_dir=os.path.join(temp_dir, "state"))
        
        # Restore from checkpoint
        await symphony2.resume_from_checkpoint(checkpoint_id)
        
        # Verify agents were restored
        agents = await symphony2.agents.get_all_agents()
        print(f"Restored {len(agents)} agents:")
        for agent in agents:
            try:
                print(f"  - {agent.name}: {agent.role}")
            except AttributeError:
                print(f"  - {agent}: (Unable to access name/role properties)")
        
        # Modify and create new checkpoint
        agent3 = await symphony2.agents.create_agent(
            name="Agent3",
            role="Added after restore",
            instruction_template="You are a test agent added after restore.",
            capabilities={"expertise": ["testing"]},
            model="mock/default"
        )
        
        # Save agent3 to make it discoverable
        agent3_id = await symphony2.agents.save_agent(agent3)
        print(f"Saved agent3 with ID: {agent3_id}")
        
        # Verify agent was saved
        agents_after_save = await symphony2.agents.get_all_agents()
        print(f"After saving agent3: {len(agents_after_save)} agents available")
        
        # Create a new checkpoint
        new_checkpoint_id = await symphony2.create_checkpoint("updated_state")
        print(f"Created new checkpoint: {new_checkpoint_id}")
        
        # Part 3: Demonstrate resuming latest checkpoint
        print("\nDemonstrating resume_latest_checkpoint...")
        symphony3 = Symphony(persistence_enabled=True)
        await symphony3.setup(state_dir=os.path.join(temp_dir, "state"))
        
        # Resume from latest checkpoint
        resumed_checkpoint_id = await symphony3.resume_latest_checkpoint()
        print(f"Resumed from latest checkpoint: {resumed_checkpoint_id}")
        
        # Verify all agents are present
        agents = await symphony3.agents.get_all_agents()
        print(f"Restored {len(agents)} agents from latest checkpoint:")
        for agent in agents:
            try:
                print(f"  - {agent.name}: {agent.role}")
            except AttributeError:
                print(f"  - {agent}: (Unable to access name/role properties)")
        
        # Part 4: Cleanup - delete checkpoints
        print("\nCleaning up checkpoints...")
        await symphony3.delete_checkpoint(checkpoint_id)
        print(f"Deleted checkpoint: {checkpoint_id}")
        
        # List remaining checkpoints
        checkpoints = await symphony3.list_checkpoints()
        print("Remaining checkpoints:")
        for cp in checkpoints:
            print(f"  - {cp['id']} ({cp['name']}): created at {cp['created_at']}")
        
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)
        print("\nTemporary directory cleaned up.")


if __name__ == "__main__":
    asyncio.run(run_example())