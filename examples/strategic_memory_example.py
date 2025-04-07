"""Example demonstrating the strategy-based memory architecture."""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.memory.importance import RuleBasedStrategy, LLMBasedStrategy, HybridStrategy
from symphony.memory.memory_manager import ConversationMemoryManager, WorkingMemory
from symphony.memory.vector_memory import VectorMemory, SimpleEmbedder
from symphony.utils.types import Message


class MockLLMClient:
    """Mock LLM client for demonstration purposes."""
    
    async def generate(self, prompt: str) -> str:
        """Generate a response based on the prompt."""
        # For importance assessment prompts
        if "Rate importance" in prompt:
            if "deadline" in prompt.lower() or "critical" in prompt.lower():
                return "9"  # High importance for deadlines or critical info
            elif "meeting" in prompt.lower() or "task" in prompt.lower():
                return "7"  # Medium-high importance for meetings/tasks
            elif "preference" in prompt.lower():
                return "5"  # Medium importance for preferences
            else:
                return "3"  # Low importance for general conversation
                
        # Default response
        return "This is a mock response."


async def demonstrate_rule_based_strategy():
    """Demonstrate rule-based importance assessment."""
    print("\n=== Rule-Based Strategy ===")
    
    # Create rule-based strategy with custom settings
    rule_strategy = RuleBasedStrategy(
        action_keywords=["urgent", "critical", "important", "deadline", "must"],
        question_bonus=0.2,
        action_bonus=0.3,
        user_bonus=0.1
    )
    
    # Create memory manager with rule-based strategy
    memory_manager = ConversationMemoryManager(
        importance_strategy=rule_strategy,
        memory_thresholds={"long_term": 0.7, "kg": 0.8}
    )
    
    # Test importance assessment with different messages
    test_messages = [
        ("How's the weather today?", "user"),
        ("The weather is sunny.", "assistant"),
        ("What is the deadline for the project?", "user"),
        ("The deadline is Friday.", "assistant"),
        ("This is a critical issue that must be addressed.", "user"),
        ("I'll make sure it's handled with top priority.", "assistant")
    ]
    
    for content, role in test_messages:
        message = Message(role=role, content=content)
        context = {"role": role}
        
        # Calculate importance
        importance = await rule_strategy.calculate_importance(content, context)
        
        # Determine storage locations
        locations = ["working"]
        if importance > 0.7:
            locations.append("long_term")
        if importance > 0.8:
            locations.append("kg")
            
        print(f"Message: \"{content}\"")
        print(f"Role: {role}")
        print(f"Importance: {importance:.2f}")
        print(f"Storage: {', '.join(locations)}")
        print()
        
        # Store in memory manager
        await memory_manager.add_message(message)


async def demonstrate_llm_based_strategy():
    """Demonstrate LLM-based importance assessment."""
    print("\n=== LLM-Based Strategy ===")
    
    # Create mock LLM client
    llm_client = MockLLMClient()
    
    # Create LLM-based strategy
    llm_strategy = LLMBasedStrategy(
        llm_client=llm_client,
        default_prompt=(
            "Evaluate the importance of this information on a scale of 0-10:\n"
            "Content: {content}\n"
            "Role: {role}\n"
            "Importance (0-10):"
        )
    )
    
    # Create memory manager with LLM-based strategy
    memory_manager = ConversationMemoryManager(
        importance_strategy=llm_strategy,
        memory_thresholds={"long_term": 0.7, "kg": 0.8}
    )
    
    # Test importance assessment with different messages
    test_messages = [
        ("How's the weather today?", "user"),
        ("The meeting is scheduled for tomorrow.", "assistant"),
        ("I prefer using the blue theme for the presentation.", "user"),
        ("The critical system failure must be fixed immediately.", "assistant")
    ]
    
    for content, role in test_messages:
        message = Message(role=role, content=content)
        context = {"role": role}
        
        # Calculate importance
        importance = await llm_strategy.calculate_importance(content, context)
        
        # Determine storage locations
        locations = ["working"]
        if importance > 0.7:
            locations.append("long_term")
        if importance > 0.8:
            locations.append("kg")
            
        print(f"Message: \"{content}\"")
        print(f"Role: {role}")
        print(f"Importance: {importance:.2f}")
        print(f"Storage: {', '.join(locations)}")
        print()
        
        # Store in memory manager
        await memory_manager.add_message(message)


async def demonstrate_hybrid_strategy():
    """Demonstrate hybrid importance assessment."""
    print("\n=== Hybrid Strategy ===")
    
    # Create component strategies
    llm_client = MockLLMClient()
    rule_strategy = RuleBasedStrategy()
    llm_strategy = LLMBasedStrategy(llm_client=llm_client)
    
    # Create hybrid strategy with weights
    hybrid_strategy = HybridStrategy([
        (rule_strategy, 0.3),  # 30% weight for rule-based
        (llm_strategy, 0.7)    # 70% weight for LLM-based
    ])
    
    # Create memory manager with hybrid strategy
    memory_manager = ConversationMemoryManager(
        importance_strategy=hybrid_strategy,
        memory_thresholds={"long_term": 0.7, "kg": 0.8}
    )
    
    # Test importance assessment with different messages
    test_messages = [
        ("The project deadline is next Friday.", "user"),
        ("I'll make sure we're on track to meet it.", "assistant")
    ]
    
    for content, role in test_messages:
        message = Message(role=role, content=content)
        context = {"role": role}
        
        # Get individual assessments for comparison
        rule_score = await rule_strategy.calculate_importance(content, context)
        llm_score = await llm_strategy.calculate_importance(content, context)
        hybrid_score = await hybrid_strategy.calculate_importance(content, context)
        
        print(f"Message: \"{content}\"")
        print(f"Role: {role}")
        print(f"Rule-based score: {rule_score:.2f}")
        print(f"LLM-based score: {llm_score:.2f}")
        print(f"Hybrid score: {hybrid_score:.2f}")
        
        # Determine storage locations based on hybrid score
        locations = ["working"]
        if hybrid_score > 0.7:
            locations.append("long_term")
        if hybrid_score > 0.8:
            locations.append("kg")
            
        print(f"Storage: {', '.join(locations)}")
        print()
        
        # Store in memory manager
        await memory_manager.add_message(message)


async def main():
    """Run the example."""
    print("=== Symphony Strategic Memory Architecture Example ===")
    
    # Demonstrate different importance strategies
    await demonstrate_rule_based_strategy()
    await demonstrate_llm_based_strategy()
    await demonstrate_hybrid_strategy()


if __name__ == "__main__":
    asyncio.run(main())