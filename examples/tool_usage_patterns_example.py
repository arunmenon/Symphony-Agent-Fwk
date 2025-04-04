"""Example demonstrating tool usage patterns in Symphony.

This example shows how to use tool usage patterns to orchestrate
complex tool interactions in Symphony.
"""

import asyncio
import json
from symphony.api import Symphony
from symphony.agents.config import AgentConfig


async def run_multi_tool_chain():
    """Demonstrate the multi-tool chain pattern."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register a simple agent
    agent_config = AgentConfig(
        name="tool_user",
        description="An agent that uses tools",
        model="gpt-4-turbo"
    )
    agent_id = await symphony.agents.create_agent(agent_config)
    
    # Register some mock tools
    await symphony.tools.register_tool(
        name="extract_entities",
        description="Extract entities from text",
        function=lambda text: {"entities": ["Mock Entity 1", "Mock Entity 2"]}
    )
    
    await symphony.tools.register_tool(
        name="sentiment_analysis",
        description="Analyze sentiment of text",
        function=lambda text: {"sentiment": "positive", "score": 0.8}
    )
    
    await symphony.tools.register_tool(
        name="summarize_text",
        description="Generate a summary of text",
        function=lambda text, max_length: {"summary": "This is a mock summary."}
    )
    
    # Create a multi-tool chain configuration
    tools_config = [
        {
            "name": "extract_entities",
            "config": {},
            "input_mapping": {"text": "query"},
            "output_mapping": {"entities": "entities"}
        },
        {
            "name": "sentiment_analysis",
            "config": {},
            "input_mapping": {"text": "query"},
            "output_mapping": {"sentiment": "sentiment", "score": "sentiment_score"}
        },
        {
            "name": "summarize_text",
            "config": {"max_length": 100},
            "input_mapping": {"text": "query"},
            "output_mapping": {"summary": "summary"}
        }
    ]
    
    # Execute the pattern through the facade
    print("Using Multi-Tool Chain Pattern:")
    result = await symphony.patterns.apply_tool_usage_pattern(
        "multi_tool_chain",
        "This is a test query for the multi-tool chain pattern. Symphony is a powerful framework for orchestrating AI agents.",
        tools=tools_config,
        config={"agent_roles": {"executor": agent_id}}
    )
    
    print(f"Multi-Tool Chain Result: {json.dumps(result, indent=2)}")
    
    # Alternative: use the builder approach
    print("\nUsing Pattern Builder:")
    result = await symphony.build_pattern() \
        .create("multi_tool_chain") \
        .with_agent("executor", agent_id) \
        .with_query("Symphony makes it easy to orchestrate complex agent workflows and tool usage patterns.") \
        .with_tools(tools_config) \
        .execute()
    
    print(f"Builder Approach Result: {json.dumps(result, indent=2)}")


async def run_verify_execute():
    """Demonstrate the verify-execute pattern."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register agents
    verifier_config = AgentConfig(
        name="plan_verifier",
        description="An agent that verifies tool execution plans",
        model="gpt-4-turbo"
    )
    verifier_id = await symphony.agents.create_agent(verifier_config)
    
    executor_config = AgentConfig(
        name="tool_executor",
        description="An agent that executes tools",
        model="gpt-4-turbo"
    )
    executor_id = await symphony.agents.create_agent(executor_config)
    
    # Register a mock tool
    await symphony.tools.register_tool(
        name="file_browser",
        description="Browse files in a directory",
        function=lambda path: {"files": ["file1.txt", "file2.txt"]}
    )
    
    # Create a tool configuration
    tools_config = [
        {
            "name": "file_browser",
            "inputs": {"path": "/safe/path"},
            "config": {}
        }
    ]
    
    # Define verification criteria
    verification_criteria = [
        "Safety: Ensure the operation doesn't access sensitive files",
        "Authorization: Verify the operation has necessary permissions",
        "Relevance: Check that the operation helps address the user query"
    ]
    
    # Execute the pattern
    print("\nUsing Verify-Execute Pattern:")
    result = await symphony.patterns.apply_tool_usage_pattern(
        "verify_execute",
        "Can you show me the files in the directory /safe/path?",
        tools=tools_config,
        config={
            "agent_roles": {
                "verifier": verifier_id,
                "executor": executor_id
            },
            "verification_criteria": verification_criteria
        }
    )
    
    print(f"Verify-Execute Result: {json.dumps(result, indent=2)}")


async def run_recursive_tool_use():
    """Demonstrate the recursive tool use pattern."""
    # Initialize Symphony
    symphony = Symphony()
    
    # Register an agent
    agent_config = AgentConfig(
        name="problem_solver",
        description="An agent that can recursively solve problems",
        model="gpt-4-turbo"
    )
    agent_id = await symphony.agents.create_agent(agent_config)
    
    # Register some mock tools
    await symphony.tools.register_tool(
        name="calculator",
        description="Perform calculations",
        function=lambda expression: {"result": eval(expression)}
    )
    
    await symphony.tools.register_tool(
        name="unit_converter",
        description="Convert between units",
        function=lambda value, from_unit, to_unit: {"result": f"{value} {to_unit}"}
    )
    
    await symphony.tools.register_tool(
        name="data_lookup",
        description="Look up data from a database",
        function=lambda entity, attribute: {"result": f"Mock data for {entity}.{attribute}"}
    )
    
    # Define available tools
    tools = [
        {
            "name": "calculator",
            "description": "Perform mathematical calculations"
        },
        {
            "name": "unit_converter",
            "description": "Convert values between different units"
        },
        {
            "name": "data_lookup",
            "description": "Look up data from a database"
        }
    ]
    
    # Execute the pattern
    print("\nUsing Recursive Tool Use Pattern:")
    result = await symphony.patterns.apply_tool_usage_pattern(
        "recursive_tool_use",
        "If I have a 1500 square foot house and electricity costs $0.15 per kilowatt-hour, and I use 20 kilowatt-hours per square foot per year, what's my annual electricity cost?",
        tools=tools,
        config={
            "agent_roles": {"dispatcher": agent_id},
            "max_depth": 3
        }
    )
    
    print(f"Recursive Tool Use Result:")
    print(f"Final Answer: {result.get('result')}")
    print(f"Decomposition Depth: {len(result.get('decomposition', {}).get('sub_problems', []))}")


async def main():
    """Run all pattern examples."""
    await run_multi_tool_chain()
    await run_verify_execute()
    await run_recursive_tool_use()


if __name__ == "__main__":
    asyncio.run(main())