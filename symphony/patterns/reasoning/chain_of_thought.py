"""Chain of Thought reasoning pattern.

This module implements the Chain of Thought reasoning pattern,
which breaks down complex reasoning tasks into explicit steps.
"""

from typing import Dict, Any, List, Optional
import json
import re

from symphony.patterns.base import Pattern, PatternContext, PatternConfig
from symphony.core.task import Task
from symphony.patterns.prompts import get_registry


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
        
        # Get prompt template
        prompt_registry = get_registry()
        prompt_style = self.config.metadata.get("prompt_style", "default")
        
        # Render the prompt template with query
        try:
            cot_prompt = prompt_registry.render_template(
                "reasoning.chain_of_thought",
                {"query": query},
                version=prompt_style
            )
        except ValueError:
            # Fallback to default prompt if template not found
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
        context.metadata["prompt_style"] = prompt_style
    
    def _extract_steps(self, text: str) -> List[str]:
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
        for _, content in matches:
            steps.append(content.strip())
        
        # If no steps found, try to split by newlines and look for numbered steps
        if not steps:
            lines = text.split("\n")
            current_step = ""
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                new_step_match = re.match(r"^(\d+)[.:]", line)
                if new_step_match and current_step:
                    steps.append(current_step)
                    current_step = line[len(new_step_match.group(0)):].strip()
                else:
                    current_step += " " + line if current_step else line
                    
            if current_step:
                steps.append(current_step)
                
        # If still no steps, just use the whole text as one step
        if not steps:
            steps.append(text.strip())
            
        return steps