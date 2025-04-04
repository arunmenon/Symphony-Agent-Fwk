# Symphony Orchestration Layer

The Orchestration Layer is the third phase of Symphony's enhanced architecture, building on the [Persistence Layer](persistence_layer.md) and [Execution Layer](execution_layer.md). It provides a powerful, declarative way to define and execute complex workflows that coordinate multiple agents, handle control flow, and manage state across multi-step processes.

## Core Concepts

### 1. Workflow Definition

A `WorkflowDefinition` is a declarative description of a workflow, containing a sequence of steps to be executed. It is designed as an immutable structure, where all modifications return new instances to facilitate safe composition and ensure thread safety.

```python
workflow = WorkflowDefinition(
    name="Content Creation",
    description="Create and refine content with multiple agents"
)
```

### 2. Workflow Steps

Steps are the building blocks of workflows, representing discrete units of execution. The Orchestration Layer provides several step types:

- **TaskStep**: Executes a single task with an agent
- **ConditionalStep**: Executes different branches based on a condition
- **ParallelStep**: Executes multiple steps concurrently
- **LoopStep**: Executes a step repeatedly until a condition is met

```python
# Task step to generate content
generate_step = TaskStep(
    name="Generate Content",
    task_template={
        "name": "Content Generation",
        "input_data": {
            "query": "Write a blog post about AI orchestration."
        }
    }
)

# Add step to workflow
workflow = workflow.add_step(generate_step)
```

### 3. Workflow Context

The `WorkflowContext` provides a shared state for workflow execution, allowing steps to share data and access services. It also supports variable templating and condition evaluation.

```python
# Template in a task
task_template = {
    "input_data": {
        "query": f"Revise this content:\n\n{{{{step.{generate_step.id}.result}}}}"
    }
}
```

### 4. Workflow Engine

The `WorkflowEngine` is responsible for executing workflow definitions, managing state, and handling errors. It integrates with the Workflow Tracker from the Execution Layer to track the execution status.

```python
# Execute a workflow
workflow_engine = registry.get_service("workflow_engine")
result = await workflow_engine.execute_workflow(workflow_def)
```

## Design Patterns

The Orchestration Layer implements several key design patterns:

1. **Immutable Data Structures**: Workflow definitions are immutable, with modifications returning new instances
2. **Registry Pattern**: Services and components are accessed through the service registry
3. **Factory Method Pattern**: Template factories create common workflow patterns
4. **Decorator Pattern**: Steps can be composed and nested to create complex behaviors
5. **Strategy Pattern**: Different execution strategies for different step types

## Common Workflow Patterns

The Orchestration Layer includes a `WorkflowTemplates` class that provides factory methods for common workflow patterns:

1. **Chain of Thought**: A reasoning process with follow-up questions building on previous answers
2. **Critic-Revise**: An initial response is critiqued and then revised based on feedback
3. **Parallel Experts**: Multiple expert agents tackle a problem in parallel, with results synthesized
4. **Iterative Refinement**: A response is progressively improved through multiple iterations

```python
# Create a critic-revise workflow
templates = registry.get_service("workflow_templates")
workflow_def = templates.critic_revise(
    name="Blog Post Creation",
    main_prompt="Write a blog post about AI.",
    critique_prompt="Identify areas for improvement.",
    revision_prompt="Revise based on the critique."
)
```

## Component Structure

The Orchestration Layer is organized into several key components:

1. **workflow_definition.py**: Core classes for defining workflows, steps, and context
2. **steps.py**: Concrete step implementations for different execution patterns
3. **engine.py**: Workflow execution engine
4. **templates.py**: Factory methods for common workflow patterns

## Integration with Symphony Framework

The Orchestration Layer integrates with existing Symphony components:

- **Persistence Layer**: Workflows and their definitions are persisted
- **Execution Layer**: Tasks are executed with enhanced agents and tracked with the workflow tracker
- **Core Components**: Uses the service registry for dependency management

## Example Use Cases

1. **Multi-Step Reasoning**: Chain-of-thought workflows for complex problem-solving
2. **Content Generation and Refinement**: Create, critique, and revise content
3. **Collaborative Problem Solving**: Multiple agents collaborating on a task
4. **Conditional Processing**: Different processing paths based on content analysis
5. **Iterative Improvement**: Progressive refinement until quality criteria are met

## Usage Example

```python
# Get service registry
registry = ServiceRegistry.get_instance()

# Get templates service
templates = registry.get_service("workflow_templates")

# Create parallel experts workflow
workflow_def = templates.parallel_experts(
    name="Smart Home Analysis",
    prompt="What are the key considerations for a smart home?",
    expert_roles=["Technology", "Security", "Home Design"],
    summary_prompt="Synthesize the expert opinions."
)

# Execute workflow
workflow_engine = registry.get_service("workflow_engine")
workflow = await workflow_engine.execute_workflow(workflow_def)

# Access results from workflow metadata
context = workflow.metadata["context"]
final_result = next(
    (v.get("result") for k, v in context.items() 
     if "Synthesis" in k and ".result" in k),
    "Not found"
)
```

## Design Principles

The Orchestration Layer design follows these key principles:

1. **Declarative Definition**: Workflows are defined declaratively, separating what to do from how to do it
2. **Composability**: Steps can be composed into complex structures
3. **Extensibility**: Custom step types can be created by extending base classes
4. **Persistence**: Workflows and their definitions can be saved and loaded
5. **Error Handling**: Comprehensive error handling and recovery
6. **Templating**: Common patterns are available as templates
7. **Context Sharing**: Data can be shared between steps

## Conclusion

The Orchestration Layer builds on Symphony's core capabilities to enable complex, multi-step workflows that coordinate multiple agents. It provides a powerful abstraction for defining sophisticated agent interaction patterns while maintaining Symphony's intuitive design philosophy and extensible architecture.