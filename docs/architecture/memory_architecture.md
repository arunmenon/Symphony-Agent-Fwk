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

## Importance Assessment Strategies

Symphony uses a strategy pattern for importance assessment, allowing you to customize how the system determines what information is important:

```python
from symphony.memory.importance import RuleBasedStrategy, LLMBasedStrategy, HybridStrategy
from symphony.memory.domain_strategies import CustomerSupportStrategy
from symphony.memory.strategy_factory import ImportanceStrategyFactory

# 1. Rule-based strategy (default)
rule_strategy = RuleBasedStrategy(
    action_keywords=["urgent", "critical", "important", "deadline", "must"],
    question_bonus=0.2,
    action_bonus=0.3,
    user_bonus=0.1
)

# 2. LLM-based strategy (uses AI to assess importance)
llm_strategy = LLMBasedStrategy(
    llm_client=llm_client,
    prompt_registry=prompt_registry,
    prompt_key="memory.importance_assessment"
)

# 3. Hybrid strategy (combines both approaches)
hybrid_strategy = HybridStrategy([
    (rule_strategy, 0.3),  # 30% weight for rule-based
    (llm_strategy, 0.7)    # 70% weight for LLM-based
])

# 4. Domain-specific strategy (optimized for a particular use case)
customer_support_strategy = CustomerSupportStrategy()

# 5. Create using factory (recommended approach)
product_research_strategy = ImportanceStrategyFactory.create_strategy(
    "product_research",
    product_categories=["smartphone", "wearable", "laptop"],
    feature_terms=["performance", "battery", "usability"]
)

# Create memory manager with your chosen strategy
memory_manager = ConversationMemoryManager(
    importance_strategy=hybrid_strategy,
    memory_thresholds={"long_term": 0.7, "kg": 0.8}
)

# Add messages (importance calculated automatically)
await memory_manager.add_message(Message(
    role="user",
    content="When is the deadline for the project?"
))
```

Each strategy has different advantages:

### Rule-Based Strategy

Basic heuristics include:
- Questions (messages containing "?")
- Action items (containing keywords like "must", "should", "need to")
- User messages (versus system or assistant messages)

```python
# Configure with custom keywords and bonuses
rule_strategy = RuleBasedStrategy(
    action_keywords=["priority", "deadline", "urgent", "important", "critical"],
    question_bonus=0.3,  # Higher bonus for questions
    action_bonus=0.4,    # Higher bonus for action items
    user_bonus=0.1       # Bonus for user messages
)
```

### LLM-Based Strategy

Uses an LLM to evaluate the semantic importance of content:

```python
# The prompt template guides importance assessment
prompt = """
Evaluate the importance of this information on a scale of 0-10:
Content: {content}
Agent role: {agent_role}
Current task: {current_task}

Rate importance (0-10):
"""

llm_strategy = LLMBasedStrategy(
    llm_client=llm_client,
    default_prompt=prompt
)
```

### Hybrid Strategy

Combines multiple strategies with weighted importance:

```python
# Create a hybrid strategy with multiple components
hybrid_strategy = HybridStrategy([
    (rule_strategy, 0.4),             # 40% rule-based
    (llm_strategy, 0.6),              # 60% LLM-based
    (custom_strategy, 0.0)            # 0% weight (disabled but ready to enable)
])
```

You can also set custom thresholds for different memory tiers:

```python
memory_manager = ConversationMemoryManager(
    importance_strategy=hybrid_strategy,
    memory_thresholds={
        "long_term": 0.6,  # Lower threshold - store more in long-term
        "kg": 0.8          # Higher threshold - only store very important in KG
    }
)
```

### Domain-Specific Strategies

Symphony provides specialized importance strategies optimized for different domains:

#### Available Domain Strategies

1. **Customer Support Strategy**
   - Optimized for customer service scenarios
   - Enhanced detection of order IDs, refund requests, and customer sentiment
   - Higher importance for urgent issues and reported problems

2. **Product Research Strategy**
   - Specialized for product development and research teams
   - Recognizes metrics, feature discussions, and competitive analysis
   - Higher importance for user feedback and decision-making content

3. **Personal Assistant Strategy**
   - Tailored for personal productivity and scheduling
   - Enhanced detection of dates, times, and contact names
   - Higher importance for appointments, tasks, and personal information

4. **Educational Strategy**
   - Optimized for learning and teaching contexts
   - Recognizes definitions, examples, principles, and assessment information
   - Adjusts based on learning level (beginner, intermediate, advanced)

5. **Medical Assistant Strategy**
   - Specialized for healthcare and patient information
   - Highest importance for emergency information and medication instructions
   - Enhanced detection of symptoms, severity terms, and medical history

#### Using Domain Strategies

The recommended way to use domain strategies is through the strategy factory:

```python
from symphony.memory.strategy_factory import ImportanceStrategyFactory

# Create a customer support strategy
customer_strategy = ImportanceStrategyFactory.create_strategy(
    "customer_support",
    action_keywords=["order", "refund", "warranty", "shipping", "damaged"],
    base_importance=0.5
)

# Create a medical strategy with domain-specific terms
medical_strategy = ImportanceStrategyFactory.create_strategy(
    "medical",
    medical_terms=["diabetes", "hypertension", "asthma"],
    severity_terms=["severe", "critical", "emergency"],
    base_importance=0.6  # Higher base importance for medical context
)

# Create a hybrid domain strategy (domain rules + LLM assessment)
educational_hybrid = ImportanceStrategyFactory.create_strategy(
    "hybrid_educational",
    llm_client=llm_client,
    subjects=["physics", "mathematics"],
    learning_level="advanced",
    domain_weight=0.7,
    llm_weight=0.3
)
```

#### Using with Builder Pattern

Domain strategies integrate seamlessly with the agent builder:

```python
from symphony.builder.agent_builder import AgentBuilder

# Create an educational agent with specialized memory
agent = (AgentBuilder(registry=registry)
    .create(
        name="PhysicsTeacherAgent", 
        role="Physics instructor", 
        instruction_template="You are an expert physics teacher."
    )
    .with_model("gpt-4")
    .with_capabilities(["physics", "education"])
    # Use domain-specific strategy
    .with_memory_importance_strategy(
        "educational",
        subjects=["physics", "mathematics"],
        learning_level="advanced"
    )
    # Or use hybrid domain strategy
    .with_memory_importance_strategy(
        "hybrid_educational",
        llm_client=llm_client,
        subjects=["physics", "mathematics"],
        learning_level="advanced",
        domain_weight=0.7,
        llm_weight=0.3
    )
    .with_memory_thresholds(long_term=0.5, kg=0.7)
    .with_knowledge_graph(enabled=True)
    .build())
```

#### Creating Custom Domain Strategies

You can create your own domain strategies by extending the base classes:

```python
from symphony.memory.importance import RuleBasedStrategy

class E-commerceStrategy(RuleBasedStrategy):
    """Specialized importance strategy for e-commerce and retail."""
    
    def __init__(
        self,
        action_keywords: Optional[List[str]] = None,
        question_bonus: float = 0.2,
        action_bonus: float = 0.3,
        user_bonus: float = 0.1,
        base_importance: float = 0.5,
        product_categories: Optional[List[str]] = None
    ):
        """Initialize with e-commerce specific parameters."""
        # Define e-commerce specific keywords if not provided
        if action_keywords is None:
            action_keywords = [
                "purchase", "buy", "order", "cart", "checkout",
                "payment", "shipping", "delivery", "discount", "sale"
            ]
            
        super().__init__(
            action_keywords=action_keywords,
            question_bonus=question_bonus,
            action_bonus=action_bonus,
            user_bonus=user_bonus,
            base_importance=base_importance
        )
        
        # E-commerce specific parameters
        self.product_categories = product_categories or []
    
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance with e-commerce-specific logic."""
        importance = await super().calculate_importance(content, context)
        content_lower = content.lower()
        
        # Increase importance for purchase intent
        purchase_indicators = ["want to buy", "looking for", "interested in", "purchase"]
        if any(indicator in content_lower for indicator in purchase_indicators):
            importance += 0.2
            
        # Add more domain-specific logic...
        
        # Cap at 1.0
        return min(importance, 1.0)
```

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

### Using Builder Pattern

The recommended way to configure agent memory is using the builder pattern:

```python
from symphony.builder.agent_builder import AgentBuilder
from symphony.core.registry import ServiceRegistry

# Create an agent with configured memory
agent = (AgentBuilder(registry=ServiceRegistry.get_instance())
    .create("MemoryAgent", "Expert assistant", "You are a helpful assistant with memory.")
    .with_model("gpt-4")
    .with_memory_type("conversation")
    # Configure memory importance strategy
    .with_memory_importance_strategy("hybrid", 
        strategies=[
            (RuleBasedStrategy(), 0.4),
            (LLMBasedStrategy(llm_client=llm_client), 0.6)
        ]
    )
    # Set custom thresholds
    .with_memory_thresholds(long_term=0.6, kg=0.8)
    # Enable knowledge graph memory
    .with_knowledge_graph(enabled=True)
    .build())
```

### Using Facade Pattern

For high-level operations, use the agent facade:

```python
from symphony.facade.agents import AgentFacade

# Create agent facade
agent_facade = AgentFacade()

# Configure memory for an existing agent
await agent_facade.configure_agent_memory(
    agent_id="agent-123",
    memory_type="conversation",
    importance_strategy="llm",
    use_knowledge_graph=True,
    memory_thresholds={"long_term": 0.6, "kg": 0.8},
    strategy_params={"llm_client": llm_client}
)

# Store information in agent's memory
await agent_facade.store_in_agent_memory(
    agent_id="agent-123", 
    key="project_deadline", 
    value="Friday at 5pm",
    importance=0.9
)

# Retrieve from agent's memory
deadline = await agent_facade.retrieve_from_agent_memory(
    agent_id="agent-123",
    key="project_deadline"
)

# Search agent's conversation history
results = await agent_facade.search_agent_conversation(
    agent_id="agent-123",
    query="deadline",
    limit=5
)
```

### Custom Agent Implementation

For direct integration, extend an agent with memory capabilities:

```python
from symphony.agents.base import ReactiveAgent
from symphony.memory.memory_manager import ConversationMemoryManager
from symphony.memory.importance import RuleBasedStrategy

class MemoryEnhancedAgent(ReactiveAgent):
    """Agent with enhanced memory capabilities."""
    
    def __init__(self, config, llm_client, prompt_registry, memory=None):
        # Create customized memory manager if none provided
        if memory is None:
            strategy = RuleBasedStrategy(
                action_keywords=["critical", "important", "deadline", "priority"],
                question_bonus=0.3
            )
            memory = ConversationMemoryManager(
                importance_strategy=strategy,
                memory_thresholds={"long_term": 0.6}
            )
            
        super().__init__(config, llm_client, prompt_registry, memory)
    
    async def run(self, input_message: str) -> str:
        # Check if the message is a search query
        if input_message.startswith("search:"):
            query = input_message[7:].strip()
            return await self._search_memory(query)
            
        # Store user message with context about current task
        user_message = Message(role="user", content=input_message)
        context = {
            "role": "user",
            "current_task": self.current_task,
            "agent_role": self.config.role
        }
        await self.memory.add_message(user_message, context=context)
        
        # Process normally
        response = await super().run(input_message)
        
        # Store agent's response
        assistant_message = Message(role="assistant", content=response)
        await self.memory.add_message(assistant_message)
        
        return response
    
    async def _search_memory(self, query: str) -> str:
        """Search memory for relevant information."""
        results = await self.memory.search_conversation(query, limit=5)
        
        # Format results in a user-friendly way
        formatted_results = ["Here's what I found in my memory:"]
        for i, message in enumerate(results, 1):
            formatted_results.append(f"\n{i}. [{message.role}]: {message.content[:100]}...")
        
        return "\n".join(formatted_results)
```

## Examples

For complete examples of using the memory architecture, see:

- `examples/memory_manager_example.py` - Basic memory manager usage
- `examples/strategic_memory_example.py` - Using importance assessment strategies
- `examples/vector_memory.py` - Vector-based semantic search
- `examples/knowledge_graph_memory.py` - Knowledge graph memory
- `examples/local_kg_memory.py` - Local knowledge graph implementation

## End-to-End Example: Intelligent Customer Support Agent

Here's a complete example of building an intelligent customer support agent with advanced memory capabilities:

```python
import asyncio
import os
from typing import Dict, List, Any

from symphony.api import Symphony
from symphony.agents.base import AgentConfig
from symphony.llm.litellm_client import LiteLLMClient, LiteLLMConfig
from symphony.memory.importance import RuleBasedStrategy, LLMBasedStrategy, HybridStrategy
from symphony.memory.memory_manager import ConversationMemoryManager, WorkingMemory
from symphony.memory.vector_memory import VectorMemory, SimpleEmbedder
from symphony.memory.local_kg_memory import LocalKnowledgeGraphMemory, SimpleEmbeddingModel
from symphony.tools.base import tool
from symphony.utils.types import Message


# 1. Define customer support-specific tools
@tool(name="lookup_order", description="Look up customer order information")
async def lookup_order(order_id: str) -> Dict[str, Any]:
    """Look up information about a customer order."""
    # In a real implementation, this would query a database
    orders = {
        "ORD-123": {
            "status": "shipped",
            "items": ["Laptop", "Mouse"],
            "delivery_date": "2025-04-10"
        },
        "ORD-456": {
            "status": "processing",
            "items": ["Monitor", "Keyboard"],
            "delivery_date": None
        }
    }
    return orders.get(order_id, {"status": "not_found"})


@tool(name="check_product_availability", description="Check if a product is in stock")
async def check_product_availability(product_name: str) -> Dict[str, Any]:
    """Check if a product is available in inventory."""
    # In a real implementation, this would query inventory system
    inventory = {
        "Laptop": {"in_stock": True, "quantity": 15, "next_restock": None},
        "Monitor": {"in_stock": True, "quantity": 8, "next_restock": None},
        "Keyboard": {"in_stock": False, "quantity": 0, "next_restock": "2025-04-15"},
        "Mouse": {"in_stock": True, "quantity": 23, "next_restock": None}
    }
    return inventory.get(product_name, {"in_stock": False, "quantity": 0, "next_restock": "unknown"})


# 2. Create a specialized importance strategy for customer support
class CustomerSupportStrategy(RuleBasedStrategy):
    """Specialized importance strategy for customer support scenarios."""
    
    def __init__(self):
        # Define customer support-specific keywords
        super().__init__(
            action_keywords=[
                "order", "refund", "cancel", "return", "shipping",
                "delivery", "payment", "warranty", "broken", "damaged"
            ],
            question_bonus=0.2,
            action_bonus=0.4,
            user_bonus=0.1,
            base_importance=0.5
        )
    
    async def calculate_importance(self, content: str, context: Dict[str, Any] = None) -> float:
        """Calculate importance with customer support-specific logic."""
        importance = await super().calculate_importance(content, context)
        
        # Increase importance for order-related queries
        if "order" in content.lower() and any(id_pattern in content for id_pattern in ["ORD-", "#"]):
            importance += 0.3
            
        # Increase importance for urgent issues
        urgent_terms = ["urgent", "immediately", "asap", "emergency", "today"]
        if any(term in content.lower() for term in urgent_terms):
            importance += 0.3
            
        # Cap at 1.0
        return min(importance, 1.0)


async def main():
    # 3. Initialize Symphony
    symphony = Symphony()
    
    # 4. Configure LLM
    llm_config = LiteLLMConfig(
        model="openai/gpt-4",
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    llm_client = LiteLLMClient(config=llm_config)
    
    # 5. Create memory components
    # Create a hybrid importance strategy
    rule_strategy = CustomerSupportStrategy()
    llm_strategy = LLMBasedStrategy(llm_client=llm_client)
    
    hybrid_strategy = HybridStrategy([
        (rule_strategy, 0.7),  # Higher weight to rule-based for predictability
        (llm_strategy, 0.3)    # Some LLM input for nuanced understanding
    ])
    
    # Create specialized working memory with shorter retention
    working_memory = WorkingMemory(retention_period=1800)  # 30 minutes
    
    # Create vector memory with persistent storage
    vector_memory = VectorMemory(
        embedder=SimpleEmbedder(dimension=384),
        persist_path="./customer_support_memory.pkl"
    )
    
    # Create knowledge graph memory for relationships
    kg_memory = LocalKnowledgeGraphMemory(
        llm_client=llm_client,
        embedding_model=SimpleEmbeddingModel(dimension=384),
        storage_path="./customer_support_kg.pkl",
        auto_extract=True
    )
    
    # Create conversation memory manager with all components
    memory_manager = ConversationMemoryManager(
        working_memory=working_memory,
        long_term_memory=vector_memory,
        kg_memory=kg_memory,
        importance_strategy=hybrid_strategy,
        memory_thresholds={
            "long_term": 0.6,  # Store more in long-term (lower threshold)
            "kg": 0.8          # Be selective about KG storage
        }
    )
    
    # 6. Create customer support agent
    agent_config = AgentConfig(
        name="CustomerSupportAgent",
        agent_type="support",
        description="An agent that provides customer support with memory of past interactions",
        tools=["lookup_order", "check_product_availability"]
    )
    
    # Register the agent with Symphony
    agent_id = await symphony.agents.create_agent(
        config=agent_config,
        llm=llm_client,
        memory=memory_manager,
        tools=[lookup_order, check_product_availability]
    )
    
    # 7. Simulate a customer conversation
    conversation = [
        "Hi, I'm having an issue with my recent order. The order number is ORD-123.",
        "Can you tell me when it will be delivered?",
        "Thanks. I also wanted to check if you have keyboards in stock?",
        "When will keyboards be back in stock?",
        "One more thing - my previous order had a broken mouse. Can you help with that?",
        "I'd like to return it for a refund.",
        "search: previous order issues"  # Special command to search memory
    ]
    
    # Process each message
    for message in conversation:
        print(f"\nCustomer: {message}")
        
        if message.startswith("search:"):
            # Handle memory search
            search_results = await symphony.agents.search_agent_conversation(
                agent_id=agent_id,
                query=message[7:].strip()
            )
            
            print("Agent memory search results:")
            for i, result in enumerate(search_results, 1):
                print(f"  {i}. {result.content[:100]}...")
        else:
            # Normal agent interaction
            response = await symphony.agents.run_agent(
                agent_id=agent_id,
                input=message
            )
            
            print(f"Agent: {response}")
    
    # 8. Show memory statistics
    print("\nMemory usage statistics:")
    if hasattr(memory_manager.memories["long_term"], "get_stats"):
        stats = memory_manager.memories["long_term"].get_stats()
        print(f"Long-term memory: {stats.get('entry_count', 0)} entries")
    
    # 9. Run memory consolidation to prepare for future sessions
    await memory_manager.consolidate()
    print("Memory consolidated for future sessions")


if __name__ == "__main__":
    asyncio.run(main())
```

This example demonstrates:

1. **Specialized memory strategies** tailored to a specific domain (customer support)
2. **Multi-tier memory** with working, long-term, and knowledge graph components
3. **Tool integration** for domain-specific capabilities
4. **Memory persistence** across sessions
5. **Memory search** for retrieving past information
6. **Importance assessment** using both rules and LLM understanding

You can adapt this pattern to other domains by:
- Creating domain-specific importance strategies
- Configuring memory thresholds based on domain needs
- Implementing specialized tools
- Customizing the consolidation process