"""End-to-end integration tests for domain-specific memory strategies."""

import asyncio
import unittest
from typing import Dict, List, Any, Optional

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from symphony.builder.agent_builder import AgentBuilder
from symphony.core.registry import ServiceRegistry
from symphony.memory.domain_strategies import (
    CustomerSupportStrategy,
    ProductResearchStrategy,
    EducationalStrategy,
    MedicalAssistantStrategy
)
from symphony.memory.memory_manager import ConversationMemoryManager
from symphony.memory.strategy_factory import ImportanceStrategyFactory
from symphony.utils.types import Message


class MockLLMClient:
    """Mock LLM client for testing purposes."""
    
    async def generate(self, prompt: str) -> str:
        """Generate a response based on the prompt."""
        # For importance assessment prompts
        if "importance" in prompt.lower() or "evaluate" in prompt.lower():
            if "emergency" in prompt.lower() or "critical" in prompt.lower():
                return "9"  # High importance for emergencies
            elif "appointment" in prompt.lower() or "deadline" in prompt.lower():
                return "7"  # Medium-high importance for time-sensitive info
            else:
                return "4"  # Medium-low importance for general content
                
        # Default response
        return "This is a mock response."


class TestDomainMemoryStrategies(unittest.TestCase):
    """Test the domain-specific memory strategies in an end-to-end flow."""
    
    def setUp(self):
        """Set up test environment."""
        self.registry = ServiceRegistry.get_instance()
        self.llm_client = MockLLMClient()
        
    async def async_setUp(self):
        """Async setup tasks."""
        # Any async initialization can go here
        pass
        
    async def test_customer_support_memory_flow(self):
        """Test the complete memory flow for a customer support agent."""
        # 1. Build agent with customer support strategy
        agent_config = (AgentBuilder(registry=self.registry)
            .create(
                name="TestCustomerSupportAgent", 
                role="Customer support representative", 
                instruction_template="You are a helpful customer support representative."
            )
            .with_model("gpt-4")
            .with_memory_importance_strategy(
                "customer_support",
                action_keywords=["order", "refund", "urgent", "issue", "problem"]
            )
            .with_memory_thresholds(long_term=0.7, kg=0.8)
            .build())
            
        # 2. Create memory manager with the same strategy (normally this would be handled by agent creation)
        strategy = ImportanceStrategyFactory.create_strategy("customer_support")
        memory_manager = ConversationMemoryManager(
            importance_strategy=strategy,
            memory_thresholds={"long_term": 0.7, "kg": 0.8}
        )
        
        # 3. Process test messages with varying importance
        low_importance_message = Message(
            role="user",
            content="What time does your store close today?"
        )
        medium_importance_message = Message(
            role="user", 
            content="I have a question about my recent purchase."
        )
        high_importance_message = Message(
            role="user",
            content="My order #12345 is damaged and I need an urgent refund!"
        )
        
        # 4. Add messages to memory
        await memory_manager.add_message(low_importance_message)
        await memory_manager.add_message(medium_importance_message)
        await memory_manager.add_message(high_importance_message)
        
        # 5. Retrieve all messages from working memory
        all_messages = memory_manager.get_messages()
        self.assertEqual(len(all_messages), 3, "All messages should be in working memory")
        
        # 6. Search for "urgent" in long-term memory (only high importance should be there)
        urgent_results = await memory_manager.search_conversation("urgent")
        self.assertEqual(len(urgent_results), 1, "Only high importance message should be in long-term memory")
        self.assertIn("order #12345", urgent_results[0].content, 
                      "The high importance message should be stored in long-term memory")
        
        # 7. Run memory consolidation
        await memory_manager.consolidate()
        
        # 8. Verify all messages are still accessible in working memory
        all_messages_after = memory_manager.get_messages()
        self.assertEqual(len(all_messages_after), 3, "All messages should still be in working memory after consolidation")
    
    async def test_educational_memory_flow(self):
        """Test the complete memory flow for an educational agent."""
        # 1. Create educational strategy
        strategy = ImportanceStrategyFactory.create_strategy(
            "educational",
            subjects=["physics", "mathematics"],
            learning_level="advanced"
        )
        
        # 2. Create memory manager with educational strategy
        memory_manager = ConversationMemoryManager(
            importance_strategy=strategy,
            memory_thresholds={"long_term": 0.7, "kg": 0.8}
        )
        
        # 3. Process test messages with varying importance
        low_importance_message = Message(
            role="assistant",
            content="Let's schedule our next session for tomorrow."
        )
        medium_importance_message = Message(
            role="assistant",
            content="In physics, acceleration is the rate of change of velocity over time."
        )
        high_importance_message = Message(
            role="assistant",
            content="The principle of conservation of energy states that energy cannot be created or destroyed, only transformed from one form to another. This is a fundamental law of physics."
        )
        
        # 4. Add messages to memory
        await memory_manager.add_message(low_importance_message)
        await memory_manager.add_message(medium_importance_message)
        await memory_manager.add_message(high_importance_message)
        
        # 5. Search for "energy" in long-term memory (only high importance should be there)
        energy_results = await memory_manager.search_conversation("energy")
        self.assertGreaterEqual(len(energy_results), 1, "High importance message should be in long-term memory")
        found_principle = False
        for msg in energy_results:
            if "principle of conservation" in msg.content:
                found_principle = True
                break
        self.assertTrue(found_principle, "The principle message should be stored in long-term memory")
        
        # 6. Run memory consolidation
        await memory_manager.consolidate()
    
    async def test_medical_memory_flow(self):
        """Test the complete memory flow for a medical assistant agent."""
        # 1. Create medical strategy
        strategy = ImportanceStrategyFactory.create_strategy(
            "medical",
            medical_terms=["diabetes", "hypertension", "asthma"],
            severity_terms=["severe", "critical", "emergency"]
        )
        
        # 2. Create memory manager with medical strategy
        memory_manager = ConversationMemoryManager(
            importance_strategy=strategy,
            memory_thresholds={"long_term": 0.7, "kg": 0.8}
        )
        
        # 3. Process test messages with varying importance
        low_importance_message = Message(
            role="assistant",
            content="Your next check-up is scheduled for next month."
        )
        medium_importance_message = Message(
            role="assistant",
            content="Your blood pressure reading is 135/85, which is slightly elevated."
        )
        high_importance_message = Message(
            role="assistant",
            content="If you experience severe dizziness or chest pain, seek emergency care immediately."
        )
        
        # 4. Add messages to memory
        await memory_manager.add_message(low_importance_message)
        await memory_manager.add_message(medium_importance_message)
        await memory_manager.add_message(high_importance_message)
        
        # 5. Search for "emergency" in long-term memory
        emergency_results = await memory_manager.search_conversation("emergency")
        self.assertGreaterEqual(len(emergency_results), 1, "High importance message should be in long-term memory")
        found_emergency = False
        for msg in emergency_results:
            if "seek emergency care" in msg.content:
                found_emergency = True
                break
        self.assertTrue(found_emergency, "The emergency message should be stored in long-term memory")
    
    async def test_hybrid_strategy_flow(self):
        """Test the memory flow with a hybrid domain strategy."""
        # 1. Create hybrid domain strategy
        strategy = ImportanceStrategyFactory.create_strategy(
            "hybrid_educational",
            llm_client=self.llm_client,
            subjects=["physics"],
            learning_level="advanced",
            domain_weight=0.7,
            llm_weight=0.3
        )
        
        # 2. Create memory manager with hybrid strategy
        memory_manager = ConversationMemoryManager(
            importance_strategy=strategy,
            memory_thresholds={"long_term": 0.7, "kg": 0.8}
        )
        
        # 3. Process test message that would get different scores from rule vs LLM
        hybrid_message = Message(
            role="assistant",
            content="For your upcoming physics exam, remember that the deadline for submitting your project is Friday."
        )
        
        # 4. Add message to memory
        await memory_manager.add_message(hybrid_message)
        
        # 5. Search for "deadline" in long-term memory
        # This should be stored in long-term memory because:
        # - Domain strategy sees "physics" (subject match) and "exam" (assessment)
        # - LLM strategy sees "deadline" which the mock rates highly
        deadline_results = await memory_manager.search_conversation("deadline")
        self.assertGreaterEqual(len(deadline_results), 1, "The deadline message should be in long-term memory")
        
    async def test_agent_builder_integration(self):
        """Test that the agent builder correctly configures memory strategies."""
        # 1. Build an agent with each strategy type
        customer_agent = (AgentBuilder(registry=self.registry)
            .create(
                name="CustomerAgent", 
                role="Support", 
                instruction_template="You are a support agent."
            )
            .with_memory_importance_strategy("customer_support")
            .build())
            
        educational_agent = (AgentBuilder(registry=self.registry)
            .create(
                name="EducationalAgent", 
                role="Teacher", 
                instruction_template="You are a teacher."
            )
            .with_memory_importance_strategy(
                "educational",
                subjects=["science"],
                learning_level="beginner"
            )
            .build())
            
        hybrid_agent = (AgentBuilder(registry=self.registry)
            .create(
                name="HybridAgent", 
                role="Assistant", 
                instruction_template="You are an assistant."
            )
            .with_memory_importance_strategy(
                "hybrid",
                llm_client=self.llm_client,
                rule_weight=0.6,
                llm_weight=0.4
            )
            .build())
        
        # 2. Verify the agents have the expected configurations
        self.assertEqual(customer_agent.name, "CustomerAgent", "Agent name should be set correctly")
        self.assertEqual(educational_agent.metadata.get("memory_type"), "conversation", 
                         "Memory type should default to conversation")
        
        # The rest would normally verify the agent's memory manager configuration
        # This depends on how Symphony exposes the memory manager in the agent
        # For example, if it's accessible via agent.memory_manager:
        #   self.assertIsInstance(agent._memory.importance_strategy, CustomerSupportStrategy)
        # But this would depend on the agent implementation details


def run_async_tests():
    """Run all async tests."""
    loop = asyncio.get_event_loop()
    
    test_instance = TestDomainMemoryStrategies()
    test_instance.setUp()
    
    # Run all async test methods
    loop.run_until_complete(test_instance.async_setUp())
    loop.run_until_complete(test_instance.test_customer_support_memory_flow())
    loop.run_until_complete(test_instance.test_educational_memory_flow())
    loop.run_until_complete(test_instance.test_medical_memory_flow())
    loop.run_until_complete(test_instance.test_hybrid_strategy_flow())
    loop.run_until_complete(test_instance.test_agent_builder_integration())


if __name__ == "__main__":
    run_async_tests()