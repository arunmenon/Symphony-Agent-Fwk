"""Verify-and-execute pattern for Symphony.

This module implements the verify-and-execute pattern,
which verifies a tool usage plan before execution.
"""

from typing import Dict, Any, List
import json

from symphony.patterns.base import Pattern, PatternContext


class VerifyExecutePattern(Pattern):
    """Verify-and-execute pattern.
    
    This pattern verifies a tool usage plan before execution,
    ensuring safety and correctness of tool operations.
    """
    
    async def execute(self, context: PatternContext) -> None:
        """Execute the verify-and-execute pattern.
        
        Args:
            context: Execution context
                
        Inputs:
            query: The user query
            tools: List of tool configurations to execute
            verification_criteria: List of verification criteria
            
        Outputs:
            verification_result: Verification result
            execution_result: Execution result if verification passed
            verified: Boolean indicating if verification passed
        """
        # Get inputs
        query = context.get_input("query")
        tools = context.get_input("tools", [])
        verification_criteria = context.get_input("verification_criteria", [
            "Safety", "Relevance", "Efficiency", "Correctness"
        ])
        
        if not tools:
            context.set_output("error", "No tools provided for execution")
            context.set_output("verified", False)
            return
            
        # Get agent and tool services
        agent_service = context.get_service("agent_manager")
        tool_manager = context.get_service("tool_manager")
        
        if not agent_service or not tool_manager:
            context.set_output("error", "Required services not found")
            context.set_output("verified", False)
            return
        
        # Get verification agent
        verifier_role = self.config.agent_roles.get("verifier")
        if not verifier_role:
            context.set_output("error", "Verifier agent role not configured")
            context.set_output("verified", False)
            return
            
        # Prepare verification request
        verification_request = {
            "query": query,
            "tools": json.dumps(tools, indent=2),
            "criteria": verification_criteria
        }
        
        # Create verification prompt
        verification_prompt = f"""
        You are a thoughtful tool usage verification agent. Please verify the following tool usage plan:
        
        User Query: {query}
        
        Proposed Tool Usage Plan:
        {json.dumps(tools, indent=2)}
        
        Verify the plan against these criteria:
        {', '.join(verification_criteria)}
        
        For each criterion, provide:
        1. Assessment (PASS/FAIL)
        2. Reasoning
        
        Then provide an overall APPROVED or REJECTED assessment with explanation.
        If rejected, suggest improvements to the plan.
        """
        
        # Execute verification
        try:
            verification_response = await agent_service.execute_agent(
                verifier_role,
                verification_prompt
            )
            
            # Parse verification result
            verification_passed = "APPROVED" in verification_response
            
            # Store verification result
            context.set_output("verification_result", verification_response)
            context.set_output("verified", verification_passed)
            
            # Execute tools if verification passed
            if verification_passed:
                # Execute multi-tool chain
                execution_results = []
                
                for i, tool_config in enumerate(tools):
                    tool_name = tool_config.get("name")
                    tool_inputs = tool_config.get("inputs", {})
                    tool_params = tool_config.get("config", {})
                    
                    try:
                        result = await tool_manager.execute_tool(
                            tool_name,
                            tool_inputs,
                            tool_params
                        )
                        
                        execution_results.append({
                            "step": i + 1,
                            "tool": tool_name,
                            "inputs": tool_inputs,
                            "outputs": result
                        })
                        
                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        context.set_output("error", error_msg)
                        break
                
                context.set_output("execution_result", execution_results)
            else:
                context.set_output("execution_result", None)
                
        except Exception as e:
            context.set_output("error", f"Verification failed: {str(e)}")
            context.set_output("verified", False)