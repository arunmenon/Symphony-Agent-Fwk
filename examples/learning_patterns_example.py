"""Example demonstrating learning patterns in Symphony.

This example shows how to use learning patterns to improve
agent performance through examples and reflection.
"""

import asyncio
import json
from symphony.api import Symphony
from symphony.agents.config import AgentConfig


async def run_few_shot_learning():
    """Demonstrate the few-shot learning pattern."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register an agent
    agent_config = AgentConfig(
        name="learner",
        description="An agent that can learn from examples",
        model="gpt-4-turbo"
    )
    agent_id = await symphony.agents.create_agent(agent_config)
    
    # Define examples for sentiment classification
    sentiment_examples = [
        {
            "input": "The product exceeded all my expectations. I'm extremely satisfied with my purchase.",
            "output": "Positive (5/5)"
        },
        {
            "input": "The service was good, but there's definitely room for improvement.",
            "output": "Neutral (3/5)"
        },
        {
            "input": "I'm very disappointed with the quality. It broke after just a few days of use.",
            "output": "Negative (1/5)"
        }
    ]
    
    # Define format instructions
    format_instructions = """
    Please analyze the sentiment of the input text and provide a rating:
    - Positive (5/5): Very positive sentiment
    - Positive (4/5): Moderately positive sentiment
    - Neutral (3/5): Balanced or neutral sentiment
    - Negative (2/5): Moderately negative sentiment
    - Negative (1/5): Very negative sentiment
    
    Include a brief explanation of your rating.
    """
    
    # Execute the pattern
    print("Using Few-Shot Learning Pattern:")
    result = await symphony.patterns.apply_learning_pattern(
        "few_shot",
        "I ordered a new laptop which arrived on time, but the packaging was damaged. Thankfully, the laptop itself works fine.",
        examples=sentiment_examples,
        config={
            "agent_roles": {"performer": agent_id},
            "task": "Analyze the sentiment of customer reviews",
            "format_instructions": format_instructions
        }
    )
    
    print(f"Few-Shot Learning Result: {result.get('result')}")
    
    # Try with standard examples using builder approach
    print("\nUsing Standard Examples with Builder:")
    result = await symphony.build_pattern() \
        .create("few_shot") \
        .with_agent("performer", agent_id) \
        .with_input("task", "Summarize the following text") \
        .with_input("query", "Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by animals including humans. AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.") \
        .with_config("task_type", "summarization") \
        .execute()
    
    print(f"Summarization Result: {result.get('result')}")


async def run_reflection_pattern():
    """Demonstrate the reflection pattern."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register agents
    performer_config = AgentConfig(
        name="task_performer",
        description="An agent that performs tasks",
        model="gpt-4-turbo"
    )
    performer_id = await symphony.agents.create_agent(performer_config)
    
    reflector_config = AgentConfig(
        name="reflector",
        description="An agent that reflects on and improves responses",
        model="gpt-4-turbo"
    )
    reflector_id = await symphony.agents.create_agent(reflector_config)
    
    # Define criteria
    criteria = [
        "Accuracy: Is the information factually correct?",
        "Completeness: Does it cover all important aspects?",
        "Clarity: Is it easy to understand?",
        "Engagement: Is it interesting and engaging?"
    ]
    
    # Execute the pattern
    print("\nUsing Reflection Pattern:")
    result = await symphony.patterns.apply_learning_pattern(
        "reflection",
        "Explain how neural networks work",
        config={
            "agent_roles": {
                "performer": performer_id,
                "reflector": reflector_id
            },
            "task": "Explain technical concepts to a beginner",
            "criteria": criteria
        }
    )
    
    print("Initial Response:")
    print(result.get("initial_response", "")[:200] + "...")
    print("\nReflection Highlights:")
    print(result.get("reflection", "")[:200] + "...")
    print("\nImproved Response:")
    print(result.get("final_response", "")[:200] + "...")
    print("\nImprovements Made:")
    print(result.get("improvement", "")[:200] + "...")


async def run_iterative_reflection():
    """Demonstrate the iterative reflection pattern."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register an agent
    agent_config = AgentConfig(
        name="essay_writer",
        description="An agent that writes and improves essays",
        model="gpt-4-turbo"
    )
    agent_id = await symphony.agents.create_agent(agent_config)
    
    # Define criteria
    criteria = [
        "Thesis clarity: Is the main argument clear?",
        "Evidence: Are claims supported with evidence?",
        "Organization: Is the structure logical?",
        "Language: Is the language precise and effective?",
        "Conclusion: Does it effectively tie the arguments together?"
    ]
    
    # Execute the pattern
    print("\nUsing Iterative Reflection Pattern:")
    result = await symphony.patterns.apply_learning_pattern(
        "iterative_reflection",
        "Write a short essay about the impact of artificial intelligence on society",
        config={
            "agent_roles": {"performer": agent_id},
            "task": "Write a persuasive essay",
            "criteria": criteria,
            "iterations": 3
        }
    )
    
    # Display improvement trace
    improvement_trace = result.get("improvement_trace", [])
    
    print(f"Completed {len(improvement_trace)} iterations of improvement")
    for i, trace in enumerate(improvement_trace):
        print(f"\nIteration {i+1} to {i+2} improvements:")
        print(trace.get("summary", "")[:200] + "...")
    
    print("\nFinal Essay (after iterations):")
    print(result.get("final_response", "")[:300] + "...")


async def main():
    """Run all pattern examples."""
    await run_few_shot_learning()
    await run_reflection_pattern()
    await run_iterative_reflection()


if __name__ == "__main__":
    asyncio.run(main())