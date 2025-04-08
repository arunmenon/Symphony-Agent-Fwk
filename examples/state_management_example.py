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
        agent1_config = AgentConfig(
            name="Agent1",
            description="First test agent",
            agent_type="reactive"
        )
        agent1 = await symphony.agents.create_agent(agent1_config, llm_client=llm_client)
        
        agent2_config = AgentConfig(
            name="Agent2",
            description="Second test agent",
            agent_type="planning"
        )
        agent2 = await symphony.agents.create_agent(agent2_config, llm_client=llm_client)
        
        # Create memory for agents
        memory = await symphony.agents.create_memory("conversation")
        
        # Create a simple workflow
        workflow = (symphony.build_workflow()
                   .create("TestWorkflow", "Test workflow for checkpointing")
                   .add_task("Task1", "First task", {"agent_id": agent1})
                   .build())
        workflow_id = await symphony.workflows.save_workflow_definition(workflow)
        
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
            print(f"  - {agent.config.name}: {agent.config.description}")
        
        # Modify and create new checkpoint
        agent3_config = AgentConfig(
            name="Agent3",
            description="Added after restore",
            agent_type="reactive"
        )
        agent3 = await symphony2.agents.create_agent(agent3_config, llm_client=llm_client)
        
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
            print(f"  - {agent.config.name}: {agent.config.description}")
        
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