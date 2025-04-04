"""Reflection-based learning pattern for Symphony.

This module implements the reflection pattern,
which enables an agent to reflect on and improve its responses.
"""

from typing import Dict, Any, List, Optional
import json

from symphony.patterns.base import Pattern, PatternContext


class ReflectionPattern(Pattern):
    """Reflection-based learning pattern.
    
    This pattern enables an agent to reflect on its initial response,
    evaluate it against criteria, and generate an improved response.
    """
    
    async def execute(self, context: PatternContext) -> None:
        """Execute the reflection pattern.
        
        Args:
            context: Execution context
                
        Inputs:
            task: The task to perform
            criteria: Evaluation criteria
            query: The input query
            
        Outputs:
            initial_response: Initial agent response
            reflection: Agent's reflection
            final_response: Improved response after reflection
            improvement: Summary of improvements made
        """
        # Get inputs
        task = context.get_input("task")
        criteria = context.get_input("criteria", [
            "Accuracy", "Clarity", "Completeness", "Conciseness"
        ])
        query = context.get_input("query")
        
        if not task or not query:
            context.set_output("error", "Task and query are required")
            return
            
        # Get agent service
        agent_service = context.get_service("agent_manager")
        if not agent_service:
            context.set_output("error", "Agent service not found")
            return
        
        # Get agent roles
        performer_role = self.config.agent_roles.get("performer")
        reflector_role = self.config.agent_roles.get("reflector") or performer_role
        
        if not performer_role:
            context.set_output("error", "Performer agent role not configured")
            return
            
        # Prepare initial prompt
        initial_prompt = f"""
        Task: {task}
        
        Please respond to the following:
        {query}
        """
        
        try:
            # Get initial response
            initial_response = await agent_service.execute_agent(
                performer_role,
                initial_prompt
            )
            
            context.set_output("initial_response", initial_response)
            
            # Prepare reflection prompt
            criteria_text = "\n".join([f"- {criterion}" for criterion in criteria])
            
            reflection_prompt = f"""
            Task: {task}
            
            Original query: {query}
            
            Your initial response:
            {initial_response}
            
            Please reflect on your response and evaluate it based on these criteria:
            {criteria_text}
            
            For each criterion:
            1. Rate your response (1-5 scale)
            2. Explain the rating
            3. Suggest specific improvements
            
            Then provide an overall assessment of your response and how it could be improved.
            """
            
            # Get reflection
            reflection = await agent_service.execute_agent(
                reflector_role,
                reflection_prompt
            )
            
            context.set_output("reflection", reflection)
            
            # Prepare improvement prompt
            improvement_prompt = f"""
            Task: {task}
            
            Original query: {query}
            
            Your initial response:
            {initial_response}
            
            Your reflection:
            {reflection}
            
            Based on your reflection, please provide an improved response to the original query.
            Focus on addressing the specific weaknesses you identified while maintaining the strengths.
            """
            
            # Get improved response
            final_response = await agent_service.execute_agent(
                performer_role,
                improvement_prompt
            )
            
            context.set_output("final_response", final_response)
            
            # Generate improvement summary
            summary_prompt = f"""
            Please provide a concise summary of how the final response improved upon the initial response.
            Highlight the key differences and improvements made based on the reflection.
            
            Initial response:
            {initial_response}
            
            Final response:
            {final_response}
            """
            
            improvement_summary = await agent_service.execute_agent(
                reflector_role,
                summary_prompt
            )
            
            context.set_output("improvement", improvement_summary)
            
        except Exception as e:
            context.set_output("error", f"Pattern execution failed: {str(e)}")
            
            
class IterativeReflectionPattern(ReflectionPattern):
    """Iterative reflection-based learning pattern.
    
    This pattern extends the basic reflection pattern with multiple
    iterations of reflection and improvement.
    """
    
    async def execute(self, context: PatternContext) -> None:
        """Execute the iterative reflection pattern.
        
        Args:
            context: Execution context
                
        Inputs:
            task: The task to perform
            criteria: Evaluation criteria
            query: The input query
            iterations: Number of reflection iterations to perform
            
        Outputs:
            responses: List of responses for each iteration
            reflections: List of reflections for each iteration
            final_response: The final improved response
            improvement_trace: Summary of improvements across iterations
        """
        # Get inputs
        task = context.get_input("task")
        criteria = context.get_input("criteria", [
            "Accuracy", "Clarity", "Completeness", "Conciseness"
        ])
        query = context.get_input("query")
        iterations = context.get_input("iterations", self.config.max_iterations)
        
        if not task or not query:
            context.set_output("error", "Task and query are required")
            return
            
        # Get agent service
        agent_service = context.get_service("agent_manager")
        if not agent_service:
            context.set_output("error", "Agent service not found")
            return
        
        # Get agent roles
        performer_role = self.config.agent_roles.get("performer")
        reflector_role = self.config.agent_roles.get("reflector") or performer_role
        
        if not performer_role:
            context.set_output("error", "Performer agent role not configured")
            return
            
        # Initialize tracking data
        responses = []
        reflections = []
        
        # Prepare initial prompt
        initial_prompt = f"""
        Task: {task}
        
        Please respond to the following:
        {query}
        """
        
        try:
            # Get initial response
            current_response = await agent_service.execute_agent(
                performer_role,
                initial_prompt
            )
            
            responses.append(current_response)
            
            # Iterative reflection loop
            for i in range(iterations):
                # Create child context for this iteration
                child_context = context.create_child_context({
                    "task": task,
                    "criteria": criteria,
                    "query": query,
                    "iteration": i + 1
                })
                
                # Prepare reflection prompt
                criteria_text = "\n".join([f"- {criterion}" for criterion in criteria])
                
                reflection_prompt = f"""
                Task: {task}
                
                Original query: {query}
                
                Your current response (iteration {i+1}):
                {current_response}
                
                Please reflect on your response and evaluate it based on these criteria:
                {criteria_text}
                
                For each criterion:
                1. Rate your response (1-5 scale)
                2. Explain the rating
                3. Suggest specific improvements
                
                Then provide an overall assessment of your response and how it could be improved.
                """
                
                # Get reflection
                reflection = await agent_service.execute_agent(
                    reflector_role,
                    reflection_prompt
                )
                
                reflections.append(reflection)
                child_context.set_output("reflection", reflection)
                
                # Prepare improvement prompt
                improvement_prompt = f"""
                Task: {task}
                
                Original query: {query}
                
                Your current response (iteration {i+1}):
                {current_response}
                
                Your reflection:
                {reflection}
                
                Based on your reflection, please provide an improved response to the original query.
                Focus on addressing the specific weaknesses you identified while maintaining the strengths.
                """
                
                # Get improved response
                improved_response = await agent_service.execute_agent(
                    performer_role,
                    improvement_prompt
                )
                
                responses.append(improved_response)
                child_context.set_output("improved_response", improved_response)
                
                # Set for next iteration
                current_response = improved_response
            
            # Set final outputs
            context.set_output("responses", responses)
            context.set_output("reflections", reflections)
            context.set_output("final_response", responses[-1])
            
            # Generate improvement trace
            improvement_trace = []
            
            for i in range(len(reflections)):
                if i < len(responses) - 1:
                    trace_prompt = f"""
                    Provide a concise summary of how the response improved from iteration {i+1} to iteration {i+2}.
                    Highlight the key differences and improvements made based on the reflection.
                    
                    Iteration {i+1} response:
                    {responses[i]}
                    
                    Reflection:
                    {reflections[i]}
                    
                    Iteration {i+2} response:
                    {responses[i+1]}
                    """
                    
                    trace = await agent_service.execute_agent(
                        reflector_role,
                        trace_prompt
                    )
                    
                    improvement_trace.append({
                        "iteration": i + 1,
                        "summary": trace
                    })
            
            context.set_output("improvement_trace", improvement_trace)
            
        except Exception as e:
            context.set_output("error", f"Pattern execution failed: {str(e)}")