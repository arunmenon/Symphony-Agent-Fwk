"""
Simple Workflow Example

This example demonstrates using the simplified Symphony API to create 
and execute multi-agent workflows with minimal cognitive load.
"""

import asyncio
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("symphony_workflow")

# Import from the simplified API
from symphony.simple_api import Symphony


# Custom research tool
def web_search(query: str) -> Dict[str, Any]:
    """Simulate web search results.
    
    Args:
        query: Search query
        
    Returns:
        Search results
    """
    # This is a simulation - would use actual search API in reality
    if "quantum computing" in query.lower():
        return {
            "results": [
                {
                    "title": "Advancements in Quantum Computing 2023",
                    "snippet": "This year saw major breakthroughs in quantum error correction...",
                    "url": "https://example.com/quantum-advances-2023"
                },
                {
                    "title": "Quantum Supremacy Developments",
                    "snippet": "Recent experiments have demonstrated quantum advantage in...",
                    "url": "https://example.com/quantum-supremacy"
                }
            ],
            "count": 2
        }
    else:
        return {
            "results": [
                {
                    "title": f"Results for {query}",
                    "snippet": "General search results would appear here...",
                    "url": "https://example.com/search"
                }
            ],
            "count": 1
        }


# Custom sentiment analysis tool
def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Analyze sentiment of text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Sentiment analysis results
    """
    # Simplified sentiment analysis - would use ML in reality
    positive_words = ["breakthrough", "advancement", "success", "impressive", "solved"]
    negative_words = ["challenge", "problem", "difficulty", "hurdle", "limitation"]
    
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


# Custom summarization tool
def summarize_text(text: str, max_length: int = 100) -> Dict[str, Any]:
    """Summarize text to specified length.
    
    Args:
        text: Text to summarize
        max_length: Maximum length of summary
        
    Returns:
        Summarized text
    """
    # Simplified summarization - would use NLP in reality
    sentences = text.split('.')
    if len(sentences) <= 2:
        summary = text
    else:
        # Just take the first two sentences as a simple summary
        summary = '. '.join(sentences[:2]) + '.'
    
    # Truncate if needed
    if len(summary) > max_length:
        summary = summary[:max_length] + '...'
    
    return {
        "summary": summary,
        "original_length": len(text),
        "summary_length": len(summary)
    }


async def run_workflow_example():
    """Run the Symphony simplified workflow example."""
    logger.info("Starting Symphony simplified workflow example")
    
    # 1. Initialize Symphony - minimal configuration
    symphony = Symphony()
    await symphony.setup()
    
    # 2. Register custom tools - simple function registration
    symphony.register_tool("web_search", web_search)
    symphony.register_tool("sentiment_analyzer", analyze_sentiment)
    symphony.register_tool("summarizer", summarize_text)
    
    # 3. Create specialized agents for the workflow
    researcher = symphony.create_agent(
        name="Researcher",
        description="Researches topics and finds information"
    )
    
    analyzer = symphony.create_agent(
        name="Analyzer",
        description="Analyzes information and extracts insights"
    )
    
    writer = symphony.create_agent(
        name="ContentWriter",
        description="Creates summaries and content based on research"
    )
    
    # 4. Create a multi-agent workflow - clean, declarative API
    research_workflow = symphony.create_workflow(
        name="ResearchWorkflow",
        description="Research a topic, analyze findings, and create a summary"
    )
    
    # 5. Add workflow steps with clear connections
    research_workflow.add_step(
        name="research",
        agent=researcher,
        input="Research recent advancements in quantum computing in 2023",
        tools=["web_search"]
    )
    
    research_workflow.add_step(
        name="analyze",
        agent=analyzer,
        input_from="research",  # Use output from previous step
        tools=["sentiment_analyzer"]
    )
    
    research_workflow.add_step(
        name="summarize",
        agent=writer,
        input_from="analyze",  # Use output from previous step
        tools=["summarizer"]
    )
    
    # 6. Execute the workflow
    logger.info("Executing research workflow...")
    result = await symphony.execute_workflow(research_workflow)
    
    # 7. Display the final result
    logger.info(f"Workflow result: {result}")
    
    logger.info("Symphony simplified workflow example completed")


if __name__ == "__main__":
    asyncio.run(run_workflow_example())