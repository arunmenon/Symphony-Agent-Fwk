"""Multi-tool chain pattern for Symphony.

This module implements the multi-tool chain pattern,
which chains together multiple tool calls in a sequence.
"""

from typing import Dict, Any, List
import json

from symphony.patterns.base import Pattern, PatternContext


class MultiToolChainPattern(Pattern):
    """Multi-tool chain pattern.
    
    This pattern chains together multiple tool calls in a sequence,
    where each tool's output becomes input for the next tool.
    """
    
    async def execute(self, context: PatternContext) -> None:
        """Execute the multi-tool chain pattern.
        
        Args:
            context: Execution context
                
        Inputs:
            query: The user query or starting input
            tools: List of tool configurations in execution order
                Each tool config should have:
                - name: Tool name
                - config: Tool-specific configuration
                - input_mapping: Dict mapping previous outputs to tool inputs
                - output_mapping: Dict mapping tool outputs to shared output keys
            
        Outputs:
            results: Results from each tool execution
            final_result: Result from the final tool in the chain
        """
        # Get inputs
        query = context.get_input("query")
        tools = context.get_input("tools", [])
        
        if not tools:
            context.set_output("error", "No tools provided for execution")
            context.set_output("final_result", None)
            return
        
        # Initialize shared state for tool chain
        shared_state = {"query": query}
        results = []
        
        # Execute each tool in sequence
        for i, tool_config in enumerate(tools):
            # Extract tool configuration
            tool_name = tool_config.get("name")
            tool_params = tool_config.get("config", {})
            input_mapping = tool_config.get("input_mapping", {})
            output_mapping = tool_config.get("output_mapping", {})
            
            if not tool_name:
                context.set_output("error", f"Tool at index {i} missing name")
                break
                
            # Create tool inputs from shared state
            tool_inputs = {}
            for target_key, source_key in input_mapping.items():
                if source_key in shared_state:
                    tool_inputs[target_key] = shared_state[source_key]
            
            # Create child context for tool execution
            child_context = context.create_child_context({
                "tool_name": tool_name,
                "tool_inputs": tool_inputs,
                "tool_config": tool_params
            })
            
            # Get tool manager service
            tool_manager = context.get_service("tool_manager")
            if not tool_manager:
                context.set_output("error", "Tool manager service not found")
                break
                
            # Execute tool
            try:
                child_context.metadata["step"] = i + 1
                child_context.metadata["tool"] = tool_name
                
                tool_result = await tool_manager.execute_tool(
                    tool_name,
                    tool_inputs,
                    tool_params
                )
                
                # Store tool result
                child_context.set_output("result", tool_result)
                results.append({
                    "step": i + 1,
                    "tool": tool_name,
                    "inputs": tool_inputs,
                    "outputs": tool_result
                })
                
                # Update shared state with tool outputs
                if output_mapping:
                    for target_key, source_key in output_mapping.items():
                        if source_key in tool_result:
                            shared_state[target_key] = tool_result[source_key]
                else:
                    # If no mapping provided, add all outputs to shared state
                    for key, value in tool_result.items():
                        shared_state[key] = value
                        
            except Exception as e:
                error_msg = f"Error executing tool {tool_name}: {str(e)}"
                child_context.set_output("error", error_msg)
                context.set_output("error", error_msg)
                break
        
        # Set outputs
        context.set_output("results", results)
        context.set_output("final_result", results[-1]["outputs"] if results else None)
        context.set_output("shared_state", shared_state)