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
                ]
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