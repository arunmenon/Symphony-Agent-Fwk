# Symphony Execution Layer

The Execution Layer builds on Symphony's Persistence Layer to provide enhanced execution capabilities, workflow tracking, and task routing. This document outlines the key components and their interactions.

## Architecture

The Execution Layer consists of these main components:

1. **Workflow Tracker**: Manages collections of related tasks as workflows
2. **Enhanced Executor**: Provides advanced execution features for agents
3. **Task Router**: Routes tasks to appropriate agents based on different strategies

All components are registered in the central `ServiceRegistry` for easy access throughout the application.

## Workflow Tracker

The Workflow Tracker maintains workflows, which are collections of related tasks with a shared lifecycle.

### Key Features:
- Create and manage workflows
- Add tasks to workflows
- Track workflow status based on task statuses
- Provide workflow-level metadata

### Status Tracking:
Workflows have the following statuses:
- `PENDING`: Workflow created but no tasks executed
- `RUNNING`: At least one task is running or pending
- `COMPLETED`: All tasks are completed
- `FAILED`: At least one task has failed
- `PAUSED`: Workflow has been paused manually

## Enhanced Executor

The Enhanced Executor expands on the basic task execution with advanced features.

### Key Features:
- Pre and post-execution hooks
- Execution context for metadata
- Detailed error tracking
- Automatic workflow integration
- Concurrent batch execution
- Automatic retries

### Execution Strategies:
- **Single task**: Execute one task with a specific agent
- **Batch execution**: Run multiple tasks concurrently with configurable parallelism
- **Retry execution**: Automatically retry failed tasks

## Task Router

The Task Router determines which agent should handle a specific task based on various strategies.

### Routing Strategies:
- **Round Robin**: Distribute tasks evenly among agents
- **Capability Match**: Match tasks to agents based on capabilities/expertise
- **Content Match**: Match tasks based on content analysis
- **Load Balanced**: Route to the least busy agent
- **Custom**: Implement custom routing logic

### Matching Logic:
- Tag-based matching with agent expertise
- Content analysis of task queries
- Agent load tracking
- Dynamic strategy switching

## Integration with Persistence

The Execution Layer integrates with the Persistence Layer through:

1. **Repository Access**: Components load and store data through repositories
2. **Domain Models**: Shared domain models (`Task`, `Workflow`, `AgentConfig`)
3. **Service Registry**: Central access to repositories and services

## Usage Examples

### Basic Workflow

```python
# Set up repositories and registry
registry = ServiceRegistry.get_instance()

# Get execution services
workflow_tracker = registry.get_workflow_tracker()
executor = registry.get_enhanced_executor()
task_manager = registry.get_task_manager()

# Create a workflow
workflow = await workflow_tracker.create_workflow(
    name="Example Workflow",
    description="A demonstration workflow"
)

# Create tasks
task = await task_manager.create_task(
    name="Example Task",
    description="A task to execute",
    input_data={"query": "Process this information"}
)

# Add task to workflow
await workflow_tracker.add_task_to_workflow(workflow.id, task.id)

# Execute task in workflow context
result = await executor.execute_task(task.id, agent, workflow.id)
```

### Task Routing

```python
# Get router with strategy
router = registry.get_task_router(RoutingStrategy.CAPABILITY_MATCH)

# Route task to appropriate agent
agent_config_id = await router.route_task(task)

# Get agent factory
agent_factory = registry.get_agent_factory()

# Create agent from config
agent = await agent_factory.create_agent(agent_config_id)

# Execute task with matched agent
result = await executor.execute_task(task.id, agent)
```

### Batch Execution

```python
# Create tasks
task_ids = []
for i in range(5):
    task = await task_manager.create_task(
        name=f"Batch Task {i}",
        description=f"Task {i} in batch execution",
        input_data={"query": f"Process batch item {i}"}
    )
    task_ids.append(task.id)
    await workflow_tracker.add_task_to_workflow(workflow.id, task.id)

# Create task-agent pairs
task_agent_pairs = [(task_id, agent) for task_id in task_ids]

# Execute in batch
results = await executor.batch_execute(
    task_agent_pairs,
    workflow_id=workflow.id,
    max_concurrent=3
)
```

## Future Extensions

The Execution Layer is designed to be extended with:

1. **Dynamic Workflow Patterns**: Support for conditional execution, branching, and loops
2. **Execution Monitoring**: Real-time monitoring and metrics for task execution
3. **Priority Queuing**: Task prioritization and scheduling
4. **Error Recovery Strategies**: Sophisticated error handling and recovery patterns
5. **Resource Management**: Managing constraints and quotas for execution