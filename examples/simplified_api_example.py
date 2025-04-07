"""
Simplified Symphony API Example

This example demonstrates the revised Symphony API with minimal cognitive load
and progressive disclosure of complexity.
"""

import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("symphony_example")

# Import Symphony with clean, simple API
from symphony import Symphony

# Custom tool example - simple function, no complex plugin architecture
def sentiment_analyzer(text):
    """Analyze sentiment of text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with sentiment analysis
    """
    # Simplified example - in reality would use NLP
    positive_words = ["good", "great", "excellent", "amazing", "happy"]
    negative_words = ["bad", "terrible", "awful", "disappointed", "sad"]
    
    text = text.lower()
    positive_count = sum(word in text for word in positive_words)
    negative_count = sum(word in text for word in negative_words)
    
    if positive_count > negative_count:
        sentiment = "positive"
        score = 0.5 + (positive_count - negative_count) * 0.1
    elif negative_count > positive_count:
        sentiment = "negative"
        score = 0.5 - (negative_count - positive_count) * 0.1
    else:
        sentiment = "neutral"
        score = 0.5
    
    return {
        "sentiment": sentiment,
        "confidence": min(max(score, 0.0), 1.0),
        "positive_aspects": positive_count,
        "negative_aspects": negative_count
    }


async def run_example():
    # 1. Initialize Symphony - minimal configuration, works out of the box
    symphony = Symphony()
    
    # 2. Create a simple agent - no plugins or complex configuration
    basic_agent = symphony.create_agent(
        name="BasicAssistant",
        description="A helpful assistant that answers questions"
    )
    
    # 3. Execute a basic task - clean, simple API
    logger.info("Executing basic task...")
    basic_result = await basic_agent.execute(
        "What are the three laws of robotics?"
    )
    logger.info(f"Basic result: {basic_result}")
    
    # 4. Progressive enhancement - add capabilities only when needed
    logger.info("Creating enhanced agent with progressive configuration...")
    enhanced_agent = symphony.create_agent(
        name="EnhancedAssistant",
        description="An assistant with enhanced capabilities"
    )
    
    # 5. Add memory - optional enhancement
    enhanced_agent.add_memory(memory_type="conversation")
    
    # 6. Register a custom tool - simple function registration, no plugins
    symphony.register_tool("sentiment_analyzer", sentiment_analyzer)
    
    # 7. Use the agent with the custom tool
    logger.info("Executing task with custom tool...")
    enhanced_result = await enhanced_agent.execute(
        "Analyze the sentiment of: I really enjoyed this product, it's amazing!",
        use_tools=["sentiment_analyzer"]
    )
    logger.info(f"Enhanced result: {enhanced_result}")
    
    # 8. Domain specialization - use presets instead of plugins
    logger.info("Creating domain-specialized agent...")
    legal_agent = symphony.create_agent(
        name="LegalAssistant",
        preset="legal"  # Pre-configured for legal domain - no plugins needed
    )
    
    # 9. Execute with domain specialization
    logger.info("Executing domain-specific task...")
    legal_result = await legal_agent.execute(
        "Summarize the key points in a non-disclosure agreement"
    )
    logger.info(f"Legal domain result: {legal_result}")
    
    # 10. Create a multi-agent workflow - still clean API with no plugins
    logger.info("Creating and executing a multi-agent workflow...")
    workflow = symphony.create_workflow(
        name="ResearchWorkflow",
        description="Research and analyze information"
    )
    
    # Add steps to the workflow
    workflow.add_step(
        name="research",
        agent=basic_agent,
        input="Research quantum computing advances in 2023"
    )
    
    workflow.add_step(
        name="analyze",
        agent=enhanced_agent,
        input_from="research",
        tools=["sentiment_analyzer"]
    )
    
    # Execute workflow
    workflow_result = await symphony.execute_workflow(workflow)
    logger.info(f"Workflow result: {workflow_result}")
    
    logger.info("Symphony example completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_example())