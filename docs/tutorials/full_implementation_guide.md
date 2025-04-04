# Symphony Implementation Guide

This comprehensive guide demonstrates how to use the enhanced Symphony framework components we've implemented. The framework now includes three main layers that build on top of each other:

1. **Persistence Layer**: Store and retrieve entities
2. **Execution Layer**: Execute tasks with advanced capabilities
3. **Orchestration Layer**: Define and run complex workflows

Let's explore each layer with examples.

## 1. Persistence Layer

The Persistence Layer provides a unified abstraction for storing entities, with implementations for both in-memory and file-system storage.

### Key Components

- `Repository`: Abstract base class defining the CRUD operations
- `InMemoryRepository`: Implementation using in-memory dictionaries
- `FileSystemRepository`: Implementation using JSON files

### Basic Usage

```python
import asyncio
from symphony.core.task import Task
from symphony.persistence.memory_repository import InMemoryRepository
from symphony.persistence.file_repository import FileSystemRepository

async def persistence_example():
    # Create repositories
    memory_repo = InMemoryRepository(Task)
    file_repo = FileSystemRepository(Task, "./data")
    
    # Create a task
    task = Task(
        name="Example Task",
        description="This is an example task",
        input_data={"query": "What is Symphony?"}
    )
    
    # Save to memory repository
    task_id = await memory_repo.save(task)
    print(f"Task saved with ID: {task_id}")
    
    # Retrieve from memory repository
    retrieved_task = await memory_repo.find_by_id(task_id)
    print(f"Retrieved task: {retrieved_task.name}")
    
    # Save to file repository
    file_task_id = await file_repo.save(task)
    print(f"Task saved to file with ID: {file_task_id}")
    
    # Find all tasks
    all_tasks = await file_repo.find_all()
    print(f"Found {len(all_tasks)} tasks")

# Run the example
asyncio.run(persistence_example())
```

### Using with Agent Configurations

```python
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.persistence.file_repository import FileSystemRepository

async def agent_config_example():
    # Create repository for agent configurations
    agent_config_repo = FileSystemRepository(AgentConfig, "./data")
    
    # Create agent configuration
    writer_agent = AgentConfig(
        name="WriterAgent",
        role="Content Writer",
        instruction_template="You are a creative content writer who excels at {{task_type}}.",
        capabilities=AgentCapabilities(
            expertise=["writing", "content", "creativity"]
        )
    )
    
    # Save configuration
    agent_id = await agent_config_repo.save(writer_agent)
    print(f"Agent configuration saved with ID: {agent_id}")
    
    # Retrieve configuration
    retrieved_config = await agent_config_repo.find_by_id(agent_id)
    print(f"Retrieved agent: {retrieved_config.name} with role: {retrieved_config.role}")
    
    # Update configuration
    retrieved_config.capabilities.expertise.append("blogging")
    await agent_config_repo.update(retrieved_config)
    print("Updated agent capabilities")
```

## 2. Execution Layer

The Execution Layer builds on the Persistence Layer to provide advanced execution capabilities.

### Key Components

- `EnhancedExecutor`: Advanced execution with persistence integration
- `WorkflowTracker`: Tracks collections of related tasks
- `TaskRouter`: Routes tasks to appropriate agents based on different strategies

### Basic Task Execution

```python
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.core.task import Task
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.agents.base import Agent
from symphony.persistence.memory_repository import InMemoryRepository

async def execute_task_example():
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Create repositories
    task_repo = InMemoryRepository(Task)
    agent_config_repo = InMemoryRepository(AgentConfig)
    
    # Register repositories
    registry.register_repository("task", task_repo)
    registry.register_repository("agent_config", agent_config_repo)
    
    # Create task manager and agent factory
    task_manager = registry.get_task_manager()
    agent_factory = registry.get_agent_factory()
    
    # Create agent configuration
    writer_config = AgentConfig(
        name="WriterAgent",
        role="Content Writer",
        instruction_template="You are a creative content writer.",
        capabilities=AgentCapabilities(
            expertise=["writing", "content", "creativity"]
        )
    )
    await agent_config_repo.save(writer_config)
    
    # Create a task
    task = await task_manager.create_task(
        name="Write Blog Post",
        description="Write a short blog post about AI",
        input_data={"query": "Write a short blog post about AI assistants"}
    )
    
    # Create agent from configuration
    agent = await agent_factory.create_agent_from_id(writer_config.id)
    
    # Get enhanced executor
    executor = registry.get_enhanced_executor()
    
    # Execute task
    result_task = await executor.execute_task(task.id, agent)
    
    # Check result
    if result_task.status == "completed":
        print(f"Task completed successfully!")
        print(f"Result: {result_task.output_data.get('result')}")
    else:
        print(f"Task failed: {result_task.error}")

# Run the example
asyncio.run(execute_task_example())
```

### Workflow Tracking

```python
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.execution.workflow_tracker import Workflow, WorkflowStatus

async def workflow_tracking_example():
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Get workflow tracker
    workflow_tracker = registry.get_workflow_tracker()
    
    # Create a workflow
    workflow = await workflow_tracker.create_workflow(
        name="Content Creation Workflow",
        description="A workflow for creating and editing content"
    )
    print(f"Created workflow: {workflow.name} with ID: {workflow.id}")
    
    # Create tasks
    task_manager = registry.get_task_manager()
    writing_task = await task_manager.create_task(
        name="Write Article",
        description="Write an article about climate change",
        input_data={"query": "Write an article about climate change"}
    )
    
    editing_task = await task_manager.create_task(
        name="Edit Article",
        description="Edit the article for clarity and style",
        input_data={"query": "Edit the article for clarity and style"}
    )
    
    # Add tasks to workflow
    await workflow_tracker.add_task_to_workflow(workflow.id, writing_task.id)
    await workflow_tracker.add_task_to_workflow(workflow.id, editing_task.id)
    
    # Update workflow status
    await workflow_tracker.update_workflow_status(workflow.id, WorkflowStatus.RUNNING)
    
    # Get workflow tasks
    tasks = await workflow_tracker.get_workflow_tasks(workflow.id)
    print(f"Workflow has {len(tasks)} tasks")
    
    # Execute tasks and update workflow
    executor = registry.get_enhanced_executor()
    agent_factory = registry.get_agent_factory()
    
    # Create agent
    agent_config_repo = registry.get_repository("agent_config")
    configs = await agent_config_repo.find_all()
    agent = await agent_factory.create_agent_from_id(configs[0].id)
    
    # Execute writing task
    await executor.execute_task(writing_task.id, agent, workflow.id)
    
    # Workflow status will be automatically updated by executor
    updated_workflow = await workflow_tracker.get_workflow(workflow.id)
    print(f"Workflow status after first task: {updated_workflow.status}")
    
    # Execute editing task
    await executor.execute_task(editing_task.id, agent, workflow.id)
    
    # Check final workflow status
    final_workflow = await workflow_tracker.get_workflow(workflow.id)
    print(f"Final workflow status: {final_workflow.status}")

# Run the example
asyncio.run(workflow_tracking_example())
```

### Task Routing

```python
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.core.task import Task
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.execution.router import RoutingStrategy

async def task_routing_example():
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Get repositories
    agent_config_repo = registry.get_repository("agent_config")
    
    # Create agent configurations
    math_agent = AgentConfig(
        name="MathAgent",
        role="Mathematics Expert",
        instruction_template="You are a mathematics expert.",
        capabilities=AgentCapabilities(
            expertise=["mathematics", "algebra", "calculations"]
        )
    )
    
    writing_agent = AgentConfig(
        name="WritingAgent",
        role="Content Writer",
        instruction_template="You are a creative content writer.",
        capabilities=AgentCapabilities(
            expertise=["writing", "content", "creativity"]
        )
    )
    
    coding_agent = AgentConfig(
        name="CodingAgent",
        role="Software Developer",
        instruction_template="You are a software developer.",
        capabilities=AgentCapabilities(
            expertise=["coding", "programming", "python"]
        )
    )
    
    # Save agent configurations
    await agent_config_repo.save(math_agent)
    await agent_config_repo.save(writing_agent)
    await agent_config_repo.save(coding_agent)
    
    # Create tasks
    task_manager = registry.get_task_manager()
    
    math_task = await task_manager.create_task(
        name="Math Problem",
        description="Solve a complex math problem",
        input_data={"query": "Solve the equation: 3x^2 + 2x - 5 = 0"},
        tags=["mathematics", "algebra"]
    )
    
    writing_task = await task_manager.create_task(
        name="Blog Post",
        description="Write a blog post",
        input_data={"query": "Write a blog post about writing"},
        tags=["writing", "content"]
    )
    
    coding_task = await task_manager.create_task(
        name="Code Function",
        description="Write a Python function",
        input_data={"query": "Write a Python function for factorial"},
        tags=["coding", "python"]
    )
    
    # Get task router with capability matching strategy
    router = registry.get_task_router(RoutingStrategy.CAPABILITY_MATCH)
    
    # Route tasks
    math_agent_id = await router.route_task(math_task)
    writing_agent_id = await router.route_task(writing_task)
    coding_agent_id = await router.route_task(coding_task)
    
    print(f"Math task routed to: {math_agent_id}")
    print(f"Writing task routed to: {writing_agent_id}")
    print(f"Coding task routed to: {coding_agent_id}")
    
    # Change routing strategy to round robin
    router.set_strategy(RoutingStrategy.ROUND_ROBIN)
    
    # Route tasks again
    for i in range(3):
        task = await task_manager.create_task(
            name=f"Task {i}",
            description=f"Test task {i}",
            input_data={"query": f"Test query {i}"}
        )
        agent_id = await router.route_task(task)
        print(f"Task {i} routed to: {agent_id} (round robin)")

# Run the example
asyncio.run(task_routing_example())
```

### Batch Execution

```python
import asyncio
from symphony.core.registry import ServiceRegistry

async def batch_execution_example():
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Get components
    task_manager = registry.get_task_manager()
    agent_factory = registry.get_agent_factory()
    executor = registry.get_enhanced_executor()
    
    # Create multiple tasks
    tasks = []
    for i in range(5):
        task = await task_manager.create_task(
            name=f"Batch Task {i}",
            description=f"Task {i} for batch execution",
            input_data={"query": f"Process batch item {i}"}
        )
        tasks.append(task.id)
    
    # Get an agent
    agent_config_repo = registry.get_repository("agent_config")
    configs = await agent_config_repo.find_all()
    agent = await agent_factory.create_agent_from_id(configs[0].id)
    
    # Create task-agent pairs
    task_agent_pairs = [(task_id, agent) for task_id in tasks]
    
    # Execute in batch with limited concurrency
    results = await executor.batch_execute(
        task_agent_pairs, 
        max_concurrent=2
    )
    
    # Check results
    for i, result in enumerate(results):
        print(f"Task {i} status: {result.status}")
        if result.status == "completed":
            print(f"  Output: {result.output_data.get('result', '')[:50]}...")

# Run the example
asyncio.run(batch_execution_example())
```

## 3. Orchestration Layer

The Orchestration Layer builds on the Execution Layer to provide complex workflow orchestration capabilities.

### Key Components

- `WorkflowDefinition`: Declarative workflow definition
- `WorkflowStep`: Building blocks for workflows (task, conditional, parallel, loop)
- `WorkflowEngine`: Engine for executing workflow definitions
- `WorkflowTemplates`: Factory for common workflow patterns

### Creating and Executing a Custom Workflow

```python
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.persistence.memory_repository import InMemoryRepository
from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.orchestration.steps import TaskStep, ConditionalStep
from symphony.orchestration import register_orchestration_components

async def custom_workflow_example():
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Register orchestration components
    register_orchestration_components(registry)
    
    # Create a custom workflow definition
    workflow_def = WorkflowDefinition(
        name="Math Problem Solver",
        description="Workflow that solves math problems with different approaches"
    )
    
    # Initial classification step
    classify_step = TaskStep(
        name="Classify Problem",
        description="Classify the math problem as simple or complex",
        task_template={
            "name": "Problem Classification",
            "description": "Determine if the problem is simple or complex",
            "input_data": {
                "query": "Classify the following math problem as SIMPLE or COMPLEX. Only respond with the single word 'SIMPLE' or 'COMPLEX'.\n\nProblem: Find the derivative of f(x) = x^3 + 2x^2 - 5x + 7"
            }
        }
    )
    
    # Simple solution step
    simple_step = TaskStep(
        name="Simple Solution",
        description="Solve a simple math problem",
        task_template={
            "name": "Simple Math Solution",
            "description": "Provide a straightforward solution",
            "input_data": {
                "query": "Solve this simple math problem step by step:\n\nFind the derivative of f(x) = x^3 + 2x^2 - 5x + 7"
            }
        }
    )
    
    # Complex solution step
    complex_step = TaskStep(
        name="Complex Solution",
        description="Solve a complex math problem with detailed explanation",
        task_template={
            "name": "Complex Math Solution",
            "description": "Provide a detailed solution with explanation",
            "input_data": {
                "query": "Solve this complex math problem with detailed explanation and show all steps:\n\nFind the derivative of f(x) = x^3 + 2x^2 - 5x + 7"
            }
        }
    )
    
    # Conditional step to choose simple or complex path
    conditional_step = ConditionalStep(
        name="Solution Path",
        description="Choose solution approach based on problem classification",
        condition=f"step.{classify_step.id}.result.strip().upper() == 'COMPLEX'",
        if_branch=complex_step,
        else_branch=simple_step
    )
    
    # Add steps to workflow
    workflow_def = workflow_def.add_step(classify_step)
    workflow_def = workflow_def.add_step(conditional_step)
    
    # Save workflow definition
    workflow_def_repo = registry.get_repository("workflow_definition")
    await workflow_def_repo.save(workflow_def)
    
    # Execute workflow
    workflow_engine = registry.get_service("workflow_engine")
    workflow = await workflow_engine.execute_workflow(workflow_def)
    
    # Display results
    print(f"Workflow status: {workflow.status}")
    if "context" in workflow.metadata:
        context = workflow.metadata["context"]
        
        classification = context.get(f"step.{classify_step.id}.result", "").strip()
        print(f"\nProblem Classification: {classification}")
        
        if classification.upper() == "COMPLEX":
            solution = context.get(f"step.{complex_step.id}.result", "Not found")
            print("\nComplex Solution:")
        else:
            solution = context.get(f"step.{simple_step.id}.result", "Not found")
            print("\nSimple Solution:")
            
        print("-" * 40)
        print(solution)

# Run the example
asyncio.run(custom_workflow_example())
```

### Using Workflow Templates

```python
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.orchestration import register_orchestration_components

async def templates_example():
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Register orchestration components
    register_orchestration_components(registry)
    
    # Get workflow templates
    templates = registry.get_service("workflow_templates")
    
    # 1. Create a critic-revise workflow
    critic_workflow = templates.critic_revise(
        name="Blog Post Creation",
        main_prompt="Write a short blog post about the benefits of AI assistants in daily life.",
        critique_prompt="Review the blog post critically. Identify areas for improvement in terms of clarity, engagement, and factual accuracy.",
        revision_prompt="Revise the blog post based on the critique to create an improved version."
    )
    
    # Save and execute the workflow
    workflow_def_repo = registry.get_repository("workflow_definition")
    await workflow_def_repo.save(critic_workflow)
    
    workflow_engine = registry.get_service("workflow_engine")
    critic_result = await workflow_engine.execute_workflow(critic_workflow)
    
    print("=== Critic-Revise Workflow Result ===")
    print(f"Status: {critic_result.status}")
    if critic_result.status == "completed":
        context = critic_result.metadata["context"]
        # Extract and print the final revision
        revision_key = next((k for k in context.keys() if k.startswith("step.") and k.endswith(".result") and "Revision" in context.get(f"{k.split('.')[0]}.{k.split('.')[1]}.name", "")), None)
        if revision_key:
            print("\nFinal Revised Version:")
            print("-" * 40)
            print(context[revision_key][:500] + "...")
    
    # 2. Create a parallel experts workflow
    experts_workflow = templates.parallel_experts(
        name="Smart Home Analysis",
        prompt="What are the key considerations when setting up a smart home system?",
        expert_roles=["Technology", "Security", "Home Design"],
        summary_prompt="Synthesize the expert opinions into a comprehensive guide for setting up a smart home system."
    )
    
    # Save and execute the workflow
    await workflow_def_repo.save(experts_workflow)
    experts_result = await workflow_engine.execute_workflow(experts_workflow)
    
    print("\n=== Parallel Experts Workflow Result ===")
    print(f"Status: {experts_result.status}")
    if experts_result.status == "completed":
        context = experts_result.metadata["context"]
        # Extract and print the final synthesis
        synthesis_key = next((k for k in context.keys() if k.startswith("step.") and k.endswith(".result") and "Synthesis" in context.get(f"{k.split('.')[0]}.{k.split('.')[1]}.name", "")), None)
        if synthesis_key:
            print("\nSynthesized Expert Opinions:")
            print("-" * 40)
            print(context[synthesis_key][:500] + "...")

# Run the example
asyncio.run(templates_example())
```

### Creating an Iterative Refinement Workflow

```python
import asyncio
from symphony.core.registry import ServiceRegistry
from symphony.orchestration import register_orchestration_components

async def iterative_refinement_example():
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Register orchestration components
    register_orchestration_components(registry)
    
    # Get workflow templates
    templates = registry.get_service("workflow_templates")
    
    # Create an iterative refinement workflow
    refinement_workflow = templates.iterative_refinement(
        name="Business Proposal Refinement",
        initial_prompt="Draft a short business proposal for a new AI-powered productivity app.",
        feedback_prompt="Review the current draft and suggest specific improvements to make it more compelling and clear.",
        max_iterations=3,
        convergence_condition="'perfect' in step.result.lower() or 'excellent' in step.result.lower()"
    )
    
    # Save and execute the workflow
    workflow_def_repo = registry.get_repository("workflow_definition")
    await workflow_def_repo.save(refinement_workflow)
    
    workflow_engine = registry.get_service("workflow_engine")
    result = await workflow_engine.execute_workflow(refinement_workflow)
    
    print("=== Iterative Refinement Workflow Result ===")
    print(f"Status: {result.status}")
    if result.status == "completed":
        context = result.metadata["context"]
        
        # Extract information about the iterations
        iterations = next((context[k]["iterations"] for k in context.keys() if k.startswith("step.") and "iterations" in context[k]), None)
        if iterations:
            print(f"\nCompleted {len(iterations)} refinement iterations")
            
            # Show initial draft
            initial_key = next((k for k in context.keys() if k.startswith("step.") and k.endswith(".result") and "Initial" in context.get(f"{k.split('.')[0]}.{k.split('.')[1]}.name", "")), None)
            if initial_key:
                print("\nInitial Draft:")
                print("-" * 40)
                print(context[initial_key][:300] + "...")
            
            # Show final refinement
            final_iteration = max(iterations.keys(), key=int)
            print(f"\nFinal Refinement (Iteration {final_iteration}):")
            print("-" * 40)
            print(iterations[final_iteration]["result"][:300] + "...")

# Run the example
asyncio.run(iterative_refinement_example())
```

## 4. Complete Application Example

Let's put it all together in a complete application example:

```python
import asyncio
import os
import json
from typing import Dict, Any

from symphony.core.registry import ServiceRegistry
from symphony.core.task import Task
from symphony.core.agent_config import AgentConfig, AgentCapabilities
from symphony.execution.workflow_tracker import Workflow, WorkflowStatus
from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.orchestration.steps import TaskStep, ConditionalStep, ParallelStep
from symphony.persistence.file_repository import FileSystemRepository
from symphony.orchestration import register_orchestration_components

async def complete_application_example():
    """Complete example demonstrating all Symphony layers working together."""
    print("\n=== Symphony Complete Application Example ===\n")
    
    # Set up directory for storage
    os.makedirs("./data", exist_ok=True)
    
    # Set up registry
    registry = ServiceRegistry.get_instance()
    
    # Create repositories
    task_repo = FileSystemRepository(Task, "./data")
    workflow_repo = FileSystemRepository(Workflow, "./data")
    agent_config_repo = FileSystemRepository(AgentConfig, "./data")
    workflow_def_repo = FileSystemRepository(WorkflowDefinition, "./data")
    
    # Register repositories
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("workflow_definition", workflow_def_repo)
    
    # Register orchestration components
    register_orchestration_components(registry)
    
    # Create agent configurations
    writer_agent = AgentConfig(
        name="WriterAgent",
        role="Content Writer",
        instruction_template="You are a creative content writer who excels at generating engaging content.",
        capabilities=AgentCapabilities(
            expertise=["writing", "content", "creativity"]
        )
    )
    
    editor_agent = AgentConfig(
        name="EditorAgent",
        role="Content Editor",
        instruction_template="You are a meticulous editor who excels at improving content clarity, flow, and correctness.",
        capabilities=AgentCapabilities(
            expertise=["editing", "review", "clarity"]
        )
    )
    
    # Save agent configurations
    await agent_config_repo.save(writer_agent)
    await agent_config_repo.save(editor_agent)
    print(f"Created agent configurations for {writer_agent.name} and {editor_agent.name}")
    
    # Get workflow templates
    templates = registry.get_service("workflow_templates")
    
    # Create a multi-stage content creation workflow
    workflow_def = WorkflowDefinition(
        name="Content Creation Pipeline",
        description="A multi-stage pipeline for creating and refining content"
    )
    
    # 1. Research step
    research_step = TaskStep(
        name="Research",
        description="Research the topic",
        task_template={
            "name": "Research",
            "description": "Research the given topic and gather key points",
            "input_data": {
                "query": "Research the topic of 'artificial intelligence in healthcare' and provide 5 key points that should be covered in an article."
            }
        },
        agent_id=writer_agent.id
    )
    
    # 2. First draft step
    draft_step = TaskStep(
        name="First Draft",
        description="Write the first draft based on research",
        task_template={
            "name": "First Draft",
            "description": "Write first draft based on research",
            "input_data": {
                "query": f"Write a well-structured 500-word article about 'artificial intelligence in healthcare' covering these key points:\n\n{{{{step.{research_step.id}.result}}}}"
            }
        },
        agent_id=writer_agent.id
    )
    
    # 3. Review step (parallel reviews from different perspectives)
    clarity_review_step = TaskStep(
        name="Clarity Review",
        description="Review for clarity and readability",
        task_template={
            "name": "Clarity Review",
            "description": "Review for clarity and readability",
            "input_data": {
                "query": f"Review this article for clarity and readability. Identify specific areas where the text could be clearer or more engaging:\n\n{{{{step.{draft_step.id}.result}}}}"
            }
        },
        agent_id=editor_agent.id
    )
    
    accuracy_review_step = TaskStep(
        name="Accuracy Review",
        description="Review for factual accuracy",
        task_template={
            "name": "Accuracy Review",
            "description": "Review for factual accuracy",
            "input_data": {
                "query": f"Review this article for factual accuracy. Identify any statements that might be incorrect or need verification:\n\n{{{{step.{draft_step.id}.result}}}}"
            }
        },
        agent_id=editor_agent.id
    )
    
    # Combine reviews in parallel
    parallel_review_step = ParallelStep(
        name="Parallel Reviews",
        description="Conduct multiple reviews in parallel",
        steps=[clarity_review_step, accuracy_review_step]
    )
    
    # 4. Final revision step
    revision_step = TaskStep(
        name="Final Revision",
        description="Revise the draft based on reviews",
        task_template={
            "name": "Final Revision",
            "description": "Revise the draft based on reviews",
            "input_data": {
                "query": f"Revise this article based on the following reviews:\n\nOriginal Draft:\n{{{{step.{draft_step.id}.result}}}}\n\nClarity Review:\n{{{{step.{parallel_review_step.id}.results.0.result}}}}\n\nAccuracy Review:\n{{{{step.{parallel_review_step.id}.results.1.result}}}}"
            }
        },
        agent_id=writer_agent.id
    )
    
    # Add all steps to the workflow
    workflow_def = workflow_def.add_step(research_step)
    workflow_def = workflow_def.add_step(draft_step)
    workflow_def = workflow_def.add_step(parallel_review_step)
    workflow_def = workflow_def.add_step(revision_step)
    
    # Save workflow definition
    await workflow_def_repo.save(workflow_def)
    print(f"Created and saved workflow definition: {workflow_def.name}")
    
    # Execute workflow
    workflow_engine = registry.get_service("workflow_engine")
    print("Executing workflow...")
    workflow = await workflow_engine.execute_workflow(workflow_def)
    
    # Display results
    print(f"\nWorkflow completed with status: {workflow.status}")
    
    if workflow.status == WorkflowStatus.COMPLETED:
        print("\nWorkflow output summary:")
        context = workflow.metadata.get("context", {})
        
        # Get task results
        final_result = context.get(f"step.{revision_step.id}.result", "Not found")
        
        print("\n=== Final Article ===")
        print("-" * 60)
        print(final_result)
        print("-" * 60)
        
        # Save output to a file
        with open("./data/final_article.md", "w") as f:
            f.write(final_result)
        print(f"\nOutput saved to ./data/final_article.md")

# Run the example
asyncio.run(complete_application_example())
```

## Extending the Framework

### Creating Custom Step Types

You can extend the workflow orchestration layer by creating custom step types:

```python
from symphony.orchestration.workflow_definition import WorkflowStep, WorkflowContext, StepResult

class SummarizationStep(WorkflowStep):
    """Step that summarizes the outputs of previous steps."""
    
    def __init__(self, name, source_step_ids, max_length=200, description=""):
        super().__init__(name, description)
        self.source_step_ids = source_step_ids
        self.max_length = max_length
        
    async def execute(self, context: WorkflowContext) -> StepResult:
        """Summarize outputs from source steps."""
        try:
            # Gather all source contents
            contents = []
            for step_id in self.source_step_ids:
                result = context.get(f"step.{step_id}.result")
                if result:
                    contents.append(result)
            
            if not contents:
                return StepResult(
                    success=False,
                    output={},
                    error="No source content found to summarize"
                )
            
            # Get task manager to create a summary task
            task_manager = context.get_service("task_manager")
            
            # Combine all content with proper spacing
            combined = "\n\n---\n\n".join(contents)
            
            # Create a summarization task
            summary_task = await task_manager.create_task(
                name=f"Summarize {self.name}",
                description=f"Summarize multiple pieces of content",
                input_data={
                    "query": f"Summarize the following content in no more than {self.max_length} words:\n\n{combined}"
                }
            )
            
            # Execute the task
            router = context.get_service("task_router")
            agent_factory = context.get_service("agent_factory")
            executor = context.get_service("enhanced_executor")
            
            agent_id = await router.route_task(summary_task)
            agent = await agent_factory.create_agent_from_id(agent_id)
            
            result_task = await executor.execute_task(
                summary_task.id,
                agent,
                workflow_id=context.workflow_id
            )
            
            # Store in context
            summary = result_task.output_data.get("result", "")
            context.set(f"step.{self.id}.result", summary)
            
            return StepResult(
                success=result_task.status == "completed",
                output={"result": summary},
                task_id=summary_task.id,
                error=result_task.error
            )
            
        except Exception as e:
            return StepResult(
                success=False,
                output={},
                error=f"Summarization error: {str(e)}"
            )
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            "source_step_ids": self.source_step_ids,
            "max_length": self.max_length
        })
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SummarizationStep':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            source_step_ids=data["source_step_ids"],
            max_length=data.get("max_length", 200)
        )
```

### Creating Custom Workflow Templates

You can also create custom workflow templates for specific use cases:

```python
from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.orchestration.steps import TaskStep, ConditionalStep, ParallelStep, LoopStep

def create_research_synthesis_workflow(
    topic: str,
    perspectives: List[str],
    agent_id: Optional[str] = None
) -> WorkflowDefinition:
    """Create a workflow for researching a topic from multiple perspectives and synthesizing findings.
    
    Args:
        topic: The research topic
        perspectives: List of perspectives to research from
        agent_id: Optional agent ID to use
        
    Returns:
        Research synthesis workflow definition
    """
    workflow = WorkflowDefinition(
        name=f"Research Synthesis: {topic}",
        description=f"Research {topic} from multiple perspectives and synthesize findings"
    )
    
    # Initial step to generate research questions
    questions_step = TaskStep(
        name="Generate Questions",
        description=f"Generate research questions about {topic}",
        task_template={
            "name": "Generate Research Questions",
            "description": f"Generate research questions about {topic}",
            "input_data": {
                "query": f"Generate 3 specific research questions about {topic} that would be valuable to explore. Format as a numbered list."
            }
        },
        agent_id=agent_id
    )
    
    workflow = workflow.add_step(questions_step)
    
    # Create research steps for each perspective
    research_steps = []
    
    for perspective in perspectives:
        research_step = TaskStep(
            name=f"Research: {perspective}",
            description=f"Research {topic} from {perspective} perspective",
            task_template={
                "name": f"Research: {perspective}",
                "description": f"Research from {perspective} perspective",
                "input_data": {
                    "query": f"Research {topic} from the perspective of {perspective}, addressing these questions:\n\n{{{{step.{questions_step.id}.result}}}}"
                }
            },
            agent_id=agent_id
        )
        research_steps.append(research_step)
    
    # Execute research in parallel
    parallel_research = ParallelStep(
        name="Parallel Research",
        description="Conduct research from multiple perspectives in parallel",
        steps=research_steps
    )
    
    workflow = workflow.add_step(parallel_research)
    
    # Build the synthesis template
    synthesis_template = {
        "name": "Research Synthesis",
        "description": "Synthesize research findings",
        "input_data": {
            "query": f"Synthesize the following research on {topic} into a comprehensive analysis that compares and contrasts findings from different perspectives. Aim for a balanced view that integrates these diverse perspectives:\n\n"
        }
    }
    
    # Add each perspective's findings to the template
    for i, perspective in enumerate(perspectives):
        synthesis_template["input_data"]["query"] += (
            f"\n## {perspective} Perspective:\n"
            f"{{{{step.{parallel_research.id}.results.{i}.result}}}}\n"
        )
    
    # Final synthesis step
    synthesis_step = TaskStep(
        name="Research Synthesis",
        description=f"Synthesize research findings on {topic}",
        task_template=synthesis_template,
        agent_id=agent_id
    )
    
    workflow = workflow.add_step(synthesis_step)
    
    return workflow
```

## Conclusion

This guide demonstrates the powerful capabilities of the enhanced Symphony framework with its three layers:

1. **Persistence Layer**: For storing and retrieving entities
2. **Execution Layer**: For executing tasks with advanced capabilities
3. **Orchestration Layer**: For defining and running complex workflows

By combining these layers, you can create sophisticated agent-based applications with complex orchestration patterns, while maintaining a clean, extensible architecture.

The framework is designed to be modular and extensible, allowing you to:

- Add custom storage implementations to the Persistence Layer
- Extend the Execution Layer with new execution strategies
- Create custom step types and workflow templates in the Orchestration Layer

This modular design ensures that Symphony can grow and adapt to your specific needs while maintaining a consistent architecture and API.