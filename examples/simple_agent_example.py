"""
Simple Agent Example

This example demonstrates using the simplified Symphony API to create 
and use agents with minimal cognitive load.
"""

import asyncio
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("symphony_example")

# Import from the simplified API
from symphony.simple_api import Symphony


# Custom tool example - simple function, no complex plugin architecture
def analyze_entities(text: str) -> Dict[str, Any]:
    """Analyze entities in text.
    
    A simple example tool that extracts potential entities from text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with extracted entities
    """
    # This is a simplified example - would use NLP in reality
    entities = []
    
    # Look for dates (very simplified)
    import re
    date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    dates = re.findall(date_pattern, text)
    
    # Look for emails (simplified)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    # Look for potential organizations (simplified)
    org_indicators = ["Inc", "Corp", "LLC", "Ltd", "Company", "GmbH"]
    words = text.split()
    for i, word in enumerate(words):
        if word in org_indicators and i > 0:
            entities.append({
                "type": "organization",
                "text": f"{words[i-1]} {word}",
                "position": i-1
            })
    
    # Return results
    return {
        "entities": {
            "dates": dates,
            "emails": emails,
            "organizations": entities
        },
        "count": len(dates) + len(emails) + len(entities)
    }


async def run_example():
    """Run the Symphony simplified API example."""
    logger.info("Starting Symphony simplified API example")
    
    # 1. Initialize Symphony - minimal configuration
    symphony = Symphony()
    await symphony.setup()
    
    # 2. Register our custom tool - simple function registration
    symphony.register_tool("entity_analyzer", analyze_entities)
    
    # 3. Create a basic agent - no builder patterns or plugins needed
    agent = symphony.create_agent(
        name="DocumentAnalyst",
        description="An agent that analyzes documents and extracts information"
    )
    
    # 4. Execute a task with the agent - clean, simple API
    logger.info("Executing basic task...")
    result = await agent.execute(
        "Extract information from this text: On 12/25/2023, " +
        "John from Acme Corp (john.doe@acme.com) sent a document to " +
        "Sarah from TechCo Ltd (sarah@techco.com) regarding the project."
    )
    logger.info(f"Basic result: {result}")
    
    # 5. Enhanced execution with tools - progressive complexity
    logger.info("Executing task with entity analyzer tool...")
    result_with_tool = await agent.execute(
        "Extract entities from this text: On 12/25/2023, " +
        "John from Acme Corp (john.doe@acme.com) sent a document to " +
        "Sarah from TechCo Ltd (sarah@techco.com) regarding the project.",
        use_tools=["entity_analyzer"]
    )
    logger.info(f"Result with tool: {result_with_tool}")
    
    # 6. Create a domain-specialized agent - presets instead of plugins
    legal_agent = symphony.create_agent(
        name="LegalAssistant",
        preset="legal"  # Pre-configured for legal domain
    )
    
    # 7. Add memory to agent - progressive enhancement
    legal_agent.add_memory("conversation")
    
    # 8. Execute domain-specific task
    logger.info("Executing legal domain task...")
    legal_result = await legal_agent.execute(
        "Analyze this clause: The parties hereby agree to maintain " +
        "confidentiality of all information shared during the term of this agreement."
    )
    logger.info(f"Legal domain result: {legal_result}")
    
    # 9. Chain interactions with the same agent (using memory)
    logger.info("Testing memory with follow-up question...")
    followup_result = await legal_agent.execute(
        "What are the key components of the clause I just asked about?"
    )
    logger.info(f"Follow-up result: {followup_result}")
    
    logger.info("Symphony simplified API example completed")


if __name__ == "__main__":
    asyncio.run(run_example())