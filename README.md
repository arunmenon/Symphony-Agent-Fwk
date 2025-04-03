# Symphony: Next-Generation Agentic Framework

Symphony is an advanced, modular framework for building complex AI agent systems. It provides a unified approach to creating, orchestrating, and managing multiple AI agents, with powerful integration with the Model Context Protocol (MCP) for standardized context management.

## Key Features

- **Multiple Agent Architectures**: Support for reactive agents, planning agents, and DAG-based workflows.
- **Multi-Agent Orchestration**: Coordinate multiple agents working together to solve complex tasks.
- **MCP Integration**: First-class support for the Model Context Protocol, providing standardized context management.
- **Prompt Management System**: Centralized registry for prompts with version control and hierarchical overrides.
- **Modular Plugin Architecture**: Extend with custom tools, memory implementations, LLM backends, and more.
- **Type-Safe Interactions**: Built on Pydantic models for robust data validation.
- **Model-Agnostic**: Works with any LLM implementation through a unified interface.

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

## Quick Start

Here's a simple example of creating and running a reactive agent with MCP integration:

```python
from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.base import MockLLMClient
from symphony.mcp.base import MCPManager
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import tool

# Define a tool that will be exposed through MCP
@tool(name="calculator", description="Perform calculations")
def calculator(operation: str, a: float, b: float) -> float:
    if operation == "add":
        return a + b
    # ... handle other operations

# Create components
registry = PromptRegistry()
registry.register_prompt(
    prompt_type="system",
    content="You are a helpful assistant with MCP capabilities.",
    agent_type="ReactiveAgent"
)

llm_client = MockLLMClient()
mcp_manager = MCPManager()

# Create and run agent
agent_config = AgentConfig(
    name="MyAssistant",
    agent_type="ReactiveAgent",
    tools=["calculator"],
    mcp_enabled=True
)

agent = ReactiveAgent(
    config=agent_config,
    llm_client=llm_client,
    prompt_registry=registry,
    mcp_manager=mcp_manager
)

# Run the agent asynchronously
async def main():
    response = await agent.run("Calculate 2 + 2")
    print(response)

import asyncio
asyncio.run(main())
```

## Core Concepts

### Model Context Protocol (MCP)

Symphony integrates with the official Model Context Protocol (MCP) for standardized context management. This provides:

- **Resources**: Access to structured data via URI schemes
- **Tools**: Standardized function calling capabilities
- **Context Management**: Dynamic context assembly

```python
from symphony.mcp.base import MCPManager

# Create MCP manager
mcp_manager = MCPManager()

# Register custom resources
@mcp_manager.mcp.resource("symphony://knowledge/{topic}")
def get_knowledge(topic: str, ctx: Context) -> str:
    # Return knowledge for the topic
    return knowledge_base.get(topic, "")

# Register tools
@mcp_manager.register_tool(name="calculate", description="Perform calculations")
def calculate(ctx: Context, operation: str, a: float, b: float) -> float:
    # Log the operation
    ctx.info(f"Calculating {a} {operation} {b}")
    # Perform calculation
    # ...
```

### Agents

Agents are the primary actors in Symphony. Each agent has:
- A role or goal defined by a system prompt
- Access to tools and memory
- A specific architecture (reactive, planning, etc.)
- Optional MCP integration

### Tools

Tools extend agent capabilities beyond text generation, allowing them to interact with external systems, process data, or perform specific actions.

```python
from symphony.tools.base import tool

@tool(name="calculator", description="Perform calculations")
def calculator(operation: str, a: float, b: float) -> float:
    """Perform a basic arithmetic calculation."""
    if operation == "add":
        return a + b
    # ... handle other operations
```

### Memory

Memory allows agents to store and retrieve information, including conversation history, knowledge, and intermediate results.

```python
from symphony.memory.base import ConversationMemory

memory = ConversationMemory()
memory.add_message(Message(role="user", content="Hello!"))
recent_messages = memory.get_messages(limit=5)
```

### Orchestration

Orchestrators manage the execution flow between multiple agents, supporting patterns like:
- Sequential execution
- Round-robin turns
- DAG-based workflows

```python
from symphony.orchestration.base import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator(
    config=orchestrator_config,
    llm_client=llm_client,
    prompt_registry=registry,
    turn_type=TurnType.SEQUENTIAL
)

result = await orchestrator.run("Analyze this data and write a report.")
```

### Prompt Management System

The Prompt Registry provides a centralized store for prompts with support for hierarchical overrides:

```python
from symphony.prompts.registry import PromptRegistry

registry = PromptRegistry("prompts.yaml")
registry.register_prompt(
    prompt_type="system",
    content="You are an expert researcher.",
    agent_type="ResearchAgent",
    agent_instance="ResearcherAlice"  # Optional instance-specific override
)

# Later, retrieve the prompt (instance → type → global fallback)
prompt = registry.get_prompt(
    prompt_type="system",
    agent_type="ResearchAgent",
    agent_instance="ResearcherAlice"
)
```

## Examples

The `examples/` directory contains complete examples demonstrating different aspects of the framework:

- `simple_agent.py` - Basic reactive agent with tools
- `planning_agent.py` - Agent that creates and follows a plan
- `multi_agent.py` - Coordinating multiple agents
- `dag_workflow.py` - Complex workflow using a directed acyclic graph
- `mcp_integration.py` - Integration with Model Context Protocol

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.