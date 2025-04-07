"""Example demonstrating configurable importance assessment strategies for memory.

This example showcases Symphony's configurable importance assessment system, 
which allows you to customize how memory systems determine what information is important.
Different applications may require different approaches to importance evaluation.

Key concepts demonstrated:
1. Creating custom rule-based importance strategies
2. Using LLM-based semantic importance assessment
3. Combining multiple strategies with hybrid approaches
4. Configuring memory systems with custom importance evaluation
5. Testing different assessment criteria with sample messages

Memory importance assessment allows intelligent filtering of information,
ensuring the most valuable content gets stored in long-term memory while
less critical details might only remain in short-term storage.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.memory.importance import RuleBasedStrategy, LLMBasedStrategy, HybridStrategy
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


class ProjectManagementStrategy(RuleBasedStrategy):
    """Custom importance strategy for project management scenarios."""
    
    def __init__(
        self,
        action_keywords: Optional[List[str]] = None,
        question_bonus: float = 0.2,
        action_bonus: float = 0.3,
        deadline_bonus: float = 0.4,
        user_bonus: float = 0.1,
        base_importance: float = 0.5
    ):
        """Initialize project management importance strategy."""
        # Define project management keywords if not provided
        if action_keywords is None:
            action_keywords = [
                "task", "project", "milestone", "deadline", "deliverable",
                "priority", "high-priority", "critical", "urgent", "important",
                "meeting", "stakeholder", "review", "approval", "decision"
            ]
            
        super().__init__(
            action_keywords=action_keywords,
            question_bonus=question_bonus,
            action_bonus=action_bonus,
            user_bonus=user_bonus,
            base_importance=base_importance
        )
        
        self.deadline_bonus = deadline_bonus
    
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance with project management logic."""
        importance = await super().calculate_importance(content, context)
        content_lower = content.lower()
        
        # Increase importance for deadline mentions
        deadline_indicators = ["by tomorrow", "due date", "due by", "deadline is", "due on"]
        if any(indicator in content_lower for indicator in deadline_indicators):
            importance += self.deadline_bonus
            
        # Increase importance for decision indicators
        decision_indicators = ["decided", "approved", "agreed", "confirmed", "finalized"]
        if any(indicator in content_lower for indicator in decision_indicators):
            importance += 0.2
            
        # Cap at 1.0
        return min(importance, 1.0)


async def demonstrate_custom_rule_strategy():
    """Demonstrate custom rule-based importance assessment."""
    print("\n=== Custom Rule-Based Strategy ===")
    
    # Create custom rule-based strategy
    project_strategy = ProjectManagementStrategy(
        deadline_bonus=0.4  # Significant bonus for deadline mentions
    )
    
    # Create memory manager with custom strategy
    memory_manager = ConversationMemoryManager(
        importance_strategy=project_strategy,
        memory_thresholds={"long_term": 0.7, "kg": 0.8}
    )
    
    # Test importance assessment with different messages
    test_messages = [
        ("Do you have an update on the project status?", "user"),
        ("We're making good progress.", "assistant"),
        ("The client meeting is scheduled for Friday.", "assistant"),
        ("The project deadline is tomorrow, we need to finalize everything today.", "user"),
        ("I've decided to approve the design changes.", "user")
    ]
    
    for content, role in test_messages:
        message = Message(role=role, content=content)
        context = {"role": role}
        
        # Calculate importance
        importance = await project_strategy.calculate_importance(content, context)
        
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
    
    # Create LLM-based strategy with custom prompt
    llm_strategy = LLMBasedStrategy(
        llm_client=llm_client,
        default_prompt=(
            "Evaluate the importance of this information on a scale of 0-10:\n"
            "Consider factors like urgency, relevance to current tasks, and potential future value.\n"
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
        ("What's the weather like today?", "user"),
        ("The meeting is scheduled for tomorrow at 2pm.", "assistant"),
        ("I prefer the blue design for the website.", "user"),
        ("There's a critical issue with the database that needs immediate attention.", "user")
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
    project_strategy = ProjectManagementStrategy(deadline_bonus=0.3)
    llm_strategy = LLMBasedStrategy(llm_client=llm_client)
    
    # Create hybrid strategy with weights
    hybrid_strategy = HybridStrategy([
        (project_strategy, 0.6),  # 60% weight for rule-based
        (llm_strategy, 0.4)       # 40% weight for LLM-based
    ])
    
    # Create memory manager with hybrid strategy
    memory_manager = ConversationMemoryManager(
        importance_strategy=hybrid_strategy,
        memory_thresholds={"long_term": 0.7, "kg": 0.8}
    )
    
    # Test importance assessment with different messages
    test_messages = [
        ("The project deadline is next Friday, we need to complete all tasks by then.", "user"),
        ("I'll make sure everything is done on time.", "assistant")
    ]
    
    for content, role in test_messages:
        message = Message(role=role, content=content)
        context = {"role": role}
        
        # Get individual assessments for comparison
        rule_score = await project_strategy.calculate_importance(content, context)
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
    print("=== Symphony Configurable Importance Assessment Example ===")
    
    # Demonstrate different importance strategies
    await demonstrate_custom_rule_strategy()
    await demonstrate_llm_based_strategy()
    await demonstrate_hybrid_strategy()


if __name__ == "__main__":
    asyncio.run(main())