"""Integration tests for Symphony patterns with OpenAI models.

These tests verify that patterns work correctly with real OpenAI GPT-4o models.
"""

import os
import asyncio
import pytest
from typing import Dict, Any, List
import json

from symphony.api import Symphony
from symphony.core.agent_config import AgentConfig
from symphony.patterns import register_patterns


@pytest.fixture
async def symphony_with_agent():
    """Create a Symphony instance with an agent."""
    # Set up Symphony
    symphony = Symphony()
    
    # Register patterns
    register_patterns(symphony.registry)
    
    # Get model from environment or use default
    model = os.environ.get("INTEGRATION_TEST_MODEL", "gpt-4o-mini")
    print(f"\n[INFO] Using model: {model}")
    
    # Create agent
    agent_config = await symphony.agents.create_agent(
        name="test_agent",
        role="reasoner",
        instruction_template="You are a helpful AI assistant that provides accurate, thoughtful responses.",
        model=model
    )
    
    # Save agent to get ID
    agent_id = await symphony.agents.save_agent(agent_config)
    print(f"[INFO] Created agent with ID: {agent_id}")
    
    # Return Symphony instance and agent ID
    return symphony, agent_id


def format_result(result):
    """Format result for better readability in test output."""
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    return str(result)


@pytest.mark.asyncio
async def test_chain_of_thought_pattern(symphony_with_agent):
    """Test the chain of thought pattern with GPT-4o."""
    symphony, agent_id = symphony_with_agent
    
    # Print test information
    print("\n" + "="*80)
    print("TESTING CHAIN OF THOUGHT PATTERN")
    print("="*80)
    
    # Test query requiring multi-step reasoning
    query = "If I have 12 apples and give 1/3 to my friend, then eat 2 myself, how many do I have left?"
    print(f"\nQuery: {query}")
    
    try:
        # Execute the chain of thought pattern
        result = await symphony.patterns.apply_reasoning_pattern(
            "chain_of_thought",
            query,
            config={"agent_roles": {"reasoner": agent_id}}
        )
        
        # Print the response for validation
        print("\nChain of Thought Pattern Result:")
        print(format_result(result))
        
        if isinstance(result, dict) and "result" in result:
            result_data = result["result"]
            if isinstance(result_data, dict):
                # Print the actual content
                if "response" in result_data:
                    print(f"\nResponse: {result_data['response']}")
                if "steps" in result_data and isinstance(result_data["steps"], list):
                    print("\nReasoning Steps:")
                    for i, step in enumerate(result_data["steps"]):
                        print(f"  Step {i+1}: {step}")
        
        # Basic validation
        assert result is not None, "Pattern should return a result"
        print("\n✅ Test passed: Chain of Thought pattern executed successfully")
        
        # Return for further analysis if needed
        return result
    except Exception as e:
        print(f"\n❌ Error executing pattern: {e}")
        raise


@pytest.mark.asyncio
async def test_reflection_pattern(symphony_with_agent):
    """Test the reflection pattern with GPT-4o."""
    symphony, agent_id = symphony_with_agent
    
    # Print test information
    print("\n" + "="*80)
    print("TESTING REFLECTION PATTERN")
    print("="*80)
    
    # Execute the reflection pattern
    task = "Write a short paragraph explaining quantum computing to a 10-year-old"
    print(f"\nTask: {task}")
    
    try:
        # Execute the pattern
        result = await symphony.patterns.apply_learning_pattern(
            "reflection",
            task,
            config={
                "agent_roles": {"performer": agent_id, "reflector": agent_id},
                "task": "Explain complex topics in simple terms",
                "criteria": [
                    "Simplicity: Uses age-appropriate language and concepts",
                    "Accuracy: Maintains factual correctness despite simplification"
                ],
                "metadata": {
                    "prompt_style": "creative"  # Use the creative prompt style
                }
            }
        )
        
        # Access nested result
        result_data = None
        if isinstance(result, dict) and "result" in result:
            result_data = result["result"]
        
        # Print results for validation
        print("\nReflection Pattern Result:")
        if result_data and isinstance(result_data, dict):
            if "initial_response" in result_data:
                print("\nINITIAL RESPONSE:")
                print(result_data["initial_response"][:250] + "..." if len(result_data["initial_response"]) > 250 else result_data["initial_response"])
            if "reflection" in result_data:
                print("\nREFLECTION:")
                print(result_data["reflection"][:250] + "..." if len(result_data["reflection"]) > 250 else result_data["reflection"])
            if "final_response" in result_data:
                print("\nFINAL RESPONSE:")
                print(result_data["final_response"][:250] + "..." if len(result_data["final_response"]) > 250 else result_data["final_response"])
        else:
            print(format_result(result))
        
        # Basic validation
        assert result is not None, "Pattern should return a result"
        print("\n✅ Test passed: Reflection pattern executed successfully")
        
        # Return for further analysis if needed
        return result
    except Exception as e:
        print(f"\n❌ Error executing pattern: {e}")
        raise


@pytest.mark.asyncio
async def test_self_consistency_pattern(symphony_with_agent):
    """Test the self-consistency pattern with GPT-4o."""
    symphony, agent_id = symphony_with_agent
    
    # Print test information
    print("\n" + "="*80)
    print("TESTING SELF-CONSISTENCY PATTERN")
    print("="*80)
    
    # Test query with multiple possible interpretations
    query = "What is the capital of Georgia?"
    print(f"\nQuery: {query}")
    
    try:
        # Execute the self-consistency pattern
        result = await symphony.patterns.apply_verification_pattern(
            "self_consistency",
            query,
            config={
                "agent_roles": {"reasoner": agent_id},
                "metadata": {
                    "num_samples": 3,
                    "threshold": 0.7,
                    "prompt_style": "detailed"  # Use the detailed prompt style
                }
            }
        )
        
        # Print the response for validation
        print("\nSelf-Consistency Pattern Result:")
        print(format_result(result))
        
        if isinstance(result, dict) and "result" in result:
            result_data = result["result"]
            if isinstance(result_data, dict):
                if "samples" in result_data:
                    print("\nSamples Generated:")
                    for i, sample in enumerate(result_data["samples"]):
                        print(f"  Sample {i+1}: {sample[:100]}...")
                if "top_answer" in result_data:
                    print(f"\nTop Answer: {result_data['top_answer']}")
                if "consistency_score" in result_data:
                    print(f"Consistency Score: {result_data['consistency_score']}")
        
        # Basic validation
        assert result is not None, "Pattern should return a result"
        print("\n✅ Test passed: Self-Consistency pattern executed successfully")
        
        # Return for further analysis if needed
        return result
    except Exception as e:
        print(f"\n❌ Error executing pattern: {e}")
        raise


@pytest.mark.asyncio
async def test_expert_panel_pattern(symphony_with_agent):
    """Test the expert panel pattern with GPT-4o."""
    symphony, agent_id = symphony_with_agent
    
    # Print test information
    print("\n" + "="*80)
    print("TESTING EXPERT PANEL PATTERN")
    print("="*80)
    
    # Test query for expert panel
    query = "What are the environmental, economic, and social implications of transitioning to renewable energy?"
    perspectives = ["environmental scientist", "economist", "social policy expert"]
    print(f"\nQuery: {query}")
    print(f"Perspectives: {', '.join(perspectives)}")
    
    try:
        # Execute the expert panel pattern
        result = await symphony.patterns.apply_multi_agent_pattern(
            "expert_panel",
            query,
            config={
                "agent_roles": {"moderator": agent_id, "synthesizer": agent_id},
                "metadata": {
                    "perspectives": perspectives,
                    "prompt_style": "academic"  # Use the academic prompt style
                }
            }
        )
        
        # Print the response for validation
        print("\nExpert Panel Pattern Result:")
        if isinstance(result, dict) and "result" in result:
            result_data = result["result"]
            if isinstance(result_data, dict):
                if "expert_opinions" in result_data:
                    print("\nExpert Opinions:")
                    for perspective, opinion in result_data["expert_opinions"].items():
                        print(f"\n--- {perspective.upper()} ---")
                        print(f"{opinion[:150]}...")
                if "synthesis" in result_data:
                    print("\nSynthesis:")
                    print(f"{result_data['synthesis'][:250]}...")
        
        # Basic validation
        assert result is not None, "Pattern should return a result"
        print("\n✅ Test passed: Expert Panel pattern executed successfully")
        
        # Return for further analysis if needed
        return result
    except Exception as e:
        print(f"\n❌ Error executing pattern: {e}")
        raise


@pytest.mark.asyncio
async def test_few_shot_pattern(symphony_with_agent):
    """Test the few-shot learning pattern with GPT-4o."""
    symphony, agent_id = symphony_with_agent
    
    # Print test information
    print("\n" + "="*80)
    print("TESTING FEW-SHOT LEARNING PATTERN")
    print("="*80)
    
    # Test summarization task
    task = "Summarize the following text in one sentence"
    query = "The human brain has approximately 86 billion neurons, which are connected by trillions of synapses. Each neuron can fire 5-50 times per second. The brain consumes about 20% of the body's energy despite being only 2% of its weight. The brain's structure includes the cerebrum, cerebellum, and brainstem, each responsible for different functions ranging from conscious thought to involuntary processes."
    
    # Examples for the few-shot pattern
    examples = [
        {
            "input": "The process of photosynthesis in plants involves capturing light energy to convert carbon dioxide and water into glucose and oxygen. This process takes place in the chloroplasts, primarily in the leaves. The glucose produced is used as energy for the plant's growth and functioning.",
            "output": "Photosynthesis is the process where plants use light energy to convert CO2 and water into glucose and oxygen in their chloroplasts, providing energy for plant growth."
        },
        {
            "input": "Machine learning is a subset of artificial intelligence that focuses on developing systems that learn from data. It involves algorithms that improve automatically through experience. Common applications include image recognition, recommendation systems, and natural language processing.",
            "output": "Machine learning is an AI subset where systems use algorithms to learn from data and improve automatically, powering applications like image recognition and NLP."
        }
    ]
    
    print(f"\nTask: {task}")
    print(f"Query: {query[:100]}...")
    
    try:
        # Execute the few-shot pattern
        result = await symphony.patterns.apply_learning_pattern(
            "few_shot",
            query,
            config={
                "agent_roles": {"performer": agent_id},
                "metadata": {
                    "prompt_style": "academic",  # Use the academic prompt style
                    "examples": examples,
                    "task": task
                }
            }
        )
        
        # Print the response for validation
        print("\nFew-Shot Learning Pattern Result:")
        if isinstance(result, dict) and "result" in result:
            response = result["result"]
            print(f"\nResponse: {response}")
        else:
            print(format_result(result))
        
        # Basic validation
        assert result is not None, "Pattern should return a result"
        print("\n✅ Test passed: Few-Shot Learning pattern executed successfully")
        
        # Return for further analysis if needed
        return result
    except Exception as e:
        print(f"\n❌ Error executing pattern: {e}")
        raise


@pytest.mark.asyncio
async def test_patterns_batch(symphony_with_agent):
    """Run all pattern tests in a batch for comprehensive validation."""
    print("\n" + "="*80)
    print("RUNNING COMPREHENSIVE PATTERN VALIDATION")
    print("="*80)
    
    results = {}
    
    try:
        # Run Chain of Thought pattern test
        results["chain_of_thought"] = await test_chain_of_thought_pattern(symphony_with_agent)
        
        # Run Reflection pattern test
        results["reflection"] = await test_reflection_pattern(symphony_with_agent)
        
        # Run Self-Consistency pattern test
        results["self_consistency"] = await test_self_consistency_pattern(symphony_with_agent)
        
        # Run Expert Panel pattern test
        results["expert_panel"] = await test_expert_panel_pattern(symphony_with_agent)
        
        # Run Few-Shot Learning pattern test
        results["few_shot"] = await test_few_shot_pattern(symphony_with_agent)
        
        # Print summary
        successful_patterns = [name for name, result in results.items() if result is not None]
        print("\n" + "="*80)
        print(f"SUMMARY: Successfully tested {len(successful_patterns)}/{len(results)} patterns")
        print(f"Successful patterns: {', '.join(successful_patterns)}")
        print("="*80)
        
        return results
    except Exception as e:
        print(f"\n❌ Error during batch testing: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(pytest.main(["-xvs", "tests/integration/test_patterns_integration.py::test_patterns_batch"]))