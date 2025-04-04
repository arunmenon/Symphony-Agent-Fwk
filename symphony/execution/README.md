# Symphony Execution Layer

The execution layer provides enhanced execution capabilities for Symphony agents, bridging the gap between persistence and orchestration. It offers workflow tracking, enhanced agent execution, and task routing.

## Components

### WorkflowTracker

The `WorkflowTracker` manages collections of related tasks as workflows, tracking their lifecycle from creation through execution to completion.

```python
# Example
workflow = await workflow_tracker.create_workflow(
    name="Example Workflow",
    description="A workflow demonstrating Symphony's execution capabilities"
)

# Add tasks to workflow
await workflow_tracker.add_task_to_workflow(workflow.id, task.id)

# Track status
status = await workflow_tracker.compute_workflow_status(workflow.id)
```

### EnhancedExecutor

The `EnhancedExecutor` provides advanced execution capabilities for agents, including hooks, batching, and retry support.

```python
# Example
# Execute with hooks
result_task = await executor.execute_task(
    task_id, 
    agent, 
    workflow_id,
    pre_execution_hook=pre_hook,
    post_execution_hook=post_hook
)

# Execute with retry
result_task = await executor.execute_with_retry(
    task_id,
    agent,
    max_retries=3
)

# Batch execution
results = await executor.batch_execute(
    [(task_id1, agent1), (task_id2, agent2)],
    max_concurrent=2
)
```

### TaskRouter

The `TaskRouter` directs tasks to appropriate agents based on various routing strategies.

```python
# Example
# Route by capability
agent_id = await router.route_task(task)

# Change strategy
router.set_strategy(RoutingStrategy.CONTENT_MATCH)

# Custom routing
router.set_custom_router(my_custom_router_function)
```

## Integration with Symphony

The execution layer is designed to work seamlessly with Symphony's other components:

1. **Persistence Layer**: Uses repositories for storing and retrieving data
2. **Core Components**: Extends the base Agent and Task classes
3. **Orchestration Layer**: Provides enhanced capabilities for agent orchestration

All execution components are available through the `ServiceRegistry`:

```python
# Get components from registry
workflow_tracker = registry.get_workflow_tracker()
executor = registry.get_enhanced_executor()
router = registry.get_task_router(RoutingStrategy.CAPABILITY_MATCH)
```

## Usage

See the example script in `/examples/execution_example.py` for detailed usage examples.