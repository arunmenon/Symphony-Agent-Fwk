"""Recursive tool use pattern for Symphony.

This module implements the recursive tool use pattern,
which enables agents to recursively decompose problems into 
sub-problems that can be solved with tools.
"""

from typing import Dict, Any, List
import json

from symphony.patterns.base import Pattern, PatternContext


class RecursiveToolUsePattern(Pattern):
    """Recursive tool use pattern.
    
    This pattern enables agents to recursively decompose complex problems
    into sub-problems that can be solved with available tools.
    """
    
    async def execute(self, context: PatternContext) -> None:
        """Execute the recursive tool use pattern.
        
        Args:
            context: Execution context
                
        Inputs:
            query: The user query
            tools: List of available tools
            max_depth: Maximum recursion depth
            
        Outputs:
            result: Final result
            decomposition: Problem decomposition tree
        """
        # Get inputs
        query = context.get_input("query")
        available_tools = context.get_input("tools", [])
        max_depth = context.get_input("max_depth", self.config.max_iterations)
        
        if not available_tools:
            context.set_output("error", "No tools provided")
            return
            
        # Get agent and tool services
        agent_service = context.get_service("agent_manager")
        tool_manager = context.get_service("tool_manager")
        
        if not agent_service or not tool_manager:
            context.set_output("error", "Required services not found")
            return
        
        # Get dispatcher agent
        dispatcher_role = self.config.agent_roles.get("dispatcher")
        if not dispatcher_role:
            context.set_output("error", "Dispatcher agent role not configured")
            return
            
        # Initialize decomposition tree
        decomposition = {
            "query": query,
            "sub_problems": [],
            "result": None
        }
        
        # Execute recursive decomposition
        final_result = await self._solve_recursively(
            query,
            available_tools,
            agent_service,
            tool_manager,
            dispatcher_role,
            decomposition,
            1,
            max_depth,
            context
        )
        
        # Set outputs
        context.set_output("result", final_result)
        context.set_output("decomposition", decomposition)
    
    async def _solve_recursively(
        self,
        query: str,
        available_tools: List[Dict[str, Any]],
        agent_service: Any,
        tool_manager: Any,
        dispatcher_role: str,
        decomposition_node: Dict[str, Any],
        current_depth: int,
        max_depth: int,
        parent_context: PatternContext
    ) -> Any:
        """Recursively solve a problem through decomposition.
        
        Args:
            query: The problem query
            available_tools: List of available tools
            agent_service: Agent service
            tool_manager: Tool manager service
            dispatcher_role: Dispatcher agent role
            decomposition_node: Current node in decomposition tree
            current_depth: Current recursion depth
            max_depth: Maximum recursion depth
            parent_context: Parent execution context
            
        Returns:
            Solution result
        """
        # Check recursion depth
        if current_depth > max_depth:
            decomposition_node["too_deep"] = True
            decomposition_node["result"] = "Recursion depth exceeded"
            return "Max recursion depth reached"
            
        # Create child context for this level
        child_context = parent_context.create_child_context({
            "query": query,
            "tools": available_tools,
            "depth": current_depth
        })
        
        # Prepare problem analysis prompt
        tools_description = "\n".join([
            f"- {tool['name']}: {tool.get('description', 'No description')}"
            for tool in available_tools
        ])
        
        dispatcher_prompt = f"""
        You are a problem-solving dispatcher. Your task is to analyze a complex problem
        and determine whether it can be solved directly with available tools, or if it
        needs to be broken down into simpler sub-problems.
        
        Available tools:
        {tools_description}
        
        Problem: {query}
        
        Please respond with a JSON object in the following format:
        
        {{
            "can_solve_directly": true/false,
            "tool_to_use": "tool_name" (if can solve directly),
            "tool_inputs": {{...}} (if can solve directly),
            "sub_problems": [
                {{
                    "query": "sub-problem 1",
                    "explanation": "why this is a necessary sub-component"
                }},
                ...
            ] (if needs decomposition)
        }}
        
        If the problem can be solved directly with one of the available tools, set can_solve_directly to true
        and specify which tool to use with appropriate inputs.
        
        If the problem is too complex for direct solution, set can_solve_directly to false and break it down
        into 2-5 simpler sub-problems that, when solved, would help address the original problem.
        """
        
        # Execute dispatcher agent
        try:
            dispatcher_response = await agent_service.execute_agent(
                dispatcher_role,
                dispatcher_prompt
            )
            
            # Parse dispatcher result as JSON
            try:
                analysis = json.loads(dispatcher_response)
                child_context.set_output("analysis", analysis)
                
                # Check if problem can be solved directly
                if analysis.get("can_solve_directly", False):
                    # Get tool to use
                    tool_name = analysis.get("tool_to_use")
                    tool_inputs = analysis.get("tool_inputs", {})
                    
                    if not tool_name:
                        error_msg = "Tool name not specified"
                        child_context.set_output("error", error_msg)
                        decomposition_node["error"] = error_msg
                        return None
                    
                    # Execute tool
                    try:
                        result = await tool_manager.execute_tool(
                            tool_name,
                            tool_inputs
                        )
                        
                        # Store result
                        child_context.set_output("result", result)
                        decomposition_node["tool_used"] = tool_name
                        decomposition_node["tool_inputs"] = tool_inputs
                        decomposition_node["result"] = result
                        
                        return result
                        
                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        child_context.set_output("error", error_msg)
                        decomposition_node["error"] = error_msg
                        return None
                    
                else:
                    # Decompose problem into sub-problems
                    sub_problems = analysis.get("sub_problems", [])
                    
                    if not sub_problems:
                        error_msg = "No sub-problems provided for decomposition"
                        child_context.set_output("error", error_msg)
                        decomposition_node["error"] = error_msg
                        return None
                    
                    # Process each sub-problem recursively
                    all_sub_results = []
                    
                    for sub_problem in sub_problems:
                        sub_query = sub_problem.get("query")
                        sub_explanation = sub_problem.get("explanation", "")
                        
                        if not sub_query:
                            continue
                            
                        # Create sub-problem node
                        sub_node = {
                            "query": sub_query,
                            "explanation": sub_explanation,
                            "sub_problems": [],
                            "result": None
                        }
                        
                        decomposition_node["sub_problems"].append(sub_node)
                        
                        # Solve sub-problem recursively
                        sub_result = await self._solve_recursively(
                            sub_query,
                            available_tools,
                            agent_service,
                            tool_manager,
                            dispatcher_role,
                            sub_node,
                            current_depth + 1,
                            max_depth,
                            child_context
                        )
                        
                        if sub_result is not None:
                            all_sub_results.append({
                                "query": sub_query,
                                "result": sub_result
                            })
                    
                    # Synthesize sub-results
                    if all_sub_results:
                        # Create synthesis prompt
                        sub_results_str = "\n".join([
                            f"Sub-problem: {r['query']}\nResult: {r['result']}"
                            for r in all_sub_results
                        ])
                        
                        synthesis_prompt = f"""
                        You are tasked with synthesizing the results of sub-problems to solve a complex problem.
                        
                        Original problem: {query}
                        
                        Results of sub-problems:
                        {sub_results_str}
                        
                        Please synthesize these results to provide a comprehensive solution to the original problem.
                        """
                        
                        # Execute synthesis
                        synthesis_result = await agent_service.execute_agent(
                            dispatcher_role,
                            synthesis_prompt
                        )
                        
                        # Store synthesis result
                        decomposition_node["result"] = synthesis_result
                        return synthesis_result
                    else:
                        decomposition_node["result"] = "Failed to solve sub-problems"
                        return None
                    
            except json.JSONDecodeError:
                error_msg = "Failed to parse dispatcher response as JSON"
                child_context.set_output("error", error_msg)
                decomposition_node["error"] = error_msg
                decomposition_node["raw_response"] = dispatcher_response
                return None
                
        except Exception as e:
            error_msg = f"Error executing dispatcher: {str(e)}"
            child_context.set_output("error", error_msg)
            decomposition_node["error"] = error_msg
            return None