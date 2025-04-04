"""Example demonstrating Symphony's execution layer capabilities.

This example shows how to use Symphony's execution layer to:
1. Create and manage workflows
2. Execute tasks with enhanced execution capabilities (retry, batching)
3. Route tasks to appropriate agents
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
from symphony.execution.workflow_tracker import WorkflowTracker, Workflow, WorkflowStatus
from symphony.execution.enhanced_agent import EnhancedExecutor
from symphony.execution.router import TaskRouter, RoutingStrategy


async def workflow_tracking_example():
    """Demonstrate workflow tracking functionality."""
    print("\n=== Workflow Tracking Example ===")
    
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Clear any existing registrations
    registry.repositories = {}
    registry.services = {}
    
    # Register repositories
    agent_config_repo = InMemoryRepository(AgentConfig)
    task_repo = InMemoryRepository(Task)
    workflow_repo = InMemoryRepository(Workflow)
    
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    
    # Get workflow tracker from registry
    workflow_tracker = registry.get_workflow_tracker()
    
    # Create a workflow
    workflow = await workflow_tracker.create_workflow(
        name="Example Workflow",
        description="A workflow demonstrating Symphony's execution capabilities"
    )
    print(f"Created workflow with ID: {workflow.id}")
    
    # Create task manager
    task_manager = registry.get_task_manager()
    
    # Create several tasks
    tasks = []
    for i in range(3):
        task = await task_manager.create_task(
            name=f"Task {i+1}",
            description=f"Example task {i+1}",
            input_data={"query": f"Process task {i+1}"}
        )
        tasks.append(task)
        
        # Add to workflow
        await workflow_tracker.add_task_to_workflow(workflow.id, task.id)
        print(f"Added task {task.id} to workflow")
    
    # Check workflow status
    status = await workflow_tracker.compute_workflow_status(workflow.id)
    print(f"Initial workflow status: {status}")
    
    # Create a mock agent for task execution
    mock_agent = Agent(name="WorkflowAgent", system_prompt="You are a workflow agent")
    
    # Mock the agent run method
    async def mock_run(query):
        print(f"Agent received query: {query}")
        return f"Completed: {query}"
    
    mock_agent.run = mock_run
    
    # Execute first task
    first_task = tasks[0]
    await task_manager.execute_task(first_task.id, mock_agent)
    print(f"Executed task: {first_task.id}")
    
    # Check workflow status
    status = await workflow_tracker.compute_workflow_status(workflow.id)
    print(f"Workflow status after first task: {status}")
    
    # Execute all remaining tasks
    for task in tasks[1:]:
        await task_manager.execute_task(task.id, mock_agent)
        print(f"Executed task: {task.id}")
    
    # Check final workflow status
    status = await workflow_tracker.sync_workflow_status(workflow.id)
    print(f"Final workflow status: {status.status}")
    
    # Get all tasks in workflow
    workflow_tasks = await workflow_tracker.get_workflow_tasks(workflow.id)
    print(f"Workflow contains {len(workflow_tasks)} tasks")
    for task in workflow_tasks:
        print(f"- Task: {task.name}, Status: {task.status}")


async def enhanced_execution_example():
    """Demonstrate enhanced execution functionality."""
    print("\n=== Enhanced Execution Example ===")
    
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Clear any existing registrations
    registry.repositories = {}
    registry.services = {}
    
    # Register repositories
    agent_config_repo = InMemoryRepository(AgentConfig)
    task_repo = InMemoryRepository(Task)
    workflow_repo = InMemoryRepository(Workflow)
    
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    
    # Get services from registry
    workflow_tracker = registry.get_workflow_tracker()
    task_manager = registry.get_task_manager()
    executor = registry.get_enhanced_executor()
    
    # Create a workflow
    workflow = await workflow_tracker.create_workflow(
        name="Enhanced Execution Workflow",
        description="A workflow demonstrating enhanced execution"
    )
    print(f"Created workflow with ID: {workflow.id}")
    
    # Create tasks for different execution patterns
    basic_task = await task_manager.create_task(
        name="Basic Task",
        description="A basic task for enhanced execution",
        input_data={"query": "Execute basic task"}
    )
    
    retry_task = await task_manager.create_task(
        name="Retry Task",
        description="A task that will be retried",
        input_data={"query": "Execute retry task"}
    )
    
    # Tasks for batch execution
    batch_tasks = []
    for i in range(3):
        task = await task_manager.create_task(
            name=f"Batch Task {i+1}",
            description=f"Task {i+1} for batch execution",
            input_data={"query": f"Execute batch task {i+1}"}
        )
        batch_tasks.append(task)
    
    # Add all tasks to workflow
    await workflow_tracker.add_task_to_workflow(workflow.id, basic_task.id)
    await workflow_tracker.add_task_to_workflow(workflow.id, retry_task.id)
    for task in batch_tasks:
        await workflow_tracker.add_task_to_workflow(workflow.id, task.id)
    
    # Create a mock agent
    mock_agent = Agent(name="ExecutorAgent", system_prompt="You are an execution agent")
    
    # Mock the agent run method - for retry demonstration, we'll make it fail initially
    attempt_count = 0
    
    async def mock_run(query):
        nonlocal attempt_count
        
        if "retry" in query.lower() and attempt_count < 2:
            attempt_count += 1
            raise Exception(f"Simulated failure (attempt {attempt_count})")
        
        print(f"Agent received query: {query}")
        return f"Completed: {query}"
    
    mock_agent.run = mock_run
    
    # Execute basic task with hooks
    def pre_execution_hook(task, agent):
        print(f"Pre-execution hook for task: {task.name}")
    
    def post_execution_hook(task, agent, result):
        print(f"Post-execution hook for task: {task.name}, Result: {result}")
    
    print("\nExecuting basic task with hooks:")
    result_task = await executor.execute_task(
        basic_task.id, 
        mock_agent, 
        workflow.id,
        pre_execution_hook=pre_execution_hook,
        post_execution_hook=post_execution_hook
    )
    print(f"Basic task status: {result_task.status}")
    
    # Execute retry task
    print("\nExecuting retry task (with simulated failures):")
    result_task = await executor.execute_with_retry(
        retry_task.id,
        mock_agent,
        max_retries=3,
        retry_delay=0.1,
        workflow_id=workflow.id
    )
    print(f"Retry task status: {result_task.status}")
    print(f"Result: {result_task.output_data.get('result')}")
    
    # Execute batch tasks
    print("\nExecuting batch tasks:")
    batch_tuples = [(task.id, mock_agent) for task in batch_tasks]
    batch_results = await executor.batch_execute(
        batch_tuples,
        workflow_id=workflow.id,
        max_concurrent=2
    )
    
    for task in batch_results:
        print(f"Batch task {task.name} status: {task.status}")
        
    # Check final workflow status
    status = await workflow_tracker.sync_workflow_status(workflow.id)
    print(f"\nFinal workflow status: {status.status}")


async def task_routing_example():
    """Demonstrate task routing functionality."""
    print("\n=== Task Routing Example ===")
    
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
    
    # Create task manager
    task_manager = registry.get_task_manager()
    
    # Create agent configurations for different capabilities
    math_agent_config = AgentConfig(
        name="MathAgent",
        role="Mathematics Expert",
        description="An agent specialized in mathematics",
        instruction_template="You are a mathematics expert named {name}. Solve math problems.",
        config={"model": "gpt-4"},
        capabilities=AgentCapabilities(
            expertise=["mathematics", "algebra", "calculus"]
        )
    )
    
    writing_agent_config = AgentConfig(
        name="WritingAgent",
        role="Content Writer",
        description="An agent specialized in writing content",
        instruction_template="You are a content writer named {name}. Create engaging content.",
        config={"model": "gpt-4"},
        capabilities=AgentCapabilities(
            expertise=["writing", "content", "creative"]
        )
    )
    
    coding_agent_config = AgentConfig(
        name="CodingAgent",
        role="Software Developer",
        description="An agent specialized in coding",
        instruction_template="You are a software developer named {name}. Write clean, efficient code.",
        config={"model": "gpt-4"},
        capabilities=AgentCapabilities(
            expertise=["coding", "programming", "python", "javascript"]
        )
    )
    
    # Save agent configurations
    await agent_config_repo.save(math_agent_config)
    await agent_config_repo.save(writing_agent_config)
    await agent_config_repo.save(coding_agent_config)
    
    # Get router from registry
    router = registry.get_task_router(RoutingStrategy.CAPABILITY_MATCH)
    
    # Create tasks with different requirements
    math_task = await task_manager.create_task(
        name="Math Problem",
        description="Solve a complex math problem",
        input_data={"query": "Solve the equation: 3x^2 + 2x - 5 = 0"},
        tags=["mathematics", "algebra"]
    )
    
    writing_task = await task_manager.create_task(
        name="Blog Post",
        description="Write a blog post about machine learning",
        input_data={"query": "Write a blog post about the latest advancements in natural language processing"},
        tags=["writing", "content"]
    )
    
    coding_task = await task_manager.create_task(
        name="Code Function",
        description="Write a Python function",
        input_data={"query": "Write a Python function to find the factorial of a number"},
        tags=["coding", "python"]
    )
    
    # Route tasks by capability
    print("\nRouting by capability:")
    math_agent_id = await router.route_task(math_task)
    writing_agent_id = await router.route_task(writing_task)
    coding_agent_id = await router.route_task(coding_task)
    
    print(f"Math task routed to agent: {math_agent_id}")
    print(f"Writing task routed to agent: {writing_agent_id}")
    print(f"Coding task routed to agent: {coding_agent_id}")
    
    # Change to content-match strategy
    router.set_strategy(RoutingStrategy.CONTENT_MATCH)
    
    # Create a mixed task
    mixed_task = await task_manager.create_task(
        name="Mixed Task",
        description="A task with mixed requirements",
        input_data={"query": "Write a blog post about how mathematics is used in coding"}
    )
    
    # Route task by content
    print("\nRouting by content:")
    mixed_agent_id = await router.route_task(mixed_task)
    print(f"Mixed task routed to agent: {mixed_agent_id}")
    
    # Change to load-balanced strategy
    router.set_strategy(RoutingStrategy.LOAD_BALANCED)
    
    # Create multiple tasks and route them
    print("\nRouting by load balancing:")
    for i in range(5):
        task = await task_manager.create_task(
            name=f"Load Test Task {i+1}",
            description=f"Task {i+1} for load balancing test",
            input_data={"query": f"Process load balancing task {i+1}"}
        )
        
        agent_id = await router.route_task(task)
        print(f"Task {i+1} routed to agent: {agent_id}")
        
        # Mark some tasks as complete to change the load
        if i % 2 == 0:
            router.mark_task_complete(agent_id)
            print(f"Marked task {i+1} as complete for agent: {agent_id}")


async def file_system_execution_example():
    """Demonstrate file system execution integration."""
    print("\n=== File System Execution Example ===")
    
    # Set up data directory
    data_dir = os.path.join(os.getcwd(), "symphony_data")
    os.makedirs(data_dir, exist_ok=True)
    print(f"Using data directory: {data_dir}")
    
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Clear any existing registrations
    registry.repositories = {}
    registry.services = {}
    
    # Register repositories with file system storage
    agent_config_repo = FileSystemRepository(AgentConfig, data_dir)
    task_repo = FileSystemRepository(Task, data_dir)
    workflow_repo = FileSystemRepository(Workflow, data_dir)
    
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    
    # Get services from registry
    workflow_tracker = registry.get_workflow_tracker()
    executor = registry.get_enhanced_executor()
    task_manager = registry.get_task_manager()
    
    # Create a workflow
    workflow = await workflow_tracker.create_workflow(
        name="Persistent Workflow",
        description="A workflow with file system persistence"
    )
    print(f"Created workflow with ID: {workflow.id}")
    print(f"Workflow saved to: {os.path.join(data_dir, 'workflow', f'{workflow.id}.json')}")
    
    # Create a task
    task = await task_manager.create_task(
        name="Persistent Task",
        description="A task with file system persistence",
        input_data={"query": "Process persistent task"}
    )
    print(f"Created task with ID: {task.id}")
    print(f"Task saved to: {os.path.join(data_dir, 'task', f'{task.id}.json')}")
    
    # Add task to workflow
    await workflow_tracker.add_task_to_workflow(workflow.id, task.id)
    
    # Create a mock agent
    mock_agent = Agent(name="PersistentAgent", system_prompt="You are a persistent storage agent")
    
    # Mock the agent run method
    async def mock_run(query):
        print(f"Agent received query: {query}")
        return f"Completed: {query} with persistence"
    
    mock_agent.run = mock_run
    
    # Execute task
    result_task = await executor.execute_task(task.id, mock_agent, workflow.id)
    print(f"Executed task with status: {result_task.status}")
    
    # Verify persistence by retrieving the task and workflow again
    retrieved_task = await task_repo.find_by_id(task.id)
    retrieved_workflow = await workflow_repo.find_by_id(workflow.id)
    
    print(f"Retrieved task - Status: {retrieved_task.status}")
    print(f"Retrieved task result: {retrieved_task.output_data.get('result')}")
    print(f"Retrieved workflow - Status: {retrieved_workflow.status}")


async def main():
    """Run the examples."""
    print("=== Symphony Execution Layer Examples ===")
    
    # Run workflow tracking example
    await workflow_tracking_example()
    
    # Run enhanced execution example
    await enhanced_execution_example()
    
    # Run task routing example
    await task_routing_example()
    
    # Run file system execution example
    await file_system_execution_example()
    
    print("\nExamples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())