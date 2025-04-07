# Symphony: Next-Generation Agentic Framework

Symphony is an advanced, modular framework for building complex AI agent systems. It provides a unified approach to creating, orchestrating, and managing multiple AI agents, with powerful integration with the Model Context Protocol (MCP) for standardized context management and LiteLLM for multi-provider LLM support.

## Key Features

- **Multiple Agent Architectures**: Support for reactive agents, planning agents, and DAG-based workflows.
- **Multi-Agent Orchestration**: Coordinate multiple agents working together to solve complex tasks.
- **Patterns Library**: Reusable interaction patterns like chain-of-thought, reflection, and multi-agent collaboration.
- **MCP Integration**: First-class support for the Model Context Protocol, providing standardized context management.
- **LiteLLM Integration**: Seamless integration with over 100+ LLM providers through a unified interface.
- **Advanced Memory Architecture**: Multi-tier memory system with configurable importance assessment, custom storage policies, and automatic memory consolidation.
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
        model="advanced-model"  # Use a model with strong reasoning capabilities
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

Symphony provides a sophisticated memory architecture with domain awareness:

#### Multi-Tier Memory System
- **Memory Manager**: Central coordinator for different memory systems
- **Working Memory**: Short-term storage with automatic expiration for current context
- **Long-Term Memory**: Persistent storage with semantic search capabilities
- **Knowledge Graph Memory**: Structured relationship storage for complex knowledge

#### Configurable Importance Assessment
- **Strategy Pattern**: Pluggable importance assessment strategies for flexible memory handling
- **Customizable Rules**: Define what information matters for your specific use case
- **Rule-Based Assessment**: Keyword and pattern matching for fast evaluation
- **LLM-Based Assessment**: Semantic understanding of information importance
- **Hybrid Strategies**: Combine rule-based approaches with AI-based assessment

#### Memory Operations
- **Importance Assessment**: Automatic evaluation of information importance
- **Memory Consolidation**: Transfer of important information from working to long-term memory
- **Conversation Memory**: Specialized memory for managing and searching conversation history
- **Memory Factory**: Simplified creation of memory systems with domain strategies

```python
# Basic usage with default importance assessment
memory_manager = ConversationMemoryManager()

# Custom memory with configurable importance assessment
from symphony.memory.strategy_factory import ImportanceStrategyFactory

# Create memory with rule-based importance strategy
memory = MemoryFactory.create_conversation_manager(
    importance_strategy_type="rule",
    strategy_params={
        "action_keywords": ["important", "critical", "remember"],
        "question_bonus": 0.3,
        "action_bonus": 0.4
    },
    memory_thresholds={"long_term": 0.6, "kg": 0.8}
)

# Add messages to memory (importance calculated automatically)
await memory.add_message(Message(
    role="user",
    content="Please remember this important information for later."
))

# Search conversation using semantic memory
results = await memory.search_conversation("important information")
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

### Agent Examples
- `simple_agent.py` - Basic reactive agent with tools
- `planning_agent.py` - Planning-based agent with goal decomposition

### Pattern Examples
- `patterns_example.py` - Using reasoning, verification, and multi-agent patterns
- `tool_usage_patterns_example.py` - Examples of tool usage patterns
- `learning_patterns_example.py` - Examples of learning patterns

### Multi-Agent Examples
- `multi_agent.py` - Coordinating multiple agents
- `dag_workflow.py` - Complex workflow using a directed acyclic graph

### Memory Examples
- `memory_manager_example.py` - Using the advanced memory architecture
- `strategic_memory_example.py` - Demonstrates importance-based memory strategies
- `memory_factory_example.py` - Factory patterns for memory system creation
- `importance_assessment_example.py` - Customizable importance evaluation approaches
- `vector_memory.py` - Semantic memory storage and retrieval
- `knowledge_graph_memory.py` - Graph-based memory for relationship storage
- `local_kg_memory.py` - Local knowledge graph without external dependencies

### Integration Examples
- `mcp_integration.py` - Model Context Protocol integration
- `litellm_integration.py` - Multi-provider LLM support
- `symphony_api_example.py` - Using the high-level Symphony API

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