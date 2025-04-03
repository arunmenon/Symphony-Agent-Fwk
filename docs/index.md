# Symphony Framework Documentation

Welcome to the Symphony Framework documentation! Symphony is a next-generation agent framework designed for building complex AI agent systems with multiple LLM providers and standardized context management.

## Quick Links

- [Getting Started Tutorial](tutorials/getting_started.md)
- [Architecture Overview](architecture/overview.md)
- [Component Reference](architecture/components.md)

## Introduction

Symphony is designed from the ground up to provide a modular, extensible framework for building AI agent systems. With Symphony, you can:

- Create agents with different architectures (reactive, planning, DAG-based)
- Connect to 100+ LLM providers through LiteLLM integration
- Leverage the Model Context Protocol (MCP) for standardized context management
- Orchestrate multiple agents to work together on complex tasks
- Extend the framework with custom tools, memory implementations, and plugins

## Installation

```bash
# Clone the repository
git clone https://github.com/arunmenon/Symphony-Agent-Fwk.git
cd Symphony-Agent-Fwk

# Install in development mode
pip install -e .

# Install optional dependencies
pip install -e ".[dev,openai,anthropic,cli]"
```

## Examples

Symphony comes with several examples that demonstrate its capabilities:

- `simple_agent.py` - A basic reactive agent with a calculator tool
- `planning_agent.py` - An agent that creates and follows plans
- `multi_agent.py` - A multi-agent system with researcher and writer agents
- `dag_workflow.py` - A complex workflow using a directed acyclic graph
- `mcp_integration.py` - Integration with the Model Context Protocol
- `litellm_integration.py` - Using different LLM providers with LiteLLM
- `modular_architecture.py` - Demonstrating Symphony's design patterns
- `comprehensive_tutorial.py` - A complete example of a research assistant
- `benchmarking.py` - Performance benchmarking of various Symphony components

## Core Concepts

### Agents

Agents are intelligent entities that use language models to make decisions and take actions. Symphony supports multiple agent architectures:

- **ReactiveAgent** - Simple, step-by-step logic
- **PlannerAgent** - Creates and follows plans
- **DAG-based Agents** - Execute complex graph workflows

### Tools

Tools extend agent capabilities beyond text generation, allowing them to perform actions like calculations, web searches, or data processing. Tools are defined with a simple decorator syntax:

```python
@tool(name="calculator", description="Perform calculations")
def calculator(operation: str, a: float, b: float) -> float:
    if operation == "add":
        return a + b
    # ...
```

### Memory

Memory allows agents to store and retrieve information across interactions, including conversation history and contextual data.

### Prompt Management

Symphony provides a centralized prompt registry that manages prompts with version control and hierarchical overrides.

### Orchestration

The orchestration layer coordinates multiple agents, allowing them to work together on complex tasks using patterns like sequential execution, round-robin turns, or DAG-based workflows.

### MCP and LiteLLM Integration

Symphony integrates with:

- **Model Context Protocol (MCP)** - Standardized context management
- **LiteLLM** - Unified API for 100+ LLM providers

## Advanced Architecture

Symphony implements modern software design patterns:

- **Factory Pattern** - For component creation
- **Service Locator** - For dependency management
- **Event System** - For component communication
- **Plugin Architecture** - For third-party extensions
- **Configuration Management** - For flexible settings

See the [Architecture Overview](architecture/overview.md) for more details.

## Contributing

We welcome contributions to Symphony! Please see the [GitHub repository](https://github.com/arunmenon/Symphony-Agent-Fwk) for more information.