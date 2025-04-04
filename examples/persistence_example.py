"""Example demonstrating Symphony's persistence capabilities.

This example shows how to use Symphony's persistence capabilities to store
and retrieve agent configurations and tasks.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.persistence.memory_repository import InMemoryRepository
from symphony.persistence.file_repository import FileSystemRepository
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.core.task import Task, TaskStatus
from symphony.core.registry import ServiceRegistry
from symphony.agents.base import Agent


async def in_memory_example():
    """Demonstrate in-memory repository functionality."""
    print("\n=== In-Memory Repository Example ===")
    
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Clear any existing registrations
    registry.repositories = {}
    registry.services = {}
    
    # Register repositories
    agent_config_repo = InMemoryRepository(AgentConfig)
    task_repo = InMemoryRepository(Task)
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("task", task_repo)
    
    # Create an agent configuration
    agent_config = AgentConfig(
        name="ExampleAgent",
        role="Assistant",
        description="A helpful example agent",
        instruction_template="You are a helpful assistant named {name}. Your role is to {role}.",
        config={"model": "gpt-4"}
    )
    
    # Save the agent configuration
    agent_factory = registry.get_agent_factory()
    config_id = await agent_config_repo.save(agent_config)
    print(f"Created agent configuration with ID: {config_id}")
    
    # Create an agent from the configuration
    agent = await agent_factory.create_agent(
        config_id,
        name="AssistantBot",
        role="answer questions helpfully"
    )
    print(f"Created agent: {agent.name}")
    print(f"Agent system prompt: {agent.system_prompt}")
    
    # Mock the agent run method for demonstration
    async def mock_run(query):
        print(f"Agent received query: {query}")
        return f"This is a response to: {query}"
    
    agent.run = mock_run
    
    # Create and execute a task
    task_manager = registry.get_task_manager()
    task = await task_manager.create_task(
        name="Example Task",
        description="An example task using in-memory storage",
        input_data={"query": "What is Symphony?"}
    )
    print(f"Created task with ID: {task.id}")
    
    # Execute the task
    result_task = await task_manager.execute_task(task.id, agent)
    
    # Display the results
    print(f"Task completed with status: {result_task.status}")
    print(f"Task result: {result_task.output_data.get('result')}")
    
    # List all tasks
    tasks = await task_manager.find_tasks()
    print(f"Found {len(tasks)} tasks in repository")


async def file_system_example():
    """Demonstrate file system repository functionality."""
    print("\n=== File System Repository Example ===")
    
    # Set up data directory
    data_dir = os.path.join(os.getcwd(), "symphony_data")
    os.makedirs(data_dir, exist_ok=True)
    print(f"Using data directory: {data_dir}")
    
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Clear any existing registrations
    registry.repositories = {}
    registry.services = {}
    
    # Register repositories
    agent_config_repo = FileSystemRepository(AgentConfig, data_dir)
    task_repo = FileSystemRepository(Task, data_dir)
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("task", task_repo)
    
    # Create an agent configuration
    agent_config = AgentConfig(
        name="PersistentAgent",
        role="File Manager",
        description="An agent that persists to the file system",
        instruction_template="You are a file system manager named {name}. Help with {task_type} operations.",
        config={"model": "gpt-4"}
    )
    
    # Save the agent configuration
    agent_factory = registry.get_agent_factory()
    config_id = await agent_config_repo.save(agent_config)
    print(f"Created agent configuration with ID: {config_id}")
    print(f"Configuration saved to: {os.path.join(data_dir, 'agentconfig', f'{config_id}.json')}")
    
    # Create an agent from the configuration
    agent = await agent_factory.create_agent(
        config_id,
        name="FileBot",
        task_type="file system"
    )
    print(f"Created agent: {agent.name}")
    print(f"Agent system prompt: {agent.system_prompt}")
    
    # Mock the agent run method for demonstration
    async def mock_run(query):
        print(f"Agent received query: {query}")
        return f"This is a file system response to: {query}"
    
    agent.run = mock_run
    
    # Create and execute a task
    task_manager = registry.get_task_manager()
    task = await task_manager.create_task(
        name="File Task",
        description="A task persisted to the file system",
        input_data={"query": "List all files in the directory."}
    )
    print(f"Created task with ID: {task.id}")
    print(f"Task saved to: {os.path.join(data_dir, 'task', f'{task.id}.json')}")
    
    # Execute the task
    result_task = await task_manager.execute_task(task.id, agent)
    
    # Display the results
    print(f"Task completed with status: {result_task.status}")
    print(f"Task result: {result_task.output_data.get('result')}")
    
    # Verify persistence by retrieving the task again
    retrieved_task = await task_repo.find_by_id(task.id)
    print(f"Retrieved task from file system - Status: {retrieved_task.status}")
    print(f"Retrieved task result: {retrieved_task.output_data.get('result')}")


async def main():
    """Run the examples."""
    print("=== Symphony Persistence Examples ===")
    
    # Run in-memory example
    await in_memory_example()
    
    # Run file system example
    await file_system_example()
    
    print("\nExamples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())