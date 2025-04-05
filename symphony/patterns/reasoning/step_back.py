"""Step Back reasoning pattern.

This module implements the Step Back reasoning pattern,
which encourages taking a high-level view before diving into details.
"""

from typing import Dict, Any, List, Optional
import json

from symphony.patterns.base import Pattern, PatternContext, PatternConfig
from symphony.core.task import Task
from symphony.patterns.prompts import get_registry


class StepBackPattern(Pattern):
    """Step Back reasoning pattern.
    
    This pattern implements a meta-level analysis approach that
    encourages taking a high-level view before diving into details,
    which can help with complex or counterintuitive problems.
    """
    
    async def execute(self, context: PatternContext) -> None:
        """Execute the step back pattern.
        
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
        
        # Get task manager
        task_manager = context.get_service("task_manager")
        
        # Get prompt template
        prompt_registry = get_registry()
        prompt_style = self.config.metadata.get("prompt_style", "default")
        
        # Step 1: High-level strategic analysis
        try:
            # Get strategic prompt template
            strategic_prompt = prompt_registry.get_template(
                "reasoning.step_back",
                version=prompt_style
            )["strategic"]["content"]
            
            # Replace variables
            strategic_prompt = strategic_prompt.replace("{query}", query)
        except (ValueError, KeyError):
            # Fallback to default prompt if template not found
            strategic_prompt = f"""Before diving into the details of this problem, let's take a step back and think about:
1. The high-level approach we should take
2. What domain knowledge is relevant
3. How we might structure our solution

Problem: {query}

First, let's analyze this at a strategic level:"""
        
        # Create the strategic analysis task
        strategic_task = Task(
            name="Step Back - Strategic Analysis",
            description="High-level strategic analysis",
            input_data={"query": strategic_prompt},
            agent_id=agent_id
        )
        
        # Execute the task
        strategic_task_id = await task_manager.save_task(strategic_task)
        executor = context.get_service("enhanced_executor")
        strategic_result = await executor.execute_task(strategic_task_id)
        
        # Check for successful execution
        if strategic_result.status.value != "completed":
            context.set_output("error", f"Strategic analysis failed: {strategic_result.error}")
            return
        
        # Get strategic analysis
        strategic_analysis = strategic_result.output_data.get("result", "")
        
        # Step 2: Detailed solution based on strategic analysis
        try:
            # Get detailed prompt template
            detailed_prompt = prompt_registry.get_template(
                "reasoning.step_back",
                version=prompt_style
            )["detailed"]["content"]
            
            # Replace variables
            detailed_prompt = detailed_prompt.replace("{query}", query)
            detailed_prompt = detailed_prompt.replace("{strategic_analysis}", strategic_analysis)
        except (ValueError, KeyError):
            # Fallback to default prompt if template not found
            detailed_prompt = f"""Based on our strategic analysis:

{strategic_analysis}

Now, let's solve the problem in detail:

{query}

Detailed solution:"""
        
        # Create the detailed solution task
        detailed_task = Task(
            name="Step Back - Detailed Solution",
            description="Detailed solution based on strategic analysis",
            input_data={"query": detailed_prompt},
            agent_id=agent_id
        )
        
        # Execute the task
        detailed_task_id = await task_manager.save_task(detailed_task)
        detailed_result = await executor.execute_task(detailed_task_id)
        
        # Check for successful execution
        if detailed_result.status.value != "completed":
            context.set_output("error", f"Detailed solution failed: {detailed_result.error}")
            return
        
        # Get detailed solution
        detailed_solution = detailed_result.output_data.get("result", "")
        
        # Set outputs
        context.set_output("strategic_analysis", strategic_analysis)
        context.set_output("detailed_solution", detailed_solution)
        context.set_output("response", detailed_solution)
        context.set_output("result", detailed_solution)  # For compatibility with other patterns
        
        # Add metadata
        context.metadata["had_strategic_analysis"] = True
        context.metadata["strategic_task_id"] = strategic_task_id
        context.metadata["detailed_task_id"] = detailed_task_id
        context.metadata["prompt_style"] = prompt_style