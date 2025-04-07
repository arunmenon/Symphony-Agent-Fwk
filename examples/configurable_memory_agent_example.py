"""Example demonstrating agent building with configurable memory strategies.

This example demonstrates how to build Symphony agents with configurable memory
systems, allowing for customized importance assessment without being tied to
specific domains.

Key concepts demonstrated:
1. Building agents with customized memory configurations
2. Using the strategy pattern for flexible importance assessment
3. Creating and configuring rule-based, LLM-based, and hybrid strategies
4. Setting appropriate memory thresholds for different use cases
5. Using the agent builder pattern with memory configuration
6. Demonstrating how the choice of strategy affects memory retention

IMPORTANT: For best results with LLM-based importance assessment, use advanced 
language models with strong reasoning capabilities for more accurate evaluation.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.builder.agent_builder import AgentBuilder
from symphony.core.factory import MemoryFactory
from symphony.core.registry import ServiceRegistry
from symphony.memory.importance import (
    ImportanceStrategy, 
    RuleBasedStrategy, 
    LLMBasedStrategy, 
    HybridStrategy
)
from symphony.memory.memory_manager import ConversationMemoryManager
from symphony.utils.types import Message


class MockLLMClient:
    """Mock LLM client that simulates high-quality model responses.
    
    This mock simulates the behavior of an advanced language model for importance
    assessment. In production, you should use models with strong reasoning
    capabilities for accurate importance evaluation.
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


class CustomerServiceStrategy(RuleBasedStrategy):
    """Custom importance strategy for customer service scenarios."""
    
    def __init__(
        self,
        action_keywords: Optional[List[str]] = None,
        question_bonus: float = 0.2,
        action_bonus: float = 0.3,
        user_bonus: float = 0.1,
        base_importance: float = 0.5
    ):
        """Initialize customer service importance strategy."""
        # Define customer service keywords if not provided
        if action_keywords is None:
            action_keywords = [
                "order", "refund", "cancel", "return", "shipping",
                "delivery", "payment", "warranty", "broken", "damaged",
                "complaint", "urgent", "issue", "problem", "support"
            ]
            
        super().__init__(
            action_keywords=action_keywords,
            question_bonus=question_bonus,
            action_bonus=action_bonus,
            user_bonus=user_bonus,
            base_importance=base_importance
        )
    
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance with customer service-specific logic."""
        importance = await super().calculate_importance(content, context)
        content_lower = content.lower()
        
        # Increase importance for order-related queries with order IDs
        if "order" in content_lower and "#" in content:
            importance += 0.2
            
        # Increase importance for urgent issues
        urgent_terms = ["urgent", "immediately", "asap", "emergency", "today"]
        if any(term in content_lower for term in urgent_terms):
            importance += 0.2
            
        # Cap at 1.0
        return min(importance, 1.0)


async def build_project_management_agent():
    """Build an agent for project management with customized memory strategy."""
    print("\n=== Building Project Management Agent ===")
    
    # Create mock LLM client
    llm_client = MockLLMClient()
    
    # Create registry
    registry = ServiceRegistry.get_instance()
    
    # Create custom project management strategy
    project_strategy = ProjectManagementStrategy(
        deadline_bonus=0.4,  # Significant bonus for deadline mentions
        base_importance=0.5
    )
    
    # Create LLM-based strategy with project management focus
    llm_strategy = LLMBasedStrategy(
        llm_client=llm_client,
        default_prompt=(
            "You are evaluating the importance of information for a project management assistant.\n"
            "Consider factors like deadlines, priorities, decisions, and critical information.\n"
            "Rate the importance of this information on a scale of 0-10:\n"
            "Content: {content}\n"
            "Importance score (0-10):"
        )
    )
    
    # Create hybrid strategy combining both approaches
    hybrid_strategy = HybridStrategy([
        (project_strategy, 0.7),  # Higher weight for rule-based for predictability
        (llm_strategy, 0.3)       # Some LLM input for nuanced understanding
    ])
    
    # Build agent using hybrid strategy
    agent_config = (AgentBuilder(registry=registry)
        .create(
            name="ProjectManagerAgent", 
            role="Project manager", 
            instruction_template="You are a helpful project management assistant."
        )
        .with_model("advanced-model")
        .with_capabilities(["project_management", "planning", "collaboration"])
        .with_custom_memory_strategy(hybrid_strategy)
        .with_memory_thresholds(long_term=0.6, kg=0.8)
        .with_knowledge_graph(enabled=True)
        .build())
    
    print(f"Agent built: {agent_config.name}")
    print(f"Role: {agent_config.role}")
    print(f"Capabilities: {', '.join(agent_config.capabilities.expertise)}")
    print(f"Memory strategy: Hybrid (Project Management + LLM)")
    print(f"Memory thresholds: {agent_config.metadata.get('memory_thresholds', {})}")
    print(f"KG memory enabled: {agent_config.metadata.get('use_kg_memory', False)}")


async def build_customer_service_agent():
    """Build an agent for customer service with specialized memory strategy."""
    print("\n=== Building Customer Service Agent ===")
    
    # Create mock LLM client
    llm_client = MockLLMClient()
    
    # Create registry
    registry = ServiceRegistry.get_instance()
    
    # Using factory pattern through the agent builder
    agent_config = (AgentBuilder(registry=registry)
        .create(
            name="CustomerServiceAgent", 
            role="Customer service representative", 
            instruction_template="You are a helpful customer service representative."
        )
        .with_model("advanced-model")
        .with_capabilities(["customer_service", "problem_solving"])
        # Use rule-based strategy with custom keywords
        .with_memory_importance_strategy(
            "rule",
            action_keywords=[
                "order", "refund", "cancel", "return", "shipping",
                "delivery", "payment", "warranty", "broken", "damaged",
                "complaint", "urgent", "issue", "problem", "support"
            ],
            question_bonus=0.3,
            action_bonus=0.4,
            user_bonus=0.2,
            base_importance=0.5
        )
        .with_memory_thresholds(long_term=0.6, kg=0.8)
        .with_knowledge_graph(enabled=True)
        .build())
    
    print(f"Agent built: {agent_config.name}")
    print(f"Role: {agent_config.role}")
    print(f"Capabilities: {', '.join(agent_config.capabilities.expertise)}")
    print(f"Memory strategy: Rule-based with customer service keywords")
    print(f"Memory thresholds: {agent_config.metadata.get('memory_thresholds', {})}")
    print(f"KG memory enabled: {agent_config.metadata.get('use_kg_memory', False)}")


async def build_hybrid_strategy_agent():
    """Build an agent with a hybrid importance assessment strategy."""
    print("\n=== Building Hybrid Strategy Agent ===")
    
    # Create mock LLM client
    llm_client = MockLLMClient()
    
    # Create registry
    registry = ServiceRegistry.get_instance()
    
    # Build agent with hybrid strategy using factory approach
    agent_config = (AgentBuilder(registry=registry)
        .create(
            name="HybridAgent", 
            role="Assistant with hybrid memory assessment", 
            instruction_template="You are an intelligent assistant with advanced memory capabilities."
        )
        .with_model("advanced-model")
        .with_capabilities(["memory_management", "context_awareness"])
        # Use hybrid strategy through the builder's factory method
        .with_memory_importance_strategy(
            "hybrid",
            llm_client=llm_client,
            rule_weight=0.5,
            llm_weight=0.5,
            # Configure the rule-based component
            action_keywords=[
                "important", "critical", "remember", "urgent", "priority", 
                "deadline", "decision", "key", "significant", "essential"
            ],
            base_importance=0.5
        )
        .with_memory_thresholds(long_term=0.6, kg=0.8)
        .with_knowledge_graph(enabled=True)
        .build())
    
    print(f"Agent built: {agent_config.name}")
    print(f"Role: {agent_config.role}")
    print(f"Capabilities: {', '.join(agent_config.capabilities.expertise)}")
    print(f"Memory strategy: Hybrid (50% rule-based, 50% LLM)")
    print(f"Memory thresholds: {agent_config.metadata.get('memory_thresholds', {})}")
    print(f"KG memory enabled: {agent_config.metadata.get('use_kg_memory', False)}")


async def demonstrate_configurable_memory_thresholds():
    """Demonstrate how memory thresholds affect information storage."""
    print("\n=== Memory Threshold Configuration Demo ===")
    
    # Create a sample strategy
    strategy = RuleBasedStrategy(
        action_keywords=["important", "critical", "deadline", "urgent"],
        base_importance=0.5
    )
    
    # Create memory managers with different thresholds
    memory_configs = {
        "Conservative": ConversationMemoryManager(
            importance_strategy=strategy,
            memory_thresholds={"long_term": 0.8, "kg": 0.9}  # Very selective
        ),
        "Balanced": ConversationMemoryManager(
            importance_strategy=strategy,
            memory_thresholds={"long_term": 0.6, "kg": 0.8}  # Moderate
        ),
        "Generous": ConversationMemoryManager(
            importance_strategy=strategy,
            memory_thresholds={"long_term": 0.4, "kg": 0.7}  # Stores more
        )
    }
    
    # Test messages with different importance levels
    test_messages = [
        {
            "content": "The weather looks nice today.",
            "role": "user",
            "description": "Low importance message"
        },
        {
            "content": "I prefer the blue design for the website.",
            "role": "user",
            "description": "Medium importance message"
        },
        {
            "content": "The project deadline is tomorrow, it's critical!",
            "role": "user",
            "description": "High importance message"
        }
    ]
    
    # Process each message with different memory configurations
    for message_data in test_messages:
        content = message_data["content"]
        role = message_data["role"]
        description = message_data["description"]
        
        print(f"\n=== {description} ===")
        print(f"Message: \"{content}\"")
        
        # Get importance score
        importance = await strategy.calculate_importance(content, {"role": role})
        print(f"Importance score: {importance:.2f}")
        
        # Show which memory systems would store the message with each configuration
        print("\nStorage decisions:")
        for config_name, memory in memory_configs.items():
            locations = ["Working Memory"]
            thresholds = memory.memory_thresholds
            
            if importance > thresholds.get("long_term", 0.7):
                locations.append("Long-term Memory")
            if importance > thresholds.get("kg", 0.8):
                locations.append("Knowledge Graph")
                
            print(f"  {config_name} ({thresholds}): {', '.join(locations)}")


async def main():
    """Run the example."""
    print("=== Symphony Configurable Memory Agent Example ===")
    
    # Build example agents with different memory configurations
    await build_project_management_agent()
    await build_customer_service_agent()
    await build_hybrid_strategy_agent()
    
    # Demonstrate memory threshold configuration
    await demonstrate_configurable_memory_thresholds()
    
    print("\nThis example demonstrates how to build agents with customized memory systems.")
    print("The key insights are:")
    print("1. Memory importance assessment is configurable with different strategies")
    print("2. Memory thresholds can be adjusted based on application requirements")
    print("3. Custom strategies can be tailored to different use cases")
    print("4. Hybrid strategies can combine rule-based and LLM-based assessment")
    print("5. The AgentBuilder pattern provides a clean interface for configuration")


if __name__ == "__main__":
    asyncio.run(main())