# Symphony Framework Architecture

Symphony is a next-generation agent framework designed for building complex AI agent systems. This document provides a comprehensive overview of Symphony's architecture.

## Core Design Principles

Symphony follows these key design principles:

1. **Modularity**: Components are loosely coupled and can be replaced or extended independently.
2. **Type Safety**: Pydantic models ensure type-safe data exchange between components.
3. **Open Standards**: Integration with open protocols like MCP and universal interfaces like LiteLLM.
4. **Extensibility**: Plugin architecture allows for third-party extensions.
5. **Event-Driven**: Communication between components via a standardized event system.

## System Architecture

![System Architecture](../images/architecture.png)

Symphony's architecture consists of these main components:

### Core (Symphony Core)

The central orchestration layer that initializes and coordinates the entire system:

- **Container**: Service locator pattern for dependency resolution
- **Configuration**: Multi-layered configuration system (environment, files, defaults)
- **Event Bus**: Publish-subscribe system for component communication
- **Plugin Manager**: Discovers and loads system extensions

### Agents

The primary actors in the system, agents are the intelligent entities that:

- Interact with language models (LLMs)
- Use tools to perform actions
- Maintain memory for stateful interactions
- Execute planning or reactive behaviors

Agent types include:
- **ReactiveAgent**: Simple, step-by-step logic
- **PlannerAgent**: Creates and follows plans
- **DAG-based Agents**: Execute complex graph workflows

### Tools

Extensions that give agents capabilities beyond text generation:

- Registered via `@tool` decorator
- Auto-generate schema from function signatures
- Provide sandbox enforcement (security)
- Integrate with MCP for standardized usage

### Memory

Persistence layer allowing agents to:

- Store conversation history
- Maintain working memory (scratchpad)
- Access long-term knowledge bases
- Perform vector search for relevant information

### Prompt Management

Centralized system for managing prompts with:

- Version control for prompts
- Hierarchical overrides (global → agent-type → agent-instance)
- Template support with variables
- Organized registry structure

### Model Context Protocol (MCP)

Integration with the open MCP standard:

- Resource management with URI scheme
- Dynamic context assembly
- Standardized tool interfaces
- Context sharing between agents

### LLM Interface

Unified API for language model providers:

- Multi-provider support via LiteLLM
- Streaming capabilities
- Function calling support
- Async/await API patterns

### Orchestration

Coordination layer for multi-agent workflows:

- Sequential execution
- Round-robin turn taking
- DAG-based workflows
- Environment for agent communication

## Data Flow

1. **Input**: User or system provides a task to the orchestrator
2. **Orchestration**: The orchestrator determines which agent(s) should handle the task
3. **Agent Processing**:
   - Agent uses prompt registry to get its system prompt
   - Agent consults memory for context
   - Agent calls LLM to generate a response or action
   - If action is needed, agent calls appropriate tools
4. **Tool Execution**: Tools perform actions and return results to the agent
5. **Memory Update**: Agent updates memory with new information
6. **Output**: Agent returns result to orchestrator, which may pass it to another agent or return it to the user

## Design Patterns

Symphony implements these software design patterns:

- **Factory Pattern**: For component creation (`AgentFactory`, `LLMClientFactory`, etc.)
- **Strategy Pattern**: For swappable algorithms (context policies, agent behaviors)
- **Repository Pattern**: For data access (prompt registry, tool registry)
- **Observer Pattern**: Via the event system for loose coupling
- **Dependency Injection**: Through the container system
- **Plugin Architecture**: For system extensibility

## File Structure

```
symphony/
├── agents/             # Agent implementations
├── core/               # Core framework components
│   ├── config.py       # Configuration management
│   ├── container.py    # Dependency injection container
│   ├── events.py       # Event system
│   ├── exceptions.py   # Exception hierarchy
│   ├── factory.py      # Component factories
│   └── plugin.py       # Plugin system
├── llm/                # LLM client implementations
├── mcp/                # Model Context Protocol integration
├── memory/             # Memory implementations
├── orchestration/      # Orchestration engines
├── prompts/            # Prompt management
├── tools/              # Tool abstractions
└── utils/              # Utilities and types
```

## Extension Points

Symphony provides these main extension points:

1. **Agents**: Custom agent implementations by subclassing `AgentBase`
2. **Tools**: New capabilities by using the `@tool` decorator
3. **Memory**: Custom memory backends by implementing `BaseMemory`
4. **LLM Clients**: Support for new LLM providers
5. **Plugins**: Full-featured extensions via the plugin system
6. **Orchestrators**: Custom coordination strategies

## Performance Considerations

- Async/await for concurrent operations
- Streaming support for real-time responses
- Efficient context management for token optimization
- Stateful memory for maintaining conversation context

## Security Model

- Tool sandboxing capabilities
- Configuration validation
- Input sanitization
- Exception handling and graceful degradation