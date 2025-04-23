# Symphony Public API Surface Inventory

This document lists all Symphony API components used by the Taxonomy Planner application. These components represent the public API that should be stabilized and maintained as part of the 0.1.0 release.

## Core Classes and Functions

### Primary API

- `Symphony` (from `symphony`)
  - Constructor: `Symphony(config, persistence_enabled)`
  - `setup(persistence_type, base_dir, with_patterns, state_dir)`
  - Properties:
    - `agents` - Agent facade
    - `tasks` - Task facade
    - `workflows` - Workflow facade
    - `patterns` - Patterns facade
  - Methods:
    - `build_agent()`
    - `build_task()`
    - `build_workflow()`
    - `build_pattern()`
    - `create_checkpoint(name)`
    - `resume_from_checkpoint(checkpoint_id)`
    - `resume_latest_checkpoint()`
    - `list_checkpoints()`
    - `delete_checkpoint(checkpoint_id)`

### Agent API

- `AgentFacade` (from `symphony.facade.agents`)
  - `save_agent(agent)`
  - `get_agent(agent_id)`
  - `create_agent(...)`
  - `execute_agent(agent_id, query)`

- `AgentBuilder` (from `symphony.builder.agent_builder`)
  - `name(name)`
  - `description(description)`
  - `with_model(model_name)`
  - `with_tools(tools)`
  - `with_memory(memory)`
  - `build()`

### Task API

- `TaskFacade` (from `symphony.facade.tasks`)
  - `save_task(task)`

- `TaskBuilder` (from `symphony.builder.task_builder`)
  - `with_query(query)`

### Workflow API

- `WorkflowFacade` (from `symphony.facade.workflows`)
  - `execute_workflow(workflow, initial_context, auto_checkpoint, resume_from_checkpoint)`

- `WorkflowBuilder` (from `symphony.builder.workflow_builder`)
  - `create(name, description)`
  - `add_step(step)`
  - `build()`
  - `build_step()`

- `WorkflowStepBuilder` (implied but not directly imported)
  - `name(name)`
  - `description(description)`
  - `agent(agent)`
  - `task(task)`
  - `pattern(pattern)`
  - `context_data(context)`
  - `output_key(key)`
  - `processing_function(func)`
  - `build()`

### Patterns API

- `PatternsFacade` (from `symphony.facade.patterns`)
  - `apply_pattern(pattern, agent, task, context)`

- `Pattern` (from `symphony.patterns.base`)
  - Base class for patterns

- Specific Pattern classes:
  - `ChainOfThoughtPattern` (from `symphony.patterns.reasoning.chain_of_thought`)
  - `RecursiveToolUsePattern` (from `symphony.patterns.tool_usage.recursive_tool_use`)
  - `VerifyExecutePattern` (from `symphony.patterns.tool_usage.verify_execute`)
  - `ExpertPanelPattern` (from `symphony.patterns.multi_agent.expert_panel`)
  - `ReflectionPattern` (from `symphony.patterns.learning.reflection`)

### Plugin System

- `LLMPlugin` (from `symphony.core.plugin`)
- `Plugin` (from `symphony.core.plugin`)
- `EventBus`, `Event`, `EventType` (from `symphony.core.events`)
- `Container` (from `symphony.core.container`)

### Persistence

- `FileSystemRepository` (from `symphony.persistence.file_repository`)

## Integration Points

In addition to the classes and methods listed above, the following integration points are used by the Taxonomy Planner:

1. Custom tool registration:
   ```python
   # Tool registration directly into Symphony object
   symphony._custom_tools.update(tools)
   ```

2. Event system for plugins:
   ```python
   # Tracing and plugin system using events
   from symphony.core.events import EventBus, Event, EventType
   from symphony.core.plugin import LLMPlugin
   ```

3. Workflow context propagation - the workflow system passes context between steps

## Usage Patterns

1. **Agent Creation and Execution**:
   ```python
   agent_builder = symphony.build_agent()
   agent = agent_builder.name("AgentName").description("...").with_model("model").build()
   agent_id = await symphony.agents.save_agent(agent)
   # Direct execution
   result = await agent.execute(prompt)
   # Or via facade
   result = await symphony.agents.execute_agent(agent_id, prompt)
   ```

2. **Workflow Creation and Execution**:
   ```python
   workflow_builder = symphony.build_workflow()
   workflow_builder.create(name="WorkflowName", description="...")
   
   step = workflow_builder.build_step()
       .name("StepName")
       .agent(agent)
       .task(task_prompt)
       .pattern(pattern)
       .context_data({...})
       .output_key("output")
       .build()
   
   workflow_builder.add_step(step)
   workflow = workflow_builder.build()
   
   result = await symphony.workflows.execute_workflow(
       workflow=workflow,
       initial_context={...},
       auto_checkpoint=True,
       resume_from_checkpoint=True
   )
   ```

3. **Pattern Application**:
   ```python
   result = await symphony.patterns.apply_pattern(
       pattern=pattern,
       agent=agent,
       task=task,
       context=context
   )
   ```

## Taxonomy Planner-Specific Extensions

These items are specific to the Taxonomy Planner but might indicate potential future extensions to the Symphony core:

1. `SearchEnhancedExplorationPattern` - A custom pattern that extends `RecursiveToolUsePattern`
2. `TaxonomyStore` - A custom persistence mechanism for taxonomy data
3. `LLMTracingPlugin` - A plugin for tracing LLM calls
4. `SearchTracingPlugin` - A plugin for tracing search operations