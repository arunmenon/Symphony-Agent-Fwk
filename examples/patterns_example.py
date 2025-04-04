"""Example demonstrating the Symphony Patterns Library.

This example demonstrates how to use the Symphony Patterns Library
to leverage advanced agent interaction patterns.
"""

import asyncio
import os
from typing import Dict, Any

from symphony import Symphony


async def chain_of_thought_example():
    """Demonstrate the Chain of Thought pattern."""
    print("\n=== Chain of Thought Pattern Example ===")
    
    # Initialize Symphony
    symphony = Symphony()
    await symphony.setup()
    
    # Create an agent for our patterns
    agent = await symphony.agents.create_agent(
        name="ReasoningAgent",
        role="Mathematical Reasoner",
        instruction_template="You are an expert at mathematical reasoning and problem-solving.",
        capabilities={"expertise": ["mathematics", "logic", "reasoning"]}
    )
    agent_id = await symphony.agents.save_agent(agent)
    
    # Using the facade approach
    print("Using Pattern Facade:")
    result = await symphony.patterns.apply_reasoning_pattern(
        "chain_of_thought",
        "Solve the following problem step by step: If a triangle has sides of length 3, 4, and 5, what is its area?",
        config={"agent_roles": {"reasoner": agent_id}}
    )
    
    print("\nChain of Thought solution:")
    print(result["response"])
    
    # Using the builder approach
    print("\nUsing Pattern Builder:")
    result = await symphony.build_pattern() \
        .create("chain_of_thought") \
        .with_agent("reasoner", agent_id) \
        .with_query("Find the area of a rectangle with length 8.5 cm and width 6.2 cm. Show your reasoning step by step.") \
        .execute()
    
    print("\nChain of Thought solution:")
    print(result["response"])


async def step_back_reasoning_example():
    """Demonstrate the Step Back pattern."""
    print("\n=== Step Back Reasoning Pattern Example ===")
    
    # Initialize Symphony
    symphony = Symphony()
    await symphony.setup()
    
    # Create an agent for our patterns
    agent = await symphony.agents.create_agent(
        name="StrategicThinker",
        role="Strategic Thinker",
        instruction_template="You excel at strategic thinking and approaching problems from a high level.",
        capabilities={"expertise": ["strategy", "planning", "systems thinking"]}
    )
    agent_id = await symphony.agents.save_agent(agent)
    
    # Using the builder approach
    result = await symphony.build_pattern() \
        .create("step_back") \
        .with_agent("reasoner", agent_id) \
        .with_query("How should we approach designing a new social media platform that prioritizes user well-being?") \
        .execute()
    
    print("\nStrategic Analysis:")
    print(result["strategic_analysis"])
    
    print("\nDetailed Solution:")
    print(result["detailed_solution"])


async def critic_review_example():
    """Demonstrate the Critic Review Revise pattern."""
    print("\n=== Critic Review Revise Pattern Example ===")
    
    # Initialize Symphony
    symphony = Symphony()
    await symphony.setup()
    
    # Create agents for different roles
    creator = await symphony.agents.create_agent(
        name="ContentCreator",
        role="Content Creator",
        instruction_template="You create original content based on provided topics.",
        capabilities={"expertise": ["writing", "content creation"]}
    )
    
    critic = await symphony.agents.create_agent(
        name="ContentCritic",
        role="Content Critic",
        instruction_template="You analyze content critically and identify areas for improvement.",
        capabilities={"expertise": ["criticism", "analysis", "evaluation"]}
    )
    
    reviser = await symphony.agents.create_agent(
        name="ContentReviser",
        role="Content Reviser",
        instruction_template="You revise content based on critical feedback to improve it.",
        capabilities={"expertise": ["revision", "editing", "improvement"]}
    )
    
    creator_id = await symphony.agents.save_agent(creator)
    critic_id = await symphony.agents.save_agent(critic)
    reviser_id = await symphony.agents.save_agent(reviser)
    
    # Using the builder approach with content that needs verification
    result = await symphony.build_pattern() \
        .create("critic_review_revise") \
        .with_agent("creator", creator_id) \
        .with_agent("critic", critic_id) \
        .with_agent("reviser", reviser_id) \
        .with_content("Bitcoin was invented in 2004 by Microsoft as a digital currency. It has since become the most valuable commodity in the world.") \
        .with_input("criteria", ["factual_accuracy", "clarity", "completeness"]) \
        .execute()
    
    print("\nOriginal Content:")
    print(result["initial_content"])
    
    print("\nCriticism:")
    print(result["criticism"])
    
    print("\nRevised Content:")
    print(result["revised_content"])
    
    # Let's see what issues were identified
    print("\nIssues Identified:")
    for issue in result["issues"]:
        print(f"- {issue}")


async def expert_panel_example():
    """Demonstrate the Expert Panel pattern."""
    print("\n=== Expert Panel Pattern Example ===")
    
    # Initialize Symphony
    symphony = Symphony()
    await symphony.setup()
    
    # Create agents for the panel
    generalist = await symphony.agents.create_agent(
        name="GeneralistAgent",
        role="Generalist",
        instruction_template="You have broad knowledge across many domains.",
        capabilities={"expertise": ["general knowledge", "synthesis", "analysis"]}
    )
    
    # Save agent
    generalist_id = await symphony.agents.save_agent(generalist)
    
    # Using the builder approach
    result = await symphony.build_pattern() \
        .create("expert_panel") \
        .with_config("perspectives", ["economic", "technological", "political", "social"]) \
        .with_agent("synthesizer", generalist_id) \
        .with_query("What are the most promising approaches to mitigate climate change in the next decade?") \
        .execute()
    
    # Display expert opinions
    print("\nExpert Opinions:")
    for perspective, opinion in result["expert_opinions"].items():
        print(f"\n=== {perspective.upper()} PERSPECTIVE ===")
        print(opinion[:300] + "..." if len(opinion) > 300 else opinion)
    
    # Display synthesis
    print("\n=== SYNTHESIS ===")
    print(result["synthesis"][:500] + "..." if len(result["synthesis"]) > 500 else result["synthesis"])


async def main():
    """Run patterns library examples."""
    print("Symphony Patterns Library Examples")
    print("=================================")
    print("\nThis example demonstrates various patterns from the Symphony Patterns Library,")
    print("showing how they can be used to implement sophisticated agent behaviors.")
    
    # Allow selecting specific examples or run all
    examples = {
        "1": ("Chain of Thought Pattern", chain_of_thought_example),
        "2": ("Step Back Reasoning Pattern", step_back_reasoning_example),
        "3": ("Critic Review Revise Pattern", critic_review_example),
        "4": ("Expert Panel Pattern", expert_panel_example),
        "all": ("All Examples", None)
    }
    
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"{key}: {name}")
    
    choice = input("\nEnter example number to run (or 'all' for all examples): ").strip()
    
    if choice in examples:
        if choice == "all":
            # Run all examples
            await chain_of_thought_example()
            await step_back_reasoning_example()
            await critic_review_example()
            await expert_panel_example()
        else:
            # Run selected example
            await examples[choice][1]()
    else:
        print(f"Invalid choice: {choice}")
        print("Running all examples...")
        await chain_of_thought_example()
        await step_back_reasoning_example()
        await critic_review_example()
        await expert_panel_example()


if __name__ == "__main__":
    asyncio.run(main())