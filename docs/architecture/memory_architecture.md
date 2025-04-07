# Memory Architecture

Symphony provides a sophisticated memory architecture that allows agents to store, retrieve, and search information efficiently. The memory system is designed to mimic human memory characteristics, with distinct memory types and automatic importance assessment.

## Memory Manager

The `MemoryManager` is the central component that coordinates different memory systems:

```python
from symphony.memory.memory_manager import MemoryManager

# Create a memory manager
memory_manager = MemoryManager()

# Store information 
await memory_manager.store(
    key="task_reminder", 
    value="Remember to complete the project by Friday",
    importance=0.9  # High importance
)

# Retrieve information
important_info = await memory_manager.retrieve(key="task_reminder")
```

The memory manager automatically decides where to store information based on its importance:
- Low importance information is stored only in working memory
- High importance information is stored in both working and long-term memory

## Memory Types

### Working Memory

Working memory is designed for short-term storage of information that is currently relevant:

- Automatically expires items after a configurable retention period
- Fast access for current context
- Limited capacity, but fast and efficient
- Primarily used for immediate context and information

```python
from symphony.memory.memory_manager import WorkingMemory

# Create working memory with 1 hour retention period
working_memory = WorkingMemory(retention_period=3600)

# Store information
await working_memory.store("key", "value")

# Retrieve information
result = await working_memory.retrieve("key")

# Clean up expired items
await working_memory.cleanup()
```

### Long-Term Memory

Long-term memory provides persistent storage with semantic search capabilities:

- Vector-based storage for semantic similarity search
- Persistent across sessions (optional)
- Used for important information that needs to be remembered
- Support for metadata and complex queries

```python
from symphony.memory.vector_memory import VectorMemory

# Create long-term memory
long_term_memory = VectorMemory()

# Store information
await long_term_memory.store("key", "value")

# Search by semantic similarity
results = long_term_memory.search("similar concept", limit=5)
```

## Conversation Memory

The `ConversationMemoryManager` extends the memory manager with specialized capabilities for managing conversation history:

```python
from symphony.memory.memory_manager import ConversationMemoryManager
from symphony.utils.types import Message

# Create a conversation memory manager
conversation_memory = ConversationMemoryManager()

# Add messages to the conversation
await conversation_memory.add_message(Message(
    role="user",
    content="What are the key benefits of using a memory manager?"
))

await conversation_memory.add_message(Message(
    role="assistant",
    content="The key benefits include centralized control, automatic prioritization, and efficient retrieval."
))

# Search the conversation history
results = await conversation_memory.search_conversation("benefits", limit=1)
```

The conversation memory manager automatically:
- Tracks the full conversation history
- Calculates importance of messages based on content
- Enables semantic search through conversation history
- Consolidates important messages to long-term memory

## Importance Assessment

The memory manager automatically assesses the importance of information based on content and context:

```python
# This message contains a question and will be rated as important
await conversation_memory.add_message(Message(
    role="user",
    content="When is the deadline for the project?"
))

# This message contains action keywords and will be rated as important
await conversation_memory.add_message(Message(
    role="user",
    content="We must complete the prototype by Friday."
))
```

Basic heuristics for importance assessment include:
- Questions (messages containing "?")
- Action items (containing keywords like "must", "should", "need to")
- User messages (versus system or assistant messages)

This mechanism can be extended with more sophisticated approaches like:
- Semantic relevance to core objectives
- Recency-weighted importance
- User explicit marking of importance

## Memory Consolidation

Memory consolidation is the process of transferring important information from working to long-term memory:

```python
# Consolidate memory (transfer important items, clean up expired items)
await memory_manager.consolidate()
```

The consolidation process:
1. Identifies important items in working memory
2. Transfers them to long-term memory if not already present
3. Removes expired items from working memory

This mimics human memory consolidation during rest periods and ensures that important information is preserved while ephemeral details are forgotten.

## Evolution Path

The memory architecture is designed to evolve over time with additional capabilities:

1. **Episodic Memory**: For storing and retrieving experiences and sequences of events
2. **Semantic Network**: For representing relationships between concepts
3. **Procedural Memory**: For storing sequences of actions or skills
4. **Attention Mechanisms**: For more sophisticated focus on relevant information
5. **Memory Compression**: For efficient storage of large amounts of information

The modular design allows these extensions to be added without disrupting existing functionality.

## Integration with Agents

Agents can use the memory manager to maintain context and recall important information:

```python
from symphony.agents.base import ReactiveAgent
from symphony.memory.memory_manager import ConversationMemoryManager

class MemoryEnhancedAgent(ReactiveAgent):
    """Agent with enhanced memory capabilities."""
    
    def __init__(self, config, llm_client, prompt_registry, memory=None):
        # Create memory manager if none provided
        if memory is None:
            memory = ConversationMemoryManager()
            
        super().__init__(config, llm_client, prompt_registry, memory)
    
    async def run(self, input_message: str) -> str:
        # Check if the message is a search query
        if input_message.startswith("search:"):
            query = input_message[7:].strip()
            return await self._search_memory(query)
            
        # Process normally and add to memory
        return await super().run(input_message)
    
    async def _search_memory(self, query: str) -> str:
        """Search memory for relevant information."""
        if isinstance(self.memory, ConversationMemoryManager):
            results = await self.memory.search_conversation(query, limit=5)
            # Format and return results
```

## Examples

For complete examples of using the memory architecture, see:
- `examples/memory_manager_example.py` - Using the memory manager
- `examples/vector_memory.py` - Using vector memory for semantic search