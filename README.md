# Symphony: A Modular AI Agent Framework

Symphony is a flexible framework for building sophisticated AI agents and multi-agent systems. It provides a comprehensive toolkit for creating, orchestrating, and managing AI agents with advanced memory capabilities and reusable interaction patterns.

- [Features](#features)
- [Installation](#installation)
- [Core Concepts](#core-concepts)
- [Getting Started](#getting-started)
- [Advanced Features](#advanced-features)
- [Integration Options](#integration-options)
- [Examples](#examples)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Modular Architecture**: Build agents from reusable, pluggable components
- **Multiple Agent Types**: Reactive agents, planning agents, and goal-driven agents
- **Advanced Memory System**: Multi-tier memory with configurable importance assessment
- **Tool Integration**: Easy extension with custom tools and capabilities
- **Patterns Library**: Reusable interaction patterns for common agent behaviors
- **Multi-Agent Orchestration**: Coordinate multiple agents working together
- **LiteLLM Integration**: Compatible with 100+ LLM providers through a unified interface
- **MCP Support**: Integration with the Model Context Protocol for standardized context management
- **Type Safety**: Built on Pydantic models for robust data validation

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

## Core Concepts

Symphony is built around several key concepts that form the foundation of the framework:

### Agents

Agents are the primary building blocks. Each agent has:

- A defined role and goal
- Access to tools and memory
- A specific architecture (reactive, planning, etc.)

Here's a simple example of creating a basic agent:

```python
import asyncio
from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.base import MockLLMClient
from symphony.prompts.registry import PromptRegistry

async def main():
    # Create a prompt registry with a system prompt
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content="You are a helpful assistant.",
        agent_type="ReactiveAgent"
    )
    
    # Create a mock LLM client (use real clients in production)
    llm_client = MockLLMClient()
    
    # Configure the agent
    agent_config = AgentConfig(
        name="SimpleAgent",
        agent_type="ReactiveAgent",
        description="A simple helpful assistant"
    )
    
    # Create the agent
    agent = ReactiveAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    # Use the agent
    response = await agent.run("Hello, how can you help me?")
    print(f"Agent: {response}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Tools

Tools extend agent capabilities beyond text generation, allowing them to interact with external systems, process data, or perform specific actions.

```python
from symphony.tools.base import tool

# Define a simple calculator tool
@tool(name="calculator", description="Perform basic arithmetic calculations")
def calculator(operation: str, a: float, b: float) -> float:
    """Perform a basic arithmetic calculation."""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")

# Add tools to an agent
agent_config = AgentConfig(
    name="CalculatorAgent",
    agent_type="ReactiveAgent",
    description="An agent that can perform calculations",
    tools=["calculator"]  # Reference the tool by name
)
```

### Model Context Protocol (MCP)

Symphony provides first-class integration with the Model Context Protocol (MCP), which offers standardized context management and a unified way for agents to access resources and tools.

**Key Benefits:**
- **Structured Context Access**: MCP provides a structured way to access resources and tools
- **Consistent API**: Standardized interface across different LLM providers
- **Dynamic Context Assembly**: Assemble resources as needed during agent execution
- **Resource URI Scheme**: Access resources with a consistent URI pattern

#### How MCP Integration Works

```
┌─────────────┐      1. Request      ┌──────────────┐ 
│    Agent    │──────────────────────▶              │ 
│             │                      │  MCP Server  │
│             │◀─────────────────────│              │
└─────────────┘    4. Response       └──────┬───────┘
                                          2.│URI Resolution
                                            ▼
┌──────────────────────┐    3. Function Call  ┌─────────────────┐
│ Application Resource │◀────────────────────▶│Resource Function│
│  Registry            │                      │  Handler        │
└──────────────────────┘                      └─────────────────┘
```

When an agent uses a resource URI like `symphony://knowledge-base/weather`:
1. The MCP server receives the request
2. Maps the URI to the registered handler function 
3. Executes the function with the extracted parameters
4. Returns the response to the agent

#### MCP Implementation Example

```python
from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.litellm_client import LiteLLMClient, LiteLLMConfig  # For production use
from symphony.mcp.base import MCPManager, MCPConfig
from mcp.server.fastmcp import Context  # Import Context from MCP
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import tool
import os

# Define a tool that will be exposed via MCP
@tool(name="web_search", description="Search the web for information")
def web_search(query: str) -> str:
    """Simulate a web search with mock results."""
    if "weather" in query.lower():
        return "It's currently sunny and 75°F."
    else:
        return f"No specific information found for: {query}"

# Define custom MCP resources
def setup_custom_mcp_resources(mcp_manager: MCPManager) -> None:
    """Set up custom MCP resources."""
    
    @mcp_manager.mcp.resource("symphony://knowledge-base/{topic}")
    def get_knowledge(topic: str, ctx: Context) -> str:
        """Example knowledge base resource."""
        knowledge = {
            "weather": "Weather is the state of the atmosphere...",
            "population": "Population refers to the number of people..."
        }
        return knowledge.get(topic, f"No information about {topic}")

# Initialize MCP Manager
mcp_config = MCPConfig(
    app_name="Symphony MCP Example",
    resource_prefix="symphony"
)
mcp_manager = MCPManager(config=mcp_config)

# Set up resources
setup_custom_mcp_resources(mcp_manager)

# Create prompt registry with MCP-aware prompts
registry = PromptRegistry()
registry.register_prompt(
    prompt_type="system",
    content=(
        "You are an MCP-enabled assistant. You can access information using URIs like:\n"
        "- symphony://knowledge-base/weather\n"
        "- symphony://knowledge-base/population\n"
        "When asked about weather or populations, use these resources."
    ),
    agent_type="MCPAgent"
)

# In examples we use MockLLMClient for simplicity and predictability
# In production, use a real LLM client:
llm_client = LiteLLMClient(
    config=LiteLLMConfig(
        model="openai/gpt-4",  # Provider/model format
        api_key=os.environ.get("OPENAI_API_KEY")
    )
)

# Create agent config with MCP enabled
agent_config = AgentConfig(
    name="MCPAgent",
    agent_type="MCPAgent", 
    description="An agent that uses MCP for context and tools",
    tools=["web_search"],
    mcp_enabled=True  # Explicitly enable MCP integration
)

# Create agent with MCP manager
agent = ReactiveAgent(
    config=agent_config,
    llm_client=llm_client,
    prompt_registry=registry,
    mcp_manager=mcp_manager
)

# Usage example
async def use_mcp_agent():
    response = await agent.run("What is the current weather?")
    print(f"Agent: {response}")
    # The agent will access symphony://knowledge-base/weather
    # and use the web_search tool
```

#### Externalized Prompt Management

Symphony's PromptRegistry provides centralized prompt management for your agent system:

```python
# Create a centralized registry for all prompts
registry = PromptRegistry()

# Register prompts by type, role and optional key
registry.register_prompt(
    prompt_type="system",
    content="You are a helpful assistant specialized in {domain}.",
    prompt_key="base_system_prompt"  # Optional key for reference
)

registry.register_prompt(
    prompt_type="user",
    content="Answer this {domain} question: {query}",
    prompt_key="domain_question"
)

# Templating with parameters
formatted_prompt = registry.get_prompt(
    "domain_question", 
    {"domain": "physics", "query": "Explain quantum entanglement"}
)

# Hierarchical overrides for specialized agent types
registry.register_prompt(
    prompt_type="system",
    content="You are a physics expert specializing in quantum mechanics.",
    agent_type="PhysicsAgent"  # Only applies to this agent type
)
```

### Memory

Symphony provides a sophisticated memory architecture with multiple tiers:

- **Working Memory**: Short-term storage with automatic expiration
- **Long-Term Memory**: Persistent storage with semantic search
- **Knowledge Graph**: Structured relationship storage

```python
from symphony.memory.memory_manager import MemoryManager, WorkingMemory
from symphony.memory.vector_memory import VectorMemory

# Create memory components
working_memory = WorkingMemory(retention_period=3600)  # 1 hour retention
long_term_memory = VectorMemory()  # Vector-based semantic search

# Create a memory manager
memory_manager = MemoryManager(
    working_memory=working_memory,
    long_term_memory=long_term_memory
)

# Store information with importance-based routing
await memory_manager.store(
    key="task_reminder", 
    value="Complete the project by Friday",
    importance=0.9  # High importance -> stored in both working and long-term
)

# Retrieve information
important_info = await memory_manager.retrieve(key="task_reminder")
```

## Getting Started

### Creating a Simple Agent

Here's a complete example of creating a simple agent with a tool:

```python
import asyncio
from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.base import MockLLMClient
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import tool

# Define a simple tool
@tool(name="weather", description="Get the current weather")
def get_weather(location: str) -> str:
    """Get the current weather for a location (simulated)."""
    return f"It's currently sunny and 75°F in {location}."

async def main():
    # Create a prompt registry
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content="You are a helpful assistant that can check the weather.",
        agent_type="ReactiveAgent"
    )
    
    # Create a mock LLM client (use real clients in production)
    llm_client = MockLLMClient(responses={
        "What's the weather in New York?": 
            "I'll check the weather for you.\nAccording to my weather tool, it's currently sunny and 75°F in New York."
    })
    
    # Configure the agent with the weather tool
    agent_config = AgentConfig(
        name="WeatherAgent",
        agent_type="ReactiveAgent",
        description="An agent that can check the weather",
        tools=["weather"]
    )
    
    # Create the agent
    agent = ReactiveAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    # Use the agent
    question = "What's the weather in New York?"
    print(f"User: {question}")
    response = await agent.run(question)
    print(f"Agent: {response}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Adding Memory to an Agent

Let's extend our agent with memory capabilities:

```python
import asyncio
from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.base import MockLLMClient
from symphony.prompts.registry import PromptRegistry
from symphony.memory.memory_manager import ConversationMemoryManager
from symphony.utils.types import Message

async def main():
    # Create a prompt registry
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content="You are a helpful assistant with memory capabilities.",
        agent_type="ReactiveAgent"
    )
    
    # Create a conversation memory manager
    memory = ConversationMemoryManager()
    
    # Create a mock LLM client
    llm_client = MockLLMClient()
    
    # Configure the agent
    agent_config = AgentConfig(
        name="MemoryAgent",
        agent_type="ReactiveAgent",
        description="An agent with memory capabilities"
    )
    
    # Create the agent with memory
    agent = ReactiveAgent(
        config=agent_config,
        llm_client=llm_client,
        prompt_registry=registry,
        memory=memory
    )
    
    # Simulate a conversation
    questions = [
        "My name is Alice.",
        "What's my name?",
        "I live in New York.",
        "Where do I live?"
    ]
    
    for question in questions:
        print(f"\nUser: {question}")
        
        # Add user message to memory
        await memory.add_message(Message(role="user", content=question))
        
        # Simplified response generation
        if "What's my name?" in question:
            response = "Your name is Alice, which you mentioned earlier."
        elif "Where do I live?" in question:
            response = "You live in New York, as you just told me."
        else:
            response = "I've made note of that information."
            
        # Add assistant's response to memory
        await memory.add_message(Message(role="assistant", content=response))
        
        print(f"Agent: {response}")
    
    # Search memory
    print("\nSearching memory for 'name'...")
    results = await memory.search_conversation("name")
    for msg in results:
        print(f"[{msg.role}]: {msg.content}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Features

### Memory Importance Assessment

Symphony's memory system can automatically assess the importance of information to determine what should be stored in long-term memory:

```python
from symphony.memory.importance import RuleBasedStrategy
from symphony.memory.memory_manager import ConversationMemoryManager

# Create a custom importance strategy
class CustomImportanceStrategy(RuleBasedStrategy):
    """Custom strategy for specialized importance assessment."""
    
    async def calculate_importance(self, content, context=None):
        # Calculate base importance using parent method
        importance = await super().calculate_importance(content, context)
        
        # Add custom logic
        if "deadline" in content.lower():
            importance += 0.3
        if "urgent" in content.lower():
            importance += 0.2
            
        # Cap at 1.0
        return min(importance, 1.0)

# Use custom strategy with memory manager
memory = ConversationMemoryManager(
    importance_strategy=CustomImportanceStrategy(),
    memory_thresholds={"long_term": 0.6, "kg": 0.8}
)
```

### Builder Pattern

Symphony provides a builder pattern for more ergonomic agent creation:

```python
from symphony.builder.agent_builder import AgentBuilder
from symphony.core.registry import ServiceRegistry

# Create a registry
registry = ServiceRegistry.get_instance()

# Build an agent with the builder pattern
agent = (AgentBuilder(registry=registry)
    .create(
        name="AdvancedAgent", 
        role="Advanced assistant", 
        instruction_template="You are a helpful advanced assistant."
    )
    .with_model("advanced-model")
    .with_capabilities(["reasoning", "planning"])
    .with_memory_importance_strategy(
        "hybrid",
        rule_weight=0.7,
        llm_weight=0.3
    )
    .with_memory_thresholds(long_term=0.6, kg=0.8)
    .with_knowledge_graph(enabled=True)
    .build())
```

### Patterns Library

Symphony's patterns library provides reusable interaction patterns that improve agent performance for common tasks. Rather than reimplementing these patterns for each application, you can leverage Symphony's pre-built collection.

#### Why Use Patterns?

- **Improved Reasoning**: Patterns like Chain-of-Thought dramatically enhance problem-solving
- **Quality Control**: Verification patterns like Self-Consistency reduce errors
- **Collaboration**: Multi-agent patterns enable expert coordination
- **Reusability**: Standardized implementations save development time
- **Composability**: Combine patterns for more sophisticated behaviors

#### Core Pattern Categories

1. **Reasoning Patterns**

   ```
   Chain-of-Thought Pattern Flow:
   ┌─────────┐    ┌─────────────┐    ┌────────────┐    ┌────────────┐
   │ Problem │───▶│ Break down  │───▶│ Step-by-   │───▶│ Synthesize │
   │ Input   │    │ into steps  │    │ step solve │    │ final ans. │
   └─────────┘    └─────────────┘    └────────────┘    └────────────┘
   ```

   ```python
   # Chain-of-Thought pattern for step-by-step reasoning
   result = await symphony.patterns.apply_reasoning_pattern(
       "chain_of_thought",
       "If a triangle has sides of length 3, 4, and 5, what is its area?",
       config={"agent_roles": {"reasoner": agent_id}}
   )
   
   # Steps are captured in the result
   for i, step in enumerate(result.get("steps", [])):
       print(f"Step {i+1}: {step}")
   
   # Step-Back pattern for taking a broader perspective
   result = await symphony.patterns.apply_reasoning_pattern(
       "step_back",
       "How could we reduce carbon emissions globally?",
       config={"agent_roles": {"reasoner": agent_id}}
   )
   ```

2. **Verification Patterns**

   ```
   Self-Consistency Pattern Flow:
   ┌─────────┐    ┌─────────────┐    ┌────────────┐    ┌────────────┐
   │ Problem │───▶│ Generate N  │───▶│ Compare    │───▶│ Select     │
   │ Input   │    │ solutions   │    │ solutions  │    │ consensus  │
   └─────────┘    └─────────────┘    └────────────┘    └────────────┘
   
   Critic Review Pattern Flow:
   ┌─────────┐    ┌─────────────┐    ┌────────────┐    ┌────────────┐
   │ Problem │───▶│ Generate    │───▶│ Critic     │───▶│ Revise     │
   │ Input   │    │ solution    │    │ evaluation │    │ solution   │
   └─────────┘    └─────────────┘    └────────────┘    └────────────┘
   ```

   ```python
   # Self-Consistency pattern generates multiple solutions and finds consensus
   result = await symphony.patterns.apply_verification_pattern(
       "self_consistency",
       "Calculate the derivative of f(x) = x³ + 2x² - 5x + 3",
       config={
           "agent_roles": {"solver": agent_id},
           "solution_count": 3
       }
   )
   
   # Critic Review pattern evaluates solutions
   result = await symphony.patterns.apply_verification_pattern(
       "critic_review",
       "Propose a marketing strategy for a new smartphone",
       config={
           "agent_roles": {
               "proposer": agent_id,
               "critic": critic_agent_id
           }
       }
   )
   ```

3. **Multi-Agent & Collaboration Patterns**

   Symphony provides several patterns for agent collaboration, enabling more complex problem-solving through coordinated multi-agent workflows:

   ```
   Expert Panel Pattern Flow:
   ┌─────────┐    ┌─────────────┐    ┌────────────────────┐    ┌──────────┐
   │ Problem │───▶│ Distribute  │───▶│ Expert responses   │───▶│ Moderator│
   │ Input   │    │ to experts  │    │ (parallel process) │    │ synthesis│
   └─────────┘    └─────────────┘    └────────────────────┘    └──────────┘
   
   Debate Pattern Flow:
   ┌─────────┐    ┌─────────────┐    ┌───────────┐    ┌───────────┐    ┌─────────┐
   │ Problem │───▶│ Initial     │───▶│ Counter-  │───▶│ Rebuttals │───▶│ Judge   │
   │ Input   │    │ positions   │    │ arguments │    │ & replies │    │ verdict │
   └─────────┘    └─────────────┘    └───────────┘    └───────────┘    └─────────┘
   ```

   ```python
   # Expert Panel pattern gathers perspectives from domain experts
   result = await symphony.patterns.apply_multi_agent_pattern(
       "expert_panel",
       "How might climate change affect agriculture?",
       config={
           "agent_roles": {
               "moderator": moderator_id,
               "experts": [climate_expert_id, agriculture_expert_id, economics_expert_id]
           },
           "rounds": 2
       }
   )
   
   # Collaborative Problem-Solving pattern with specialized agent roles
   result = await symphony.patterns.apply_multi_agent_pattern(
       "collaborative_solving",
       "Design a scalable architecture for a high-traffic e-commerce site",
       config={
           "agent_roles": {
               "coordinator": coordinator_id,
               "specialists": {
                   "database_expert": db_expert_id,
                   "frontend_expert": frontend_expert_id,
                   "security_expert": security_expert_id,
                   "devops_expert": devops_expert_id
               }
           },
           "collaboration_type": "iterative"  # Options: parallel, sequential, iterative
       }
   )
   
   # Debate pattern for analyzing controversial topics
   result = await symphony.patterns.apply_multi_agent_pattern(
       "debate",
       "Is nuclear energy a good solution for climate change?",
       config={
           "agent_roles": {
               "moderator": moderator_id,
               "pro_position": proponent_id,
               "con_position": opponent_id,
               "judge": judge_id
           },
           "debate_format": "structured",  # Options: structured, free-form
           "rounds": 3
       }
   )
   ```
   
   #### Agent Orchestration

   For complex workflows, Symphony provides advanced orchestration capabilities:

   ```python
   from symphony.orchestration.engine import OrchestrationEngine
   from symphony.orchestration.workflow_definition import WorkflowDefinition
   
   # Define a workflow with multiple agent interactions
   workflow = WorkflowDefinition(
       name="research_workflow",
       description="Research workflow with data gathering, analysis, and summary"
   )
   
   # Add steps to the workflow
   workflow.add_step(
       "data_gathering",
       agent_id=researcher_id,
       inputs={"query": "{topic}"},
       outputs=["research_data"]
   )
   
   workflow.add_step(
       "data_analysis",
       agent_id=analyst_id,
       inputs={"data": "{research_data}"},
       outputs=["analysis_results"]
   )
   
   workflow.add_step(
       "summary_generation",
       agent_id=writer_id,
       inputs={"analysis": "{analysis_results}", "audience": "{audience_type}"},
       outputs=["final_summary"]
   )
   
   # Create execution engine
   engine = OrchestrationEngine()
   
   # Execute workflow with specific inputs
   result = await engine.execute_workflow(
       workflow,
       {
           "topic": "Renewable energy developments in 2025",
           "audience_type": "technical"
       }
   )
   
   print(f"Final summary: {result['final_summary']}")
   ```

#### Pattern Composition

Patterns can be composed to create more sophisticated behaviors:

```
Pattern Composition Flow:
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│            │     │            │     │            │     │            │
│ Chain of   │────▶│ Reflection │────▶│   Self-    │────▶│ Integrated │
│ Thought    │     │ Pattern    │     │ Consistency│     │   Result   │
│            │     │            │     │            │     │            │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
```

```python
import asyncio
from symphony.api import Symphony
from symphony.core.agent_config import AgentConfig

async def main():
    # Initialize Symphony
    symphony = Symphony()
    
    # Create an agent
    agent_config = AgentConfig(
        name="reasoner",
        description="An agent that can perform reasoning",
        model="advanced-model"
    )
    agent_id = await symphony.agents.create_agent(agent_config)
    
    # Create individual patterns
    cot_pattern = symphony.patterns.create_pattern(
        "chain_of_thought",
        {"agent_roles": {"reasoner": agent_id}}
    )
    
    reflection_pattern = symphony.patterns.create_pattern(
        "reflection",
        {"agent_roles": {"performer": agent_id, "reflector": agent_id}}
    )
    
    verification_pattern = symphony.patterns.create_pattern(
        "self_consistency",
        {"agent_roles": {"solver": agent_id}, "solution_count": 3}
    )
    
    # Compose sequentially for a comprehensive reasoning workflow
    composed_pattern = symphony.patterns.compose_sequential(
        [cot_pattern, reflection_pattern, verification_pattern],
        name="reason_reflect_verify"
    )
    
    # Execute the composed pattern
    result = await composed_pattern.run({
        "query": "Explain quantum computing and its applications"
    })
    
    # The result contains all steps from each pattern
    print(f"Final result: {result.get('final_response')}")
    print(f"Certainty score: {result.get('certainty_score')}")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Pattern Implementation Details

Patterns are implemented as reusable templates with configurable components:

1. **Pattern Definition**: Each pattern is defined in YAML templates that specify the interaction flow
2. **Dynamic Prompting**: Templates include specialized prompts for each agent role
3. **Execution Logic**: Pattern-specific logic handles the flow between components
4. **Result Processing**: Results are processed and formatted in a consistent way

For example, the Chain-of-Thought pattern template uses a structure like:

```yaml
name: chain_of_thought
description: Step-by-step reasoning for complex problems
version: 1.0
prompts:
  system:
    reasoner: |
      You are an expert at solving complex problems through step-by-step reasoning.
      Break down the problem, solve each step, and provide a final answer.
  
  user:
    reasoner: |
      Problem: {query}
      
      Solve this step-by-step:
      1. Break the problem into parts
      2. Solve each part carefully
      3. Combine the results
      4. Provide your final answer
```

The framework handles the execution logic, making it easy to use patterns without reimplementing the underlying mechanics.

## Integration Options

### LiteLLM Integration

Symphony integrates with LiteLLM for unified access to 100+ LLM providers:

```python
from symphony.llm.litellm_client import LiteLLMClient, LiteLLMConfig

# Configure LiteLLM
llm_config = LiteLLMConfig(
    model="openai/gpt-4",  # Provider/model format
    api_key="your-api-key",
    temperature=0.7
)

# Create LLM client
llm_client = LiteLLMClient(config=llm_config)

# Create agent with LLM client
agent = ReactiveAgent(
    config=agent_config,
    llm_client=llm_client,
    prompt_registry=registry
)
```

### Model Context Protocol (MCP) Integration

Symphony integrates with the Model Context Protocol for standardized context management:

```python
from symphony.mcp.base import MCPManager, MCPConfig
from mcp.server.fastmcp import Context

# Initialize MCP Manager
mcp_config = MCPConfig(
    app_name="Symphony MCP Example",
    resource_prefix="symphony"
)
mcp_manager = MCPManager(config=mcp_config)

# Define custom MCP resources
@mcp_manager.mcp.resource("symphony://knowledge-base/{topic}")
def get_knowledge(topic: str, ctx: Context) -> str:
    """Example knowledge base resource."""
    knowledge = {
        "weather": "Weather is the state of the atmosphere...",
        "population": "Population refers to the number of people..."
    }
    return knowledge.get(topic, f"No information about {topic}")

# Create agent with MCP
agent_config = AgentConfig(
    name="MCPAgent",
    agent_type="MCPAgent",
    description="An agent that uses MCP",
    tools=["web_search"],
    mcp_enabled=True
)

agent = ReactiveAgent(
    config=agent_config,
    llm_client=llm_client,
    prompt_registry=registry,
    mcp_manager=mcp_manager
)
```

## Examples

The `examples/` directory contains complete examples demonstrating different aspects of the framework:

### Foundational Examples
- `simple_agent.py` - Creating a basic reactive agent with tools
- `memory_manager_example.py` - Using the advanced memory architecture
- `tool_usage_example.py` - Defining and using custom tools

### Memory Examples
- `importance_assessment_example.py` - Configurable importance evaluation approaches
- `strategic_memory_example.py` - Demonstrates importance-based memory strategies
- `configurable_memory_agent_example.py` - Building agents with customized memory
- `vector_memory.py` - Semantic memory storage and retrieval
- `knowledge_graph_memory.py` - Graph-based memory for relationship storage

### Pattern Examples
- `patterns_example.py` - Using reasoning, verification, and multi-agent patterns
- `chain_of_thought_example.py` - Step-by-step reasoning pattern
- `reflection_example.py` - Self-improvement through reflection
- `tool_usage_patterns_example.py` - Examples of tool usage patterns

### Multi-Agent Examples
- `multi_agent.py` - Coordinating multiple agents
- `orchestration_example.py` - Orchestrating multiple agents
- `expert_panel_example.py` - Using an expert panel pattern
- `dag_workflow.py` - Complex workflow using a directed acyclic graph

### Integration Examples
- `mcp_integration.py` - Model Context Protocol integration
- `litellm_integration.py` - Multi-provider LLM support
- `symphony_api_example.py` - Using the high-level Symphony API

### Advanced Examples
- `planning_agent.py` - Planning-based agent with goal decomposition
- `comprehensive_tutorial.py` - End-to-end tutorial
- `persistence_example.py` - Data persistence across sessions

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