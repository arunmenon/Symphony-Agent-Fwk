# Symphony Components Reference

This document provides detailed information about Symphony's core components, their responsibilities, and interactions.

## Agents

Agents are the primary actors in Symphony, capable of using LLMs for decision-making and tools for actions.

### AgentBase

The abstract base class that all agents inherit from. Responsibilities:

- Managing LLM interactions
- Tool dispatching
- Memory access
- MCP context handling

```python
class AgentBase(ABC):
    def __init__(
        self,
        config: AgentConfig,
        llm_client: LLMClient,
        prompt_registry: PromptRegistry,
        memory: Optional[BaseMemory] = None,
        mcp_manager: Optional[MCPManager] = None,
    ):
        # Initialization...
    
    async def run(self, input_message: str) -> str:
        # Run the agent's decision-making loop
        
    @abstractmethod
    async def decide_action(
        self, 
        messages: List[Message], 
        mcp_context: Optional[Context] = None
    ) -> Message:
        # Decide what action to take (implemented by subclasses)
```

### ReactiveAgent

A simple agent implementation that reacts to messages directly:

- No planning or complex reasoning
- Direct LLM calls for responses
- Good for simple Q&A or chatbot scenarios

### PlannerAgent

A more sophisticated agent that plans before acting:

- Creates step-by-step plans for tasks
- Executes each step in sequence
- Can revise plans based on new information
- Good for complex tasks requiring multiple steps

## Tools

Tools extend agent capabilities beyond text generation, allowing them to perform actions in the world.

### Tool

The core tool abstraction:

- Name and description for agent discovery
- Function for executing the action
- Schema for parameter validation

```python
class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        function: Callable,
        schema: Optional[Type[BaseModel]] = None,
    ):
        self.name = name
        self.description = description
        self.function = function
        # ...
    
    def __call__(self, **kwargs: Any) -> Any:
        """Execute the tool function."""
        return self.function(**kwargs)
```

### ToolRegistry

Central registry for managing available tools:

- Tool registration via decorator
- Schema inference from function signatures
- Tool discovery by name

## Memory

Memory allows agents to store and retrieve information across interactions.

### BaseMemory

Abstract interface for all memory implementations:

```python
class BaseMemory(ABC):
    @abstractmethod
    def store(self, key: str, value: Any) -> None:
        """Store a value in memory with the given key."""
        pass
    
    @abstractmethod
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value from memory by key."""
        pass
    
    @abstractmethod
    def search(self, query: str, limit: Optional[int] = None) -> List[Any]:
        """Search memory for items matching the query."""
        pass
```

### ConversationMemory

Specialized memory for storing chat history:

- Add/retrieve conversation messages
- Manage message history length
- Convert to context items for LLM prompts

## Prompt Management

The centralized system for managing and versioning prompts.

### PromptTemplate

The basic unit of the prompt system:

```python
class PromptTemplate(BaseModel):
    """A template for a prompt."""
    
    content: str
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### PromptRegistry

Manages storage and retrieval of prompts with hierarchical overrides:

- Global prompts (default for all agents)
- Agent-type prompts (specific to agent types)
- Agent-instance prompts (specific to individual agents)

## Model Context Protocol (MCP)

Integration with the open MCP standard for context management.

### MCPManager

Manages MCP resources and tools:

```python
class MCPManager:
    """Manager for MCP resources and tools integration."""
    
    def __init__(self, config: Optional[MCPConfig] = None):
        """Initialize the MCP manager with configuration."""
        # ...
    
    def register_resource(self, resource_path: str, handler: Any) -> None:
        """Register a custom resource with MCP."""
        # ...
    
    def register_tool(self, name: Optional[str] = None, description: Optional[str] = None):
        """Register a Symphony tool as an MCP tool."""
        # ...
```

## LLM Interface

Unified API for language model access across providers.

### LLMClient

Abstract interface for all LLM clients:

```python
class LLMClient(ABC):
    """Interface for language model clients."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from a prompt string."""
        pass
    
    @abstractmethod
    async def chat(self, messages: List[Message], **kwargs: Any) -> Message:
        """Generate a response to a list of chat messages."""
        pass
    
    @abstractmethod
    async def chat_with_mcp(
        self, 
        messages: List[Message], 
        mcp_context: Context,
        **kwargs: Any
    ) -> Message:
        """Generate a response to chat messages with MCP context."""
        pass
```

### LiteLLMClient

Multi-provider implementation using LiteLLM:

- Supports 100+ LLM providers
- Consistent interface across models
- Streaming and function calling support

## Core System

Symphony's central orchestration layer.

### Container

Service locator and dependency injection container:

```python
class Container:
    """Service locator and dependency injection container."""
    
    def register(self, name: str, service: Any, singleton: bool = True) -> None:
        """Register a service instance."""
        # ...
    
    def get(self, name: str) -> Any:
        """Get a service by name."""
        # ...
```

### EventBus

Event system for component communication:

```python
class EventBus:
    """Event bus for publishing and subscribing to events."""
    
    def subscribe(
        self, 
        callback: Callable[[Event], Any], 
        event_type: Optional[Union[EventType, str]] = None
    ) -> str:
        """Subscribe to events."""
        # ...
    
    def publish(self, event: Event) -> None:
        """Publish an event (synchronously)."""
        # ...
```

### PluginManager

System for discovering and loading plugins:

```python
class PluginManager:
    """Manages plugins for Symphony."""
    
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin."""
        # ...
    
    def discover_plugins(self, package_name: str) -> None:
        """Discover plugins in a package."""
        # ...
```

## Orchestration

Coordination layer for multi-agent workflows.

### Orchestrator

Base class for all orchestrators:

```python
class Orchestrator(ABC):
    """Base class for orchestration engines."""
    
    @abstractmethod
    async def run(self, input_message: str) -> str:
        """Run the orchestration flow with an input message."""
        pass
```

### MultiAgentOrchestrator

Manages multiple agents in sequence or parallel:

- Sequential execution (one after another)
- Round-robin turns
- Output-based agent selection

### DAGOrchestrator

Executes agents and tools in a directed acyclic graph:

- Complex workflow definitions
- Conditional branching
- Parallel execution paths
- Merging of results