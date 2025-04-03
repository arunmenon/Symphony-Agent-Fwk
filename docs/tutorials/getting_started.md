# Getting Started with Symphony

This tutorial will guide you through setting up your first Symphony application, creating agents, and orchestrating them to solve problems.

## Installation

First, install Symphony from GitHub:

```bash
# Clone the repository
git clone https://github.com/arunmenon/Symphony-Agent-Fwk.git
cd Symphony-Agent-Fwk

# Install in development mode
pip install -e .

# Install optional dependencies
pip install -e ".[dev,openai,anthropic,cli]"
```

## Basic Concepts

Before diving into code, let's understand Symphony's key concepts:

- **Agents**: Intelligent entities that use language models for decision-making
- **Tools**: Functions that agents can call to perform actions
- **Memory**: Storage for conversation history and other data
- **Prompts**: Templates for instructing agents
- **Orchestration**: Coordination of multiple agents

## Your First Agent

Let's create a simple question-answering agent:

```python
import asyncio
from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.litellm_client import LiteLLMClient, LiteLLMConfig
from symphony.prompts.registry import PromptRegistry

# 1. Set up a prompt registry
registry = PromptRegistry()
registry.register_prompt(
    prompt_type="system",
    content="You are a helpful assistant. Answer questions concisely and accurately.",
    agent_type="BasicAssistant"
)

# 2. Configure LLM client (using OpenAI in this example)
llm_config = LiteLLMConfig(
    model="openai/gpt-3.5-turbo",
    max_tokens=500,
    temperature=0.7,
    # Set your API key here or use environment variable
    api_key="your-api-key"  # Or use: os.environ.get("OPENAI_API_KEY")
)
llm_client = LiteLLMClient(config=llm_config)

# 3. Create agent configuration
agent_config = AgentConfig(
    name="MyAssistant",
    agent_type="BasicAssistant",
    description="A simple question-answering assistant"
)

# 4. Create and run the agent
agent = ReactiveAgent(
    config=agent_config,
    llm_client=llm_client,
    prompt_registry=registry
)

async def main():
    # Run the agent with a question
    response = await agent.run("What is machine learning?")
    print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Adding Tools

Let's enhance our agent with a calculator tool:

```python
from symphony.tools.base import tool

# 1. Define a calculator tool
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

# 2. Update agent config to include the tool
agent_config = AgentConfig(
    name="CalculatorAssistant",
    agent_type="BasicAssistant",
    description="An assistant that can perform calculations",
    tools=["calculator"]  # Add the calculator tool
)

# 3. Update prompt to mention calculator capability
registry.register_prompt(
    prompt_type="system",
    content="""You are a helpful assistant with calculation abilities.
When asked to perform arithmetic, use the calculator tool.
Show your work when solving problems.""",
    agent_type="BasicAssistant"
)

# 4. Create and run the agent with the tool
# (rest of the code remains the same)
```

## Using Memory

Let's add conversation memory to make our agent remember previous interactions:

```python
from symphony.memory.base import ConversationMemory

# 1. Create a conversation memory instance
memory = ConversationMemory()

# 2. Pass memory to the agent
agent = ReactiveAgent(
    config=agent_config,
    llm_client=llm_client,
    prompt_registry=registry,
    memory=memory  # Add memory
)

async def main():
    # Have a multi-turn conversation
    responses = []
    
    questions = [
        "What is 25 + 17?",
        "Can you multiply that result by 2?",
        "What was the original question I asked?"
    ]
    
    for question in questions:
        print(f"\nQuestion: {question}")
        response = await agent.run(question)
        print(f"Response: {response}")
        responses.append(response)

if __name__ == "__main__":
    asyncio.run(main())
```

## Orchestrating Multiple Agents

Now, let's create a multi-agent system with a researcher and a writer:

```python
from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.orchestration.base import MultiAgentOrchestrator, OrchestratorConfig, TurnType

# 1. Create configurations for both agents
researcher_config = AgentConfig(
    name="Researcher",
    agent_type="ResearchAgent",
    description="An agent that researches information",
    tools=["web_search"]  # Assuming we've defined a web_search tool
)

writer_config = AgentConfig(
    name="Writer",
    agent_type="WriterAgent",
    description="An agent that writes content based on research",
    tools=["summarize"]  # Assuming we've defined a summarize tool
)

# 2. Set up prompts for each agent type
registry.register_prompt(
    prompt_type="system",
    content="You are a Research Agent. Find detailed information on topics.",
    agent_type="ResearchAgent"
)

registry.register_prompt(
    prompt_type="system",
    content="You are a Writer Agent. Create well-written content based on research.",
    agent_type="WriterAgent"
)

# 3. Create an orchestrator configuration
orchestrator_config = OrchestratorConfig(
    agent_configs=[researcher_config, writer_config],
    max_steps=5
)

# 4. Create a multi-agent orchestrator
orchestrator = MultiAgentOrchestrator(
    config=orchestrator_config,
    llm_client=llm_client,
    prompt_registry=registry,
    turn_type=TurnType.SEQUENTIAL  # First Researcher, then Writer
)

async def main():
    # Run the multi-agent system with a topic
    topic = "The impact of artificial intelligence on healthcare"
    print(f"\nTopic: {topic}")
    
    final_result = await orchestrator.run(topic)
    print(f"\nFinal Result: {final_result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Using Model Context Protocol (MCP)

Symphony integrates with the Model Context Protocol. Here's how to use it:

```python
from symphony.mcp.base import MCPManager, MCPConfig

# 1. Create an MCP manager
mcp_config = MCPConfig(app_name="My Symphony App")
mcp_manager = MCPManager(config=mcp_config)

# 2. Register a custom resource
@mcp_manager.mcp.resource("knowledge://healthcare/{topic}")
def get_healthcare_knowledge(topic: str, ctx: Context) -> str:
    """Get knowledge about healthcare topics."""
    knowledge = {
        "diagnostics": "AI is revolutionizing diagnostics through image analysis...",
        "treatment": "Personalized treatment plans are being developed using AI...",
        "research": "Drug discovery is accelerated by AI models that can predict..."
    }
    return knowledge.get(topic, f"No information available about {topic}")

# 3. Create agent with MCP enabled
agent_config = AgentConfig(
    name="HealthcareExpert",
    agent_type="ExpertAgent",
    description="An expert on healthcare and AI",
    tools=["calculator"],
    mcp_enabled=True  # Enable MCP integration
)

agent = ReactiveAgent(
    config=agent_config,
    llm_client=llm_client,
    prompt_registry=registry,
    mcp_manager=mcp_manager  # Add MCP manager
)
```

## Advanced Architecture with Design Patterns

For more complex applications, Symphony provides advanced design patterns:

```python
from symphony.core import (
    Symphony,
    SymphonyConfig,
    AgentFactory,
    LLMClientFactory,
    MemoryFactory
)

# 1. Create a Symphony configuration
config = SymphonyConfig(
    application_name="Advanced Symphony App",
    llm_provider="openai",
    llm_model="gpt-4"
)

# 2. Create a Symphony instance
symphony = Symphony(config)
container = symphony.get_container()
event_bus = symphony.get_event_bus()

# 3. Use factories to create components
llm_client = LLMClientFactory.create_from_provider(
    provider="openai",
    model_name="gpt-4"
)
container.register("llm_client", llm_client)

memory = MemoryFactory.create("conversation")
container.register("memory", memory)

# 4. Register an event listener
def log_message(event):
    if event.type == "message:sent":
        print(f"Message sent: {event.data.get('content', '')[:30]}...")

event_bus.subscribe(log_message, event_type="message:sent")

# 5. Create an agent using the factory
agent_config = AgentConfig(
    name="AdvancedAgent",
    agent_type="reactive",
    tools=["calculator"]
)

agent = AgentFactory.create(
    config=agent_config,
    llm_client=llm_client,
    prompt_registry=registry,
    memory=memory
)
```

## Next Steps

Now that you've learned the basics, try:

1. Creating a complex DAG workflow with conditional branches
2. Implementing a custom memory backend
3. Building a planning agent that breaks tasks into steps
4. Creating a custom plugin for Symphony

Refer to the [Architecture Documentation](../architecture/overview.md) and [API Reference](../api/index.md) for more detailed information.