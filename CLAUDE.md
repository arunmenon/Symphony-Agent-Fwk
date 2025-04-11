# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Testing Commands
- Install: `pip install -e .`
- Install with dev dependencies: `pip install -e ".[dev]"`
- Run all tests: `pytest`
- Run specific test category: `pytest -m "unit"` (unit, integration, memory, agents, etc.)
- Run single test: `pytest path/to/test.py::test_function_name`
- Run with coverage: `pytest --cov=symphony`
- Lint code: `ruff check .`
- Type check: `mypy .`
- Auto-format: `black .`

## Code Style Guidelines
- Use **descriptive variable names** that reflect purpose
- Follow imports order: stdlib → third-party → local modules
- Use type hints for all function parameters and return values
- Naming: Classes=PascalCase, functions/methods=snake_case, constants=UPPER_SNAKE_CASE
- Error handling: Use specific error types with clear error messages
- Document public APIs with Google style docstrings
- Use Pydantic BaseModel for data validation and structured objects
- Keep functions focused (single responsibility principle)
- Use async/await for I/O-bound operations
- Apply builder pattern for fluent interfaces
- Follow dependency injection through container system
- Line length: 100 characters max
- Follow PEP 8 style guidelines

## Git Commit Guidelines
- Write concise, descriptive commit messages
- Focus on the "why" rather than just the "what"
- Use present tense (e.g., "Add feature" not "Added feature")
- NEVER include Claude Code or any AI assistant attribution in commit messages
- CRITICAL: Do not mention AI or Claude in commit messages or metadata
- Structure commits logically around related changes
- Keep commits focused on single concerns

## Prompt Template Guidelines

### Externalize All Prompt Templates
- **NEVER hardcode prompt templates in Python files**
- Always use external template files stored in a centralized location
- Place prompt templates in appropriate directories:
  - `task-prompts/` for agent task instructions
  - `system-prompts/` for system instructions
  - `example-prompts/` for few-shot examples

### Template Organization
- Group templates by functional area (planning, exploration, etc.)
- Use descriptive filenames that indicate purpose (e.g., `category_planning.txt`)
- Include version information in template files when making significant changes
- Document template variables with comments

### Template Loading
- Create a dedicated template loader that:
  - Caches templates for performance
  - Validates required variables
  - Handles template not found errors gracefully
- Example implementation:
```python
def load_prompt_template(template_name: str) -> str:
    """Load prompt template from filesystem.
    
    Args:
        template_name: Name of template file without directory or extension
        
    Returns:
        Template content as string
        
    Raises:
        TemplateNotFoundError: If template cannot be found
    """
    template_path = os.path.join(TEMPLATE_DIR, f"{template_name}.txt")
    if not os.path.exists(template_path):
        raise TemplateNotFoundError(f"Template {template_name} not found at {template_path}")
        
    with open(template_path, "r") as f:
        return f.read()
```

### Template Variable Substitution
- Use a consistent method for variable substitution
- Prefer named placeholders over positional formatting
- Consider using a template engine like Jinja2 for complex templates
- Example usage:
```python
# Load template
planning_template = load_prompt_template("planning")

# Format template with variables
formatted_prompt = planning_template.format(
    category=category,
    enhanced_fields=", ".join(enhanced_fields),
    jurisdictions=", ".join(jurisdictions)
)
```

### Template Refactoring Process
1. Identify all hardcoded templates in the codebase
2. Extract each template to an appropriate external file
3. Update code to load and format the external template
4. Add validation for required template variables
5. Document the template's purpose and variables

## Symphony Architecture Blueprint

### Core Primitives and Abstractions

#### Core Domain Models
- **Agent** (`symphony/agents/base.py`): Represents an AI entity with capabilities, memory, and tools
- **Task** (`symphony/core/task.py`): Unit of work that can be executed by an agent (has lifecycle: pending → running → completed/failed)
- **Workflow** (`symphony/execution/workflow_tracker.py`): Orchestrated collection of steps with defined execution order
- **WorkflowStep** (`symphony/orchestration/steps.py`): Individual operation in a workflow (task execution, decision point, or processing)
- **Memory** (`symphony/memory/base.py`): Storage for contextual information and conversation history
- **Pattern** (`symphony/patterns/base.py`): Reusable interaction strategy that can be applied to tasks

#### Key Abstractions
- **Registry** (`symphony/core/registry.py`): Service locator pattern implementation for component access
- **Repository** (`symphony/persistence/repository.py`): Data access abstraction for persistence
- **Facades** (`symphony/facade/`): Simplified interfaces to subsystems (agents, tasks, workflows)
- **Builders** (`symphony/builder/`): Fluent interfaces for constructing complex objects
- **Patterns** (`symphony/patterns/`): Composable interaction strategies that can be applied to agents

### Key Components and Their Relationships

#### Symphony API (Main Entry Point)
- Central facade for all Symphony operations (`symphony/api.py`)
- Provides methods for creating and managing agents, tasks, and workflows
- Handles initialization and service registration

#### Agents Subsystem
- **AgentConfig** (`symphony/core/agent_config.py`): Defines agent capabilities, instructions, and metadata
- **AgentBase** (`symphony/agents/base.py`): Abstract base class for all agent implementations
- **ReactiveAgent** (`symphony/agents/base.py`): Simple agent that responds to messages directly
- **PlannerAgent** (`symphony/agents/planning.py`): Agent that creates and follows structured plans
- **Memory Augmented Agents** (`symphony/agents/kg_enhanced.py`, `symphony/agents/local_kg_enhanced.py`): Agents enhanced with various memory strategies

#### Orchestration Layer
- **WorkflowDefinition** (`symphony/orchestration/workflow_definition.py`): Declarative description of workflow structure
- **WorkflowStep** (`symphony/orchestration/steps.py`): Abstract unit of execution in workflows
- **WorkflowContext** (`symphony/orchestration/workflow_definition.py`): Shared state across workflow execution
- **WorkflowEngine** (`symphony/orchestration/engine.py`): Executes workflow definitions

#### Execution Layer
- **WorkflowTracker** (`symphony/execution/workflow_tracker.py`): Tracks workflow execution state
- **Workflow** (`symphony/execution/workflow_tracker.py`): Runtime instance of executing workflow
- **TaskManager** (`symphony/core/task_manager.py`): Handles task execution and lifecycle
- **EnhancedAgent** (`symphony/execution/enhanced_agent.py`): Agent with execution enhancements
- **Router** (`symphony/execution/router.py`): Routes tasks to appropriate handlers

#### Memory System
- **BaseMemory** (`symphony/memory/base.py`): Abstract memory interface
- **ConversationMemory** (`symphony/memory/memory_manager.py`): Stores message history
- **VectorMemory** (`symphony/memory/vector_memory.py`): Semantic search capabilities
- **KGMemory** (`symphony/memory/kg_memory.py`): Knowledge graph-based memory
- **MemoryManager** (`symphony/memory/memory_manager.py`): Manages different memory types
- **ImportanceStrategies** (`symphony/memory/importance.py`): Determines importance of memories

#### Patterns System
- **ChainOfThought** (`symphony/patterns/reasoning/chain_of_thought.py`): Sequential reasoning with intermediate steps
- **RecursiveToolUse** (`symphony/patterns/tool_usage/recursive_tool_use.py`): Recursive pattern for hierarchical tasks
- **VerifyExecute** (`symphony/patterns/tool_usage/verify_execute.py`): Verification before execution
- **ExpertPanel** (`symphony/patterns/multi_agent/expert_panel.py`): Multi-agent collaboration
- **PatternRegistry** (`symphony/patterns/registry.py`): Registry for available patterns

#### Persistence Layer
- **Repository** (`symphony/persistence/repository.py`): Interface for data access
- **InMemoryRepository** (`symphony/persistence/memory_repository.py`): In-memory implementation
- **FileSystemRepository** (`symphony/persistence/file_repository.py`): File-based persistence

#### State Management System
- **CheckpointManager** (`symphony/core/state/checkpoint.py`): Creates and manages system state snapshots
- **EntityRestorer** (`symphony/core/state/restore.py`): Restores entities from serialized state
- **StorageProvider** (`symphony/core/state/storage.py`): Handles state storage operations
- **Serialization** (`symphony/core/state/serialization.py`): Serializes and deserializes state

### Builder Framework
- **AgentBuilder** (`symphony/builder/agent_builder.py`): Builder for creating agents
- **TaskBuilder** (`symphony/builder/task_builder.py`): Builder for creating tasks
- **WorkflowBuilder** (`symphony/builder/workflow_builder.py`): Builder for creating workflows
- **WorkflowStepBuilder** (`symphony/builder/workflow_step_builder.py`): Builder for creating workflow steps

### Facade Layer
- **AgentFacade** (`symphony/facade/agents.py`): Facade for agent operations
- **TaskFacade** (`symphony/facade/tasks.py`): Facade for task operations
- **WorkflowFacade** (`symphony/facade/workflows.py`): Facade for workflow operations

### Main Design Patterns

- **Builder Pattern**: For constructing complex objects with fluent interfaces (AgentBuilder, WorkflowBuilder)
- **Facade Pattern**: Simplifies subsystem access (AgentFacade, TaskFacade, WorkflowFacade)
- **Repository Pattern**: Abstracts data access logic (InMemoryRepository, FileSystemRepository)
- **Registry Pattern**: Central service locator for component discovery (ServiceRegistry)
- **Strategy Pattern**: Encapsulates algorithms in interchangeable components (memory strategies, patterns)
- **Factory Pattern**: Creates objects without exposing creation logic (AgentFactory)
- **Composition Pattern**: Complex objects built from smaller components (Workflow composition)

### Architecture Layers

- **API Layer**: Symphony class, builders, facades
- **Domain Layer**: Core entities (Agent, Task, Workflow)
- **Application Layer**: Orchestration engine, workflow execution
- **Infrastructure Layer**: Persistence, external service integrations
- **Tool Layer**: Tool definitions and implementations

### Taxonomy Planner Application

#### Domain-Specific Components
- **TaxonomyPlanner** (`applications/taxonomy_planner/main.py`): Main application coordinator
- **TaxonomyStore** (`applications/taxonomy_planner/persistence.py`): Domain-specific persistence for taxonomies
- **SearchEnhancedExplorationPattern** (`applications/taxonomy_planner/patterns.py`): Specialized exploration pattern
- **LLMTracingPlugin** (`applications/taxonomy_planner/llm_tracing_plugin.py`): Plugin for capturing traces of LLM interactions

#### Domain-Specific Agents
- **PlannerAgent/ExplorerAgent/etc.** (`applications/taxonomy_planner/agents.py`): Specialized agents for taxonomy planning
- **TaxonomyConfig** (`applications/taxonomy_planner/config.py`): Configuration for taxonomy generation

#### Domain-Specific Tools
- **Knowledge Base Tools** (`applications/taxonomy_planner/tools/knowledge_base.py`): Domain knowledge access
- **Search Tools** (`applications/taxonomy_planner/tools/search_tools.py`): External search capabilities
- **Compliance Tools** (`applications/taxonomy_planner/tools/compliance_tools.py`): Compliance mapping tools
- **Legal Tools** (`applications/taxonomy_planner/tools/legal_tools.py`): Legal mapping tools

#### Enhanced Taxonomy Structure
- **Basic Taxonomy**: Category hierarchies and relationships 
- **Enhanced Fields** (`applications/taxonomy_planner/persistence.py`): 
  - description: Text description of the category
  - enforcement_examples: Examples of enforcement actions
  - social_media_trends: Current trends related to the category
  - risk_level: Assessment of regulatory risk
  - detection_methods: Methods for detecting violations

#### Generation Scripts
- **generate_taxonomy.py**: Unified taxonomy generation script with `--enhanced` flag for additional fields
- **generate_us_taxonomies.sh**: Generates taxonomies for US jurisdictions with `--enhanced` option
- **generate_multiple.sh**: Batch generation for multiple categories
- **generate_compliance_taxonomies.py**: Higher-level compliance taxonomies generation script
- **analyze_traces.py**: Analyze traces from taxonomy generation runs
- **visualize_taxonomy.py/visualize_all.py**: Visualization tools for taxonomies

#### Symphony Integration
- **Correct Agent Execution Pattern**:
  1. Create agent with `symphony.build_agent()`
  2. Build and save agent with `symphony.agents.save_agent()`
  3. Create task with `symphony.build_task()` and `.with_query()`
  4. Build workflow with proper steps
  5. Execute workflow with `symphony.workflows.execute_workflow()`
- **Serialization Extensions**: Custom `DateTimeEncoder` for handling datetime serialization in Symphony components

#### Workflow Implementation (`applications/taxonomy_planner/main.py`)
1. **Planning Step**: Determine high-level structure
2. **Plan Processing**: Extract initial categories
3. **Exploration Step**: Recursive subcategory discovery 
4. **Compliance Mapping**: Associate regulatory requirements
5. **Legal Mapping**: Associate applicable laws
6. **Tree Building**: Construct final taxonomy with enhanced fields

### Key Architectural Principles
- **Extensibility**: Plugin architecture, abstract base classes
- **Composability**: Workflows from reusable steps, patterns from strategies
- **Separation of Concerns**: Clear boundaries between subsystems
- **Immutability**: Workflow definitions immutable, explicit state transitions
- **State Management**: Checkpoint/restore capabilities