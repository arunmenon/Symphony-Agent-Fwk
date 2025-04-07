"""Example demonstrating Symphony's memory factory with domain-specific strategies.

This example shows how to leverage the MemoryFactory to create various memory systems, 
including advanced conversation memory managers with domain-specific importance assessment.

Key concepts demonstrated:
1. Basic memory creation (in-memory and conversation)
2. Advanced memory managers with domain-specific strategies
3. Custom importance assessment for different agent domains
4. Memory tier selection based on message importance
5. Factory convenience methods for simplified memory creation

The example uses high-quality models (or their mocks) for LLM-based importance assessment,
which is crucial for accurately determining the most relevant information to remember.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.memory.memory_manager import ConversationMemoryManager
from symphony.memory.domain_strategies import CustomerSupportStrategy
from symphony.memory.strategy_factory import ImportanceStrategyFactory
from symphony.core.factory import MemoryFactory
from symphony.utils.types import Message


# Example MockLLMClient for LLM-based strategies
class MockLLMClient:
    """Mock LLM client for demonstration purposes."""
    
    async def generate(self, prompt: str) -> str:
        """Generate a response based on the prompt."""
        # For importance assessment prompts
        if "importance" in prompt.lower() or "evaluate" in prompt.lower():
            if "urgent" in prompt.lower() or "emergency" in prompt.lower():
                return "9"  # High importance for urgent messages
            elif "order" in prompt.lower() or "refund" in prompt.lower():
                return "7"  # Medium-high importance for customer orders/refunds
            elif "question" in prompt.lower() or "when" in prompt.lower():
                return "5"  # Medium importance for questions
            else:
                return "3"  # Low importance for general messages
                
        # Default response
        return "This is a mock response."


async def demonstrate_factory_basic():
    """Demonstrate basic memory factory usage."""
    print("\n=== Basic Memory Factory Usage ===")
    
    # Create in-memory storage
    in_memory = MemoryFactory.create("in_memory")
    in_memory.store("greeting", "Hello, world!")
    result = in_memory.retrieve("greeting")
    print(f"In-memory storage: {result}")
    
    # Create conversation memory
    conversation = MemoryFactory.create("conversation")
    conversation.add_message(Message(role="user", content="What time is it?"))
    messages = conversation.get_messages()
    print(f"Conversation memory has {len(messages)} messages")
    print(f"First message: {messages[0].role}: {messages[0].content}")


async def demonstrate_factory_with_domain_strategies():
    """Demonstrate memory factory with domain-specific strategies."""
    print("\n=== Memory Factory with Domain Strategies ===")
    
    # Create mock LLM client for strategy that needs it
    llm_client = MockLLMClient()
    
    # 1. Create a memory manager with customer support strategy
    customer_support_memory = MemoryFactory.create(
        "conversation_manager",
        importance_strategy_type="customer_support",
        strategy_params={
            "action_keywords": ["order", "refund", "urgent", "issue"],
            "base_importance": 0.5
        },
        memory_thresholds={"long_term": 0.7, "kg": 0.8}
    )
    
    # 2. Create a memory manager with educational strategy
    educational_memory = MemoryFactory.create(
        "conversation_manager",
        importance_strategy_type="educational",
        strategy_params={
            "subjects": ["physics", "math"],
            "learning_level": "advanced"
        },
        memory_thresholds={"long_term": 0.6, "kg": 0.8}
    )
    
    # 3. Create a memory manager with hybrid LLM strategy
    hybrid_memory = MemoryFactory.create(
        "conversation_manager",
        importance_strategy_type="hybrid",
        strategy_params={
            "llm_client": llm_client,
            "rule_weight": 0.6,
            "llm_weight": 0.4
        },
        memory_thresholds={"long_term": 0.7, "kg": 0.9}
    )
    
    print("Successfully created memory managers with different strategies")
    
    # Test with some messages
    customer_message = Message(
        role="user", 
        content="My order #12345 is damaged and I need an urgent refund!"
    )
    
    educational_message = Message(
        role="assistant",
        content="In physics, the principle of conservation of energy states that energy cannot be created or destroyed."
    )
    
    # Add messages to memory managers
    await customer_support_memory.add_message(customer_message)
    await educational_memory.add_message(educational_message)
    
    # Show storage locations based on importance calculation
    print("\nAssessing importance for different domains:")
    
    # Get memory managers with direct casts for type hints
    cs_memory: ConversationMemoryManager = customer_support_memory
    edu_memory: ConversationMemoryManager = educational_memory
    
    # Get messages back with importance info
    cs_messages = cs_memory.get_messages()
    edu_messages = edu_memory.get_messages()
    
    # Get importance via context and calculate
    cs_context = {"role": "user"}
    edu_context = {"role": "assistant"}
    
    cs_importance = await cs_memory.importance_strategy.calculate_importance(
        customer_message.content, cs_context
    )
    
    edu_importance = await edu_memory.importance_strategy.calculate_importance(
        educational_message.content, edu_context
    )
    
    # Print results
    print(f"Customer support message importance: {cs_importance:.2f}")
    print(f"Storage tiers: {get_storage_tiers(cs_importance, cs_memory.memory_thresholds)}")
    
    print(f"Educational message importance: {edu_importance:.2f}")
    print(f"Storage tiers: {get_storage_tiers(edu_importance, edu_memory.memory_thresholds)}")


async def demonstrate_factory_convenience_methods():
    """Demonstrate memory factory convenience methods."""
    print("\n=== Memory Factory Convenience Methods ===")
    
    # Create with specialized create method
    llm_client = MockLLMClient()
    memory = MemoryFactory.create_conversation_manager(
        importance_strategy_type="hybrid_medical",
        strategy_params={
            "llm_client": llm_client,
            "medical_terms": ["diabetes", "hypertension"],
            "domain_weight": 0.8,
            "llm_weight": 0.2
        },
        memory_thresholds={"long_term": 0.6, "kg": 0.7}
    )
    
    # Test with a medical message
    message = Message(
        role="assistant", 
        content="If you experience severe dizziness, seek emergency care immediately."
    )
    
    await memory.add_message(message)
    
    # Get importance
    medical_memory: ConversationMemoryManager = memory
    importance = await medical_memory.importance_strategy.calculate_importance(
        message.content, {"role": "assistant"}
    )
    
    print(f"Medical message importance: {importance:.2f}")
    print(f"Storage tiers: {get_storage_tiers(importance, medical_memory.memory_thresholds)}")


def get_storage_tiers(importance: float, thresholds: Dict[str, float]) -> str:
    """Determine storage tiers based on importance and thresholds."""
    tiers = ["Working Memory"]
    if importance > thresholds.get("long_term", 0.7):
        tiers.append("Long-term Memory")
    if importance > thresholds.get("kg", 0.8):
        tiers.append("Knowledge Graph")
    return ", ".join(tiers)


async def main():
    """Run the memory factory example."""
    print("=== Memory Factory Example ===")
    
    # Demonstrate basic memory factory
    await demonstrate_factory_basic()
    
    # Demonstrate factory with domain strategies
    await demonstrate_factory_with_domain_strategies()
    
    # Demonstrate convenience methods
    await demonstrate_factory_convenience_methods()


if __name__ == "__main__":
    asyncio.run(main())