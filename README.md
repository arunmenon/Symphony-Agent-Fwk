# Symphony: Next-Generation Agentic Framework

Symphony is an advanced, modular framework for building complex AI agent systems. It provides a unified approach to creating, orchestrating, and managing multiple AI agents, with powerful integration with the Model Context Protocol (MCP) for standardized context management and LiteLLM for multi-provider LLM support.

## Key Features

- **Multiple Agent Architectures**: Support for reactive agents, planning agents, and DAG-based workflows.
- **Multi-Agent Orchestration**: Coordinate multiple agents working together to solve complex tasks.
- **Patterns Library**: Reusable interaction patterns like chain-of-thought, reflection, and multi-agent collaboration.
- **MCP Integration**: First-class support for the Model Context Protocol, providing standardized context management.
- **LiteLLM Integration**: Seamless integration with over 100+ LLM providers through a unified interface.
- **Advanced Memory Architecture**: Multi-tier memory system with working and long-term memory, automatic importance assessment and memory consolidation.
- **Prompt Management System**: Centralized registry for prompts with version control and hierarchical overrides.
- **Modular Plugin Architecture**: Extend with custom tools, memory implementations, LLM backends, and more.
- **Type-Safe Interactions**: Built on Pydantic models for robust data validation.

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

Here's a simple example of using Symphony with patterns:

```python
import asyncio
from symphony.api import Symphony
from symphony.agents.config import AgentConfig

async def main():
    # Initialize Symphony
    symphony = Symphony()
    
    # Create an agent
    agent_config = AgentConfig(
        name="reasoner",
        description="An agent that can perform reasoning",
        model="gpt-4-turbo"
    )
    agent_id = await symphony.agents.create_agent(agent_config)
    
    # Use a pattern for multi-step reasoning
    result = await symphony.patterns.apply_reasoning_pattern(
        "chain_of_thought",
        "If a triangle has sides of length 3, 4, and 5, what is its area?",
        config={"agent_roles": {"reasoner": agent_id}}
    )
    
    print("Reasoning steps:")
    for i, step in enumerate(result.get("steps", [])):
        print(f"Step {i+1}: {step}")
    
    print(f"Final answer: {result.get('response')}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Core Concepts

### Patterns Library

Symphony includes a comprehensive Patterns Library that encapsulates common agent interaction patterns:

#### Reasoning Patterns
- **Chain of Thought**: Step-by-step reasoning for complex problems
- **Step Back**: Take a strategic perspective before solving a problem

#### Verification Patterns
- **Critic Review**: One agent evaluates and critiques another's work
- **Self-Consistency**: Generate multiple solutions and find consensus

#### Multi-Agent Patterns
- **Expert Panel**: Gather perspectives from multiple expert agents

#### Tool Usage Patterns
- **Multi-Tool Chain**: Sequence tools together in a workflow
- **Verify-Execute**: Verify a tool usage plan before execution
- **Recursive Tool Use**: Recursively decompose problems into tool-solvable parts

#### Learning Patterns
- **Few-Shot Learning**: Use examples to guide agent behavior
- **Reflection**: Self-improve through reflection and revision
- **Iterative Reflection**: Multiple rounds of reflection and improvement

### Pattern Composition

Patterns can be composed to create more complex behaviors:

```python
# Create individual patterns
cot_pattern = symphony.patterns.create_pattern(
    "chain_of_thought",
    {"agent_roles": {"reasoner": agent_id}}
)

reflection_pattern = symphony.patterns.create_pattern(
    "reflection",
    {"agent_roles": {"performer": agent_id, "reflector": agent_id}}
)

# Compose sequentially
composed_pattern = symphony.patterns.compose_sequential(
    [cot_pattern, reflection_pattern],
    name="reason_then_reflect"
)

# Execute the composed pattern
result = await composed_pattern.run({
    "query": "Explain quantum computing"
})
```

### LiteLLM Integration

Symphony integrates with LiteLLM to provide a unified interface for over 100+ LLM providers:

- **Unified API**: Consistent interface across OpenAI, Anthropic, Azure, Cohere, and many more
- **Simple Provider Switching**: Easily switch between models with minimal code changes
- **Advanced Features**: Streaming, function calling, and async support

### Model Context Protocol (MCP)

Symphony integrates with the official Model Context Protocol (MCP) for standardized context management:

- **Resources**: Access to structured data via URI schemes
- **Tools**: Standardized function calling capabilities
- **Context Management**: Dynamic context assembly

### Agents

Agents are the primary actors in Symphony. Each agent has:
- A role or goal defined by a system prompt
- Access to tools and memory
- A specific architecture (reactive, planning, etc.)
- Optional MCP integration

### Memory Architecture

Symphony provides a sophisticated memory architecture:
- **Memory Manager**: Central coordinator for different memory systems
- **Working Memory**: Short-term storage with automatic expiration for current context
- **Long-Term Memory**: Persistent storage with semantic search capabilities
- **Importance Assessment**: Automatic evaluation of information importance
- **Memory Consolidation**: Transfer of important information from working to long-term memory
- **Conversation Memory**: Specialized memory for managing and searching conversation history

```python
# Create a memory manager
memory_manager = ConversationMemoryManager()

# Store information with different importance levels
await memory_manager.store(
    key="important_fact", 
    value="The project deadline is Friday",
    importance=0.9  # High importance - will go to long-term memory
)

# Search conversation history
results = await memory_manager.search_conversation("deadline")
```

### Tools

Tools extend agent capabilities beyond text generation, allowing them to interact with external systems, process data, or perform specific actions.

### Orchestration

Orchestrators manage the execution flow between multiple agents, supporting patterns like:
- Sequential execution
- Round-robin turns
- DAG-based workflows

## Examples

The `examples/` directory contains complete examples demonstrating different aspects of the framework:

- `simple_agent.py` - Basic reactive agent with tools
- `patterns_example.py` - Using reasoning, verification, and multi-agent patterns
- `tool_usage_patterns_example.py` - Examples of tool usage patterns
- `learning_patterns_example.py` - Examples of learning patterns
- `multi_agent.py` - Coordinating multiple agents
- `memory_manager_example.py` - Using the advanced memory architecture
- `vector_memory.py` - Semantic memory storage and retrieval
- `dag_workflow.py` - Complex workflow using a directed acyclic graph

## Testing

### Unit Tests

```bash
pytest tests/unit
```

### Integration Tests

Integration tests require API keys for the model providers you want to test with:

1. Copy `.env.example` to `.env` and add your API keys
2. Run the integration tests:

```bash
# Run all integration tests
python scripts/run_integration_tests.py

# Run tests for a specific pattern
python scripts/run_integration_tests.py --pattern chain_of_thought
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.