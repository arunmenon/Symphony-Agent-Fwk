"""Chain of Thought reasoning pattern.

This module implements the Chain of Thought reasoning pattern,
which breaks down complex reasoning tasks into explicit steps.
"""

from typing import Dict, Any, List, Optional
import json
import re

from symphony.patterns.base import Pattern, PatternContext, PatternConfig
from symphony.core.task import Task


class ChainOfThoughtPattern(Pattern):
    """Chain of Thought reasoning pattern.
    
    This pattern implements sequential reasoning with explicit
    intermediate steps, allowing the model to break down complex
    problems into manageable pieces.
    """
    
    async def execute(self, context: PatternContext) -> None:
        """Execute the chain of thought pattern.
        
        Args:
            context: Pattern execution context
            
        Returns:
            None
        """
        # Get inputs
        query = context.get_input("query")
        if not query:
            context.set_output("error", "No query provided")
            return
        
        # Get agent ID from config or context
        agent_id = self.config.agent_roles.get("reasoner") or context.get_input("agent_id")
        
        # Get max iterations
        max_iterations = min(self.config.max_iterations, 10)  # Limit to 10 max
        
        # Get task manager
        task_manager = context.get_service("task_manager")
        
        # Format the initial prompt to encourage step-by-step reasoning
        cot_prompt = f"""Please solve this problem step-by-step, showing your reasoning:

{query}

Let's work through this carefully:

Step 1:"""
        
        # Create the initial task
        task = Task(
            name="Chain of Thought Reasoning",
            description="Step-by-step reasoning task",
            input_data={"query": cot_prompt},
            agent_id=agent_id
        )
        
        # Execute the task
        task_id = await task_manager.save_task(task)
        executor = context.get_service("enhanced_executor")
        result_task = await executor.execute_task(task_id)
        
        # Check for successful execution
        if result_task.status.value != "completed":
            context.set_output("error", f"Task execution failed: {result_task.error}")
            return
        
        # Extract steps from response
        response = result_task.output_data.get("result", "")
        
        # Parse steps from the response
        steps = self._extract_steps(response)
        
        # Set outputs
        context.set_output("response", response)
        context.set_output("steps", steps)
        context.set_output("result", response)  # For compatibility with other patterns
        
        # Add metadata
        context.metadata["num_steps"] = len(steps)
    
    def _extract_steps(self, text: str) -> List[Dict[str, Any]]:
        """Extract reasoning steps from text.
        
        Args:
            text: Response text
            
        Returns:
            List of reasoning steps
        """
        # Look for step patterns like "Step 1:", "Step 2:", etc.
        step_pattern = re.compile(r"(?:Step\s+(\d+)[:.]\s*)(.*?)(?=Step\s+\d+[:.]\s*|$)", re.DOTALL)
        matches = step_pattern.findall(text)
        
        steps = []
        for num, content in matches:
            steps.append({
                "number": int(num),
                "content": content.strip()
            })
        
        # If no steps found, try to split by newlines and create steps
        if not steps:
            lines = text.split("\n")
            current_step = {"number": 1, "content": ""}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                new_step_match = re.match(r"^(\d+)[.:]", line)
                if new_step_match and current_step["content"]:
                    steps.append(current_step)
                    step_num = int(new_step_match.group(1))
                    content = line[len(new_step_match.group(0)):].strip()
                    current_step = {"number": step_num, "content": content}
                else:
                    current_step["content"] += " " + line
                    
            if current_step["content"]:
                steps.append(current_step)
                
        # If still no steps, just use the whole text as one step
        if not steps:
            steps.append({
                "number": 1,
                "content": text.strip()
            })
            
        return steps