"""Example demonstrating patterns in Symphony.

This example shows how to use the Symphony Patterns Library
to implement common agent interaction patterns.
"""

import asyncio
import json
from symphony.api import Symphony
from symphony.agents.config import AgentConfig


async def run_reasoning_patterns():
    """Demonstrate reasoning patterns."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register a simple agent
    agent_config = AgentConfig(
        name="reasoner",
        description="An agent that can perform reasoning",
        model="gpt-4-turbo"
    )
    agent_id = await symphony.agents.create_agent(agent_config)
    
    # Use the chain of thought pattern
    print("Using Chain of Thought Pattern:")
    result = await symphony.patterns.apply_reasoning_pattern(
        "chain_of_thought",
        "Solve the following problem step by step: If a triangle has sides of length 3, 4, and 5, what is its area?",
        config={"agent_roles": {"reasoner": agent_id}}
    )
    
    print(f"Chain of Thought Result: {result.get('response')}\n")
    
    # Use the step back pattern
    print("Using Step Back Pattern:")
    result = await symphony.patterns.apply_reasoning_pattern(
        "step_back",
        "What will happen to global sea levels if all the ice at the poles melts?",
        config={"agent_roles": {"reasoner": agent_id}}
    )
    
    print(f"Step Back Result: {result.get('response')}\n")


async def run_verification_patterns():
    """Demonstrate verification patterns."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register agents
    primary_config = AgentConfig(
        name="writer",
        description="An agent that generates content",
        model="gpt-4-turbo"
    )
    primary_id = await symphony.agents.create_agent(primary_config)
    
    critic_config = AgentConfig(
        name="critic",
        description="An agent that critiques content",
        model="gpt-4-turbo"
    )
    critic_id = await symphony.agents.create_agent(critic_config)
    
    # Use the critic review pattern
    print("Using Critic Review Pattern:")
    result = await symphony.patterns.apply_verification_pattern(
        "critic_review",
        "Climate change is a significant global challenge requiring immediate action. We must reduce carbon emissions, transition to renewable energy, and implement sustainable practices.",
        criteria=["Accuracy", "Completeness", "Balance"],
        config={
            "agent_roles": {
                "creator": primary_id,
                "critic": critic_id,
                "reviser": primary_id
            }
        }
    )
    
    print(f"Original Content: {result.get('original_content')}")
    print(f"Critique: {result.get('critique')}")
    print(f"Revised Content: {result.get('revised_content')}\n")
    
    # Use the self-consistency pattern
    print("Using Self-Consistency Pattern:")
    result = await symphony.patterns.apply_verification_pattern(
        "self_consistency",
        "What is the capital of France?",
        config={
            "agent_roles": {"agent": primary_id},
            "num_samples": 3
        }
    )
    
    print(f"Self-Consistency Results:")
    for i, response in enumerate(result.get("responses", [])):
        print(f"  Sample {i+1}: {response}")
    print(f"  Final Answer: {result.get('final_answer')}\n")


async def run_multi_agent_patterns():
    """Demonstrate multi-agent patterns."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register expert agents
    expert_configs = [
        AgentConfig(
            name="financial_expert",
            description="An expert in financial analysis",
            model="gpt-4-turbo"
        ),
        AgentConfig(
            name="technical_expert",
            description="An expert in technical analysis",
            model="gpt-4-turbo"
        ),
        AgentConfig(
            name="market_expert",
            description="An expert in market trends",
            model="gpt-4-turbo"
        )
    ]
    
    expert_ids = []
    for config in expert_configs:
        expert_id = await symphony.agents.create_agent(config)
        expert_ids.append(expert_id)
    
    # Use the expert panel pattern
    print("Using Expert Panel Pattern:")
    result = await symphony.patterns.apply_multi_agent_pattern(
        "expert_panel",
        {
            "query": "Should I invest in renewable energy stocks in the current market?",
            "perspectives": [
                "Financial analysis: Consider ROI, risk factors, and investment timeline",
                "Technical analysis: Evaluate industry innovation and technological trends",
                "Market analysis: Assess market sentiment, regulations, and growth potential"
            ]
        },
        agents={
            "financial_expert": expert_ids[0],
            "technical_expert": expert_ids[1],
            "market_expert": expert_ids[2],
            "synthesizer": expert_ids[0]
        }
    )
    
    print(f"Expert Panel Query: {result.get('query')}")
    print("Expert Responses:")
    for i, (perspective, response) in enumerate(zip(result.get("perspectives", []), result.get("expert_responses", []))):
        print(f"  Expert {i+1} ({perspective.split(':')[0]}): {response[:100]}...")
    print(f"Synthesis: {result.get('synthesis')[:200]}...\n")


async def run_tool_usage_patterns():
    """Demonstrate tool usage patterns."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register an agent
    agent_config = AgentConfig(
        name="tool_user",
        description="An agent that uses tools",
        model="gpt-4-turbo"
    )
    agent_id = await symphony.agents.create_agent(agent_config)
    
    # Register some mock tools
    await symphony.tools.register_tool(
        name="search_tool",
        description="Search for information",
        function=lambda query: {"results": [f"Mock result for {query}"]}
    )
    
    await symphony.tools.register_tool(
        name="calculator",
        description="Perform calculations",
        function=lambda expression: {"result": eval(expression)}
    )
    
    # Use the multi-tool chain pattern
    print("Using Multi-Tool Chain Pattern:")
    result = await symphony.patterns.apply_tool_usage_pattern(
        "multi_tool_chain",
        "I need to calculate the area of a circle with radius 5",
        tools=[
            {
                "name": "calculator",
                "config": {},
                "input_mapping": {"expression": "math_expression"},
                "output_mapping": {"result": "area"}
            }
        ],
        config={
            "agent_roles": {"executor": agent_id},
            "metadata": {"math_expression": "3.14159 * 5 * 5"}
        }
    )
    
    print(f"Multi-Tool Chain Result: {result.get('final_result')}")
    
    # Use the verify-execute pattern
    print("\nUsing Verify-Execute Pattern:")
    result = await symphony.patterns.apply_tool_usage_pattern(
        "verify_execute",
        "Calculate 25 * 32",
        tools=[
            {
                "name": "calculator",
                "inputs": {"expression": "25 * 32"},
                "config": {}
            }
        ],
        config={
            "agent_roles": {
                "verifier": agent_id,
                "executor": agent_id
            }
        }
    )
    
    print(f"Verification Result: {result.get('verification_result')}")
    print(f"Execution Result: {result.get('execution_result')}")


async def run_learning_patterns():
    """Demonstrate learning patterns."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register an agent
    agent_config = AgentConfig(
        name="learner",
        description="An agent that can learn from examples",
        model="gpt-4-turbo"
    )
    agent_id = await symphony.agents.create_agent(agent_config)
    
    # Use the few-shot pattern
    print("Using Few-Shot Pattern:")
    result = await symphony.patterns.apply_learning_pattern(
        "few_shot",
        "The moon orbits the Earth at an average distance of 384,400 km.",
        examples=[
            {
                "input": "The Earth orbits the Sun at an average distance of 149.6 million km.",
                "output": "Distance between Earth and Sun: 149,600,000 km (149.6 million km)"
            },
            {
                "input": "Mars orbits the Sun at an average distance of 227.9 million km.",
                "output": "Distance between Mars and Sun: 227,900,000 km (227.9 million km)"
            }
        ],
        config={
            "agent_roles": {"performer": agent_id},
            "task": "Extract celestial distance measurements and format them consistently",
            "format_instructions": "Output the distance in both kilometers (with commas) and the original unit provided."
        }
    )
    
    print(f"Few-Shot Result: {result.get('result')}")
    
    # Use the reflection pattern
    print("\nUsing Reflection Pattern:")
    result = await symphony.patterns.apply_learning_pattern(
        "reflection",
        "Write a short paragraph explaining quantum computing to a 10-year-old",
        config={
            "agent_roles": {"performer": agent_id, "reflector": agent_id},
            "task": "Explain complex topics in simple terms",
            "criteria": [
                "Simplicity: Uses age-appropriate language and concepts",
                "Accuracy: Maintains factual correctness despite simplification",
                "Engagement: Captures interest and sparks curiosity",
                "Analogies: Uses helpful comparisons to familiar concepts"
            ]
        }
    )
    
    print("Initial Response:")
    print(result.get("initial_response", "")[:150] + "...")
    print("\nImproved Response:")
    print(result.get("final_response", "")[:150] + "...")


async def run_composition_example():
    """Demonstrate pattern composition."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register an agent
    agent_config = AgentConfig(
        name="composer",
        description="An agent for pattern composition",
        model="gpt-4-turbo"
    )
    agent_id = await symphony.agents.create_agent(agent_config)
    
    # First create individual patterns
    cot_pattern = symphony.patterns.create_pattern(
        "chain_of_thought",
        {"agent_roles": {"reasoner": agent_id}}
    )
    
    consistency_pattern = symphony.patterns.create_pattern(
        "self_consistency",
        {"agent_roles": {"agent": agent_id}, "num_samples": 2}
    )
    
    # Create sequential composition
    print("Using Sequential Pattern Composition:")
    # First reason step by step, then verify with self-consistency
    composition = symphony.patterns.compose_sequential(
        [cot_pattern, consistency_pattern],
        name="reason_then_verify"
    )
    
    result = await composition.run({
        "query": "If I have 12 apples and give 1/3 to my friend, then eat 2 myself, how many do I have left?"
    })
    
    print(f"Step 1 (Chain of Thought): {result.get('results')[0].get('response')}")
    print(f"Step 2 (Self Consistency): Final Answer = {result.get('results')[1].get('final_answer')}")


async def main():
    """Run all pattern examples."""
    await run_reasoning_patterns()
    await run_verification_patterns()
    await run_multi_agent_patterns()
    await run_tool_usage_patterns()
    await run_learning_patterns()
    await run_composition_example()


if __name__ == "__main__":
    asyncio.run(main())