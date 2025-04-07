"""Example demonstrating domain-specific importance assessment strategies for memory.

This example showcases Symphony's specialized domain-specific memory importance strategies, 
which determine how agent memory systems prioritize information. Different agent types 
(customer support, educational, medical, etc.) have different requirements for what's 
considered important information to remember.

Key concepts demonstrated:
1. Domain-specific strategy creation and configuration
2. Importance assessment of different messages in context
3. Storage location determination based on importance scores
4. Comparative analysis of how different domains assess the same message
5. Memory tier selection (working memory, long-term, knowledge graph)

The domain strategies improve agent memory capabilities by encoding domain expertise
into the memory system, ensuring the most relevant information is retained for each
agent's specific purpose and context.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.memory.domain_strategies import (
    CustomerSupportStrategy,
    ProductResearchStrategy,
    PersonalAssistantStrategy,
    EducationalStrategy,
    MedicalAssistantStrategy
)
from symphony.memory.memory_manager import ConversationMemoryManager
from symphony.utils.types import Message


class MockLLMClient:
    """Mock LLM client that simulates high-quality model responses.
    
    This mock simulates the behavior of a powerful language model for importance
    assessment. In production, you should use advanced models with strong
    reasoning capabilities for accurate importance assessment.
    """
    
    async def generate(self, prompt: str) -> str:
        """Generate a high-quality model response based on the prompt."""
        # For importance assessment prompts
        if "Rate importance" in prompt or "Evaluate" in prompt:
            # Simulate sophisticated reasoning about importance
            if "deadline" in prompt.lower() or "critical" in prompt.lower():
                return "9"  # High importance for deadlines or critical info
            elif "meeting" in prompt.lower() or "task" in prompt.lower():
                return "7"  # Medium-high importance for meetings/tasks
            elif "preference" in prompt.lower():
                return "5"  # Medium importance for preferences
            else:
                return "3"  # Low importance for general conversation
                
        # Default response
        return "This is a mock response simulating advanced model reasoning."


async def demonstrate_customer_support_strategy():
    """Demonstrate customer support-specific importance assessment."""
    print("\n=== Customer Support Strategy ===")
    
    # Create customer support strategy
    strategy = CustomerSupportStrategy()
    
    # Create memory manager with strategy
    memory_manager = ConversationMemoryManager(
        importance_strategy=strategy,
        memory_thresholds={"long_term": 0.7, "kg": 0.8}
    )
    
    # Test importance assessment with different messages
    test_messages = [
        ("I'd like to check on my order status.", "user"),
        ("My order #12345 hasn't arrived yet.", "user"),
        ("I need a refund for my broken headphones.", "user"),
        ("This is urgent! My account has been charged twice.", "user"),
        ("I'm very unhappy with the customer service I received.", "user"),
        ("When will the blue shirt be back in stock?", "user")
    ]
    
    for content, role in test_messages:
        context = {"role": role}
        
        # Calculate importance
        importance = await strategy.calculate_importance(content, context)
        
        # Determine storage locations
        locations = ["working"]
        if importance > 0.7:
            locations.append("long_term")
        if importance > 0.8:
            locations.append("kg")
            
        print(f"Message: \"{content}\"")
        print(f"Importance: {importance:.2f}")
        print(f"Storage: {', '.join(locations)}")
        print()


async def demonstrate_product_research_strategy():
    """Demonstrate product research-specific importance assessment."""
    print("\n=== Product Research Strategy ===")
    
    # Create product research strategy with specific categories
    strategy = ProductResearchStrategy(
        product_categories=["smartphone", "tablet", "laptop", "wearable"],
        feature_terms=["performance", "battery life", "camera", "display", "UI"]
    )
    
    # Test importance assessment with different messages
    test_messages = [
        ("The new prototype achieved 120fps refresh rate with 15% less power consumption.", "user"),
        ("User testing shows people prefer the simplified UI design.", "user"),
        ("Competitor X just released a device with similar features at $50 less.", "user"),
        ("We've decided to focus on improving the camera quality for the next release.", "user"),
        ("Should we use the new processor or stick with the current one?", "user")
    ]
    
    for content, role in test_messages:
        context = {"role": role}
        
        # Calculate importance
        importance = await strategy.calculate_importance(content, context)
        
        print(f"Message: \"{content}\"")
        print(f"Importance: {importance:.2f}")
        print()


async def demonstrate_personal_assistant_strategy():
    """Demonstrate personal assistant-specific importance assessment."""
    print("\n=== Personal Assistant Strategy ===")
    
    # Create personal assistant strategy with user-specific information
    strategy = PersonalAssistantStrategy(
        user_contacts=["John Smith", "Sarah Johnson", "Michael Brown"],
        user_interests=["running", "photography", "cooking", "travel"]
    )
    
    # Test importance assessment with different messages
    test_messages = [
        ("Remind me to call John Smith tomorrow at 3:30pm.", "user"),
        ("I need to pick up my photos from the store.", "user"),
        ("Please schedule a meeting with Sarah Johnson for next Tuesday.", "user"),
        ("Don't forget my doctor's appointment on Friday at 10am.", "user"),
        ("I'm thinking about trying a new pasta recipe this weekend.", "user")
    ]
    
    for content, role in test_messages:
        context = {"role": role}
        
        # Calculate importance
        importance = await strategy.calculate_importance(content, context)
        
        print(f"Message: \"{content}\"")
        print(f"Importance: {importance:.2f}")
        print()


async def demonstrate_educational_strategy():
    """Demonstrate educational-specific importance assessment."""
    print("\n=== Educational Strategy ===")
    
    # Create educational strategy for advanced physics
    strategy = EducationalStrategy(
        subjects=["physics", "quantum mechanics", "relativity"],
        learning_level="advanced"
    )
    
    # Test importance assessment with different messages
    test_messages = [
        ("The concept of quantum entanglement refers to particles that interact in ways such that their quantum states cannot be described independently.", "assistant"),
        ("For tomorrow's exam, remember the formula for calculating relativistic momentum.", "assistant"),
        ("Here's an example of how to solve a simple harmonic oscillator problem.", "assistant"),
        ("The key principle to understand is that energy and mass are equivalent, as expressed in E=mc².", "assistant"),
        ("When would you like to schedule our next study session?", "assistant")
    ]
    
    for content, role in test_messages:
        context = {"role": role}
        
        # Calculate importance
        importance = await strategy.calculate_importance(content, context)
        
        print(f"Message: \"{content}\"")
        print(f"Importance: {importance:.2f}")
        print()


async def demonstrate_medical_assistant_strategy():
    """Demonstrate medical assistant-specific importance assessment."""
    print("\n=== Medical Assistant Strategy ===")
    
    # Create medical strategy with specific terms
    strategy = MedicalAssistantStrategy(
        medical_terms=["diabetes", "hypertension", "asthma", "cholesterol"]
    )
    
    # Test importance assessment with different messages
    test_messages = [
        ("Take 10mg of medication twice daily with food.", "assistant"),
        ("If you experience severe dizziness, seek emergency care immediately.", "assistant"),
        ("Your blood pressure reading was slightly elevated at 135/85.", "assistant"),
        ("Remember to monitor your blood sugar levels before each meal.", "assistant"),
        ("Let's schedule a follow-up appointment in two weeks.", "assistant")
    ]
    
    for content, role in test_messages:
        context = {"role": role}
        
        # Calculate importance
        importance = await strategy.calculate_importance(content, context)
        
        print(f"Message: \"{content}\"")
        print(f"Importance: {importance:.2f}")
        print()


async def compare_strategies():
    """Compare how different strategies rate the same message."""
    print("\n=== Strategy Comparison ===")
    
    # Create sample strategies
    strategies = {
        "Customer Support": CustomerSupportStrategy(),
        "Product Research": ProductResearchStrategy(),
        "Personal Assistant": PersonalAssistantStrategy(),
        "Educational": EducationalStrategy(),
        "Medical": MedicalAssistantStrategy()
    }
    
    # Test messages that might be interpreted differently by different domains
    test_messages = [
        "Please remember to check on this by tomorrow at 3pm.",
        "This is a critical issue that needs immediate attention.",
        "The user reported experiencing problems with the latest update.",
        "Here's an example of how this works in practice."
    ]
    
    for content in test_messages:
        print(f"Message: \"{content}\"")
        print("Importance by domain:")
        
        results = []
        for name, strategy in strategies.items():
            importance = await strategy.calculate_importance(content)
            results.append((name, importance))
            
        # Sort by importance (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        for name, importance in results:
            print(f"  {name}: {importance:.2f}")
        print()


async def main():
    """Run the example."""
    print("=== Symphony Domain-Specific Memory Strategies Example ===")
    
    # Demonstrate domain-specific strategies
    await demonstrate_customer_support_strategy()
    await demonstrate_product_research_strategy()
    await demonstrate_personal_assistant_strategy()
    await demonstrate_educational_strategy()
    await demonstrate_medical_assistant_strategy()
    
    # Compare how different strategies assess the same content
    await compare_strategies()


if __name__ == "__main__":
    asyncio.run(main())