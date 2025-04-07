"""Example demonstrating agent building with domain-specific memory strategies."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.builder.agent_builder import AgentBuilder
from symphony.core.registry import ServiceRegistry
from symphony.memory.domain_strategies import (
    CustomerSupportStrategy,
    ProductResearchStrategy,
    EducationalStrategy,
    MedicalAssistantStrategy,
    PersonalAssistantStrategy
)
from symphony.memory.strategy_factory import ImportanceStrategyFactory
from symphony.memory.importance import LLMBasedStrategy, HybridStrategy
from symphony.utils.types import Message


class MockLLMClient:
    """Mock LLM client for demonstration purposes."""
    
    async def generate(self, prompt: str) -> str:
        """Generate a response based on the prompt."""
        # For importance assessment prompts
        if "Rate importance" in prompt or "Evaluate" in prompt:
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


async def build_customer_support_agent():
    """Build an agent for customer support with specialized memory strategy."""
    print("\n=== Building Customer Support Agent ===")
    
    # Create mock LLM client
    llm_client = MockLLMClient()
    
    # Create registry
    registry = ServiceRegistry.get_instance()
    
    # Build agent using domain-specific strategy
    agent_config = (AgentBuilder(registry=registry)
        .create(
            name="CustomerSupportAgent", 
            role="Customer support specialist", 
            instruction_template="You are a helpful customer support agent."
        )
        .with_model("gpt-4")
        .with_capabilities(["customer_service", "problem_solving", "product_knowledge"])
        # Use factory through builder
        .with_memory_importance_strategy(
            "customer_support",
            action_keywords=["order", "refund", "urgent", "issue", "problem"]
        )
        .with_memory_thresholds(long_term=0.6, kg=0.8)  # Store more in long-term memory
        .with_knowledge_graph(enabled=True)
        .build())
    
    print(f"Agent built: {agent_config.name}")
    print(f"Capabilities: {', '.join(agent_config.capabilities.expertise)}")
    print(f"Memory type: {agent_config.metadata.get('memory_type', 'default')}")
    print(f"Memory thresholds: {agent_config.metadata.get('memory_thresholds', {})}")
    print(f"KG memory enabled: {agent_config.metadata.get('use_kg_memory', False)}")
    

async def build_educational_agent():
    """Build an agent for education with hybrid importance strategy."""
    print("\n=== Building Educational Agent ===")
    
    # Create mock LLM client
    llm_client = MockLLMClient()
    
    # Create registry
    registry = ServiceRegistry.get_instance()
    
    # Build agent using hybrid domain strategy
    agent_config = (AgentBuilder(registry=registry)
        .create(
            name="PhysicsTeacherAgent", 
            role="Physics instructor", 
            instruction_template="You are an expert physics teacher."
        )
        .with_model("gpt-4")
        .with_capabilities(["physics", "education", "explanation"])
        # Use hybrid domain strategy
        .with_memory_importance_strategy(
            "hybrid_educational",
            llm_client=llm_client,
            subjects=["physics", "mathematics"],
            learning_level="advanced",
            domain_weight=0.7,
            llm_weight=0.3
        )
        .with_memory_thresholds(long_term=0.5, kg=0.7)  # Even lower threshold for educational content
        .with_knowledge_graph(enabled=True)
        .build())
    
    print(f"Agent built: {agent_config.name}")
    print(f"Capabilities: {', '.join(agent_config.capabilities.expertise)}")
    print(f"Memory type: {agent_config.metadata.get('memory_type', 'default')}")
    print(f"Memory thresholds: {agent_config.metadata.get('memory_thresholds', {})}")
    print(f"KG memory enabled: {agent_config.metadata.get('use_kg_memory', False)}")


async def build_medical_assistant_agent():
    """Build an agent for medical assistance with specialized memory strategy."""
    print("\n=== Building Medical Assistant Agent ===")
    
    # Create mock LLM client
    llm_client = MockLLMClient()
    
    # Create registry
    registry = ServiceRegistry.get_instance()
    
    # Create medical terms and severity terms
    medical_terms = [
        "hypertension", "diabetes", "asthma", "arthritis", "migraine",
        "cholesterol", "thyroid", "anemia", "allergies"
    ]
    
    severity_terms = [
        "severe", "critical", "acute", "chronic", "urgent", 
        "emergency", "painful", "distressing"
    ]
    
    # Build agent using medical strategy directly from factory
    medical_strategy = ImportanceStrategyFactory.create_strategy(
        "medical",
        medical_terms=medical_terms,
        severity_terms=severity_terms,
        base_importance=0.6  # Higher base importance for all medical content
    )
    
    # Create LLM strategy with medical-specific prompt
    llm_strategy = LLMBasedStrategy(
        llm_client=llm_client,
        default_prompt=(
            "You are a medical assistant evaluating the importance of this information.\n"
            "Consider patient safety, medical relevance, and clinical significance.\n"
            "Content: {content}\n"
            "Importance score (0-10):"
        )
    )
    
    # Create hybrid strategy combining both
    hybrid_medical_strategy = HybridStrategy([
        (medical_strategy, 0.8),  # Higher weight for rule-based in medical context
        (llm_strategy, 0.2)
    ])
    
    # Build agent with custom strategy
    agent_config = (AgentBuilder(registry=registry)
        .create(
            name="MedicalAssistantAgent", 
            role="Medical assistant", 
            instruction_template="You are a helpful medical assistant. Always prioritize patient safety."
        )
        .with_model("gpt-4")
        .with_capabilities(["medical_knowledge", "patient_care", "health_monitoring"])
        .with_memory_importance_strategy("medical", 
            medical_terms=medical_terms,
            severity_terms=severity_terms,
            base_importance=0.6
        )
        # Alternative approach with custom strategy:
        # .with_custom_memory_strategy(hybrid_medical_strategy)
        .with_memory_thresholds(long_term=0.5, kg=0.7)  # Lower thresholds for medical info
        .with_knowledge_graph(enabled=True)
        .build())
    
    print(f"Agent built: {agent_config.name}")
    print(f"Capabilities: {', '.join(agent_config.capabilities.expertise)}")
    print(f"Memory type: {agent_config.metadata.get('memory_type', 'default')}")
    print(f"Memory thresholds: {agent_config.metadata.get('memory_thresholds', {})}")
    print(f"KG memory enabled: {agent_config.metadata.get('use_kg_memory', False)}")


async def demonstrate_message_routing():
    """Demonstrate how messages are routed to different memory tiers in each domain."""
    print("\n=== Message Routing Demonstration ===")
    
    # Create strategies
    llm_client = MockLLMClient()
    strategies = {
        "Customer Support": ImportanceStrategyFactory.create_strategy("customer_support"),
        "Educational": ImportanceStrategyFactory.create_strategy(
            "educational", subjects=["physics"], learning_level="advanced"
        ),
        "Medical": ImportanceStrategyFactory.create_strategy(
            "medical", medical_terms=["diabetes", "hypertension"]
        ),
        "Personal Assistant": ImportanceStrategyFactory.create_strategy(
            "personal_assistant", user_contacts=["John", "Sarah"]
        ),
        "Product Research": ImportanceStrategyFactory.create_strategy(
            "product_research", product_categories=["smartphone", "tablet"] 
        )
    }
    
    # Prepare test messages for each domain
    domain_messages = {
        "Customer Support": [
            "I need a refund for my broken laptop that I purchased last week.",
            "When will the blue shirt be back in stock?",
            "My order #12345 hasn't been delivered and it's urgent!"
        ],
        "Educational": [
            "The law of conservation of energy states that energy cannot be created or destroyed.",
            "For tomorrow's exam, remember the formula E=mc².",
            "Let's schedule our next physics tutoring session."
        ],
        "Medical": [
            "Take your medication twice daily with food.",
            "If you experience severe dizziness, seek emergency care immediately.",
            "Your blood pressure is slightly elevated at 135/85."
        ],
        "Personal Assistant": [
            "Remind me to call John tomorrow at 3pm.",
            "Add milk to my shopping list.",
            "Please reschedule my meeting with Sarah to Friday at 2pm."
        ],
        "Product Research": [
            "User testing shows that 85% of participants preferred the new interface.",
            "Our competitor just released a similar product at a 10% lower price point.",
            "The team decided to focus on improving battery life for the next release."
        ]
    }
    
    # Simulate thresholds
    thresholds = {
        "long_term": 0.7,
        "kg": 0.8
    }
    
    # Process messages and show routing
    for domain, messages in domain_messages.items():
        print(f"\n{domain} Domain:")
        strategy = strategies[domain]
        
        for message in messages:
            importance = await strategy.calculate_importance(message)
            
            # Determine storage locations
            storage = ["Working Memory"]
            if importance > thresholds["long_term"]:
                storage.append("Long-term Memory")
            if importance > thresholds["kg"]:
                storage.append("Knowledge Graph")
                
            print(f"  Message: \"{message}\"")
            print(f"  Importance: {importance:.2f}")
            print(f"  Storage: {', '.join(storage)}")
            print()


async def main():
    """Run the example."""
    print("=== Symphony Domain-Specific Memory Agent Example ===")
    
    # Build example agents
    await build_customer_support_agent()
    await build_educational_agent()
    await build_medical_assistant_agent()
    
    # Demonstrate message routing
    await demonstrate_message_routing()


if __name__ == "__main__":
    asyncio.run(main())