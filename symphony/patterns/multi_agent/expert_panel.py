"""Expert Panel pattern.

This module implements the Expert Panel pattern,
which uses multiple specialized agents to analyze a problem
from different perspectives.
"""

from typing import Dict, Any, List, Optional
import json
import asyncio

from symphony.patterns.base import Pattern, PatternContext, PatternConfig
from symphony.patterns.prompts import get_registry
from symphony.core.task import Task


class ExpertPanelPattern(Pattern):
    """Expert Panel pattern.
    
    This pattern uses multiple specialized agents to analyze a problem
    from different perspectives, followed by a synthesis of their insights.
    """
    
    async def execute(self, context: PatternContext) -> None:
        """Execute the expert panel pattern.
        
        Args:
            context: Pattern execution context
            
        Returns:
            None
        """
        # Get inputs
        query = context.get_input("query")
        topic = context.get_input("topic")
        
        if not query and not topic:
            context.set_output("error", "No query or topic provided")
            return
        
        # If only topic provided, create a generic query
        if not query and topic:
            query = f"What are the key considerations, insights, and recommendations regarding {topic}?"
        
        # Get perspectives from config or context
        perspectives = self.config.metadata.get("perspectives") or context.get_input("perspectives")
        if not perspectives:
            context.set_output("error", "No perspectives specified")
            return
            
        # Ensure perspectives is a list
        if isinstance(perspectives, str):
            perspectives = [p.strip() for p in perspectives.split(",")]
        
        # Get agent IDs from config
        moderator_agent_id = self.config.agent_roles.get("moderator")
        synthesizer_agent_id = self.config.agent_roles.get("synthesizer") or moderator_agent_id
        
        # Get default agent ID if no specialized agents
        default_agent_id = context.get_input("agent_id")
        
        # Get task manager
        task_manager = context.get_service("task_manager")
        executor = context.get_service("enhanced_executor")
        
        # Get prompt template
        prompt_registry = get_registry()
        prompt_style = self.config.metadata.get("prompt_style", "default")
        
        # Step 1: Generate expert responses for each perspective
        expert_tasks = []
        for perspective in perspectives:
            try:
                # Get expert prompt template and render
                expert_template = prompt_registry.get_template(
                    "multi_agent.expert_panel", 
                    version=prompt_style
                )["expert"]["content"]
                
                # Replace variables
                expert_prompt = expert_template.replace("{perspective}", perspective)
                expert_prompt = expert_prompt.replace("{query}", query)
            except (ValueError, KeyError):
                # Fallback to default prompt if template not found
                expert_prompt = f"""You are an expert analyzing this question from the {perspective} perspective.
            
Question: {query}

Provide your analysis, insights, and recommendations from a {perspective} perspective.
Focus on the unique contributions and considerations that the {perspective} viewpoint brings to this issue.

{perspective} expert analysis:"""
            
            # Create the expert task
            expert_task = Task(
                name=f"Expert - {perspective}",
                description=f"Expert analysis from {perspective} perspective",
                input_data={"query": expert_prompt},
                agent_id=default_agent_id
            )
            
            # Save the task
            expert_task_id = await task_manager.save_task(expert_task)
            expert_tasks.append((perspective, expert_task_id))
        
        # Execute all expert tasks
        expert_results = {}
        for perspective, task_id in expert_tasks:
            result = await executor.execute_task(task_id)
            if result.status.value == "completed":
                expert_results[perspective] = result.output_data.get("result", "")
            else:
                expert_results[perspective] = f"[Failed to generate {perspective} perspective: {result.error}]"
        
        # Store expert results
        context.set_output("expert_opinions", expert_results)
        
        # Step 2: Synthesize expert insights
        try:
            # Get synthesis prompt template
            synthesis_template = prompt_registry.get_template(
                "multi_agent.expert_panel", 
                version=prompt_style
            )["synthesis"]["content"]
            
            # Format expert opinions text
            expert_opinions_text = ""
            for perspective, opinion in expert_results.items():
                expert_opinions_text += f"\n## {perspective.upper()} PERSPECTIVE:\n{opinion}\n\n"
            
            # Replace variables
            synthesis_prompt = synthesis_template.replace("{query}", query)
            synthesis_prompt = synthesis_prompt.replace("{expert_opinions}", expert_opinions_text)
        except (ValueError, KeyError):
            # Fallback to default prompt if template not found
            synthesis_prompt = f"""You are tasked with synthesizing the insights from multiple experts who have analyzed this question:

Question: {query}

The experts have provided the following perspectives:

"""
            
            # Add each expert's perspective
            for perspective, opinion in expert_results.items():
                synthesis_prompt += f"\n## {perspective.upper()} PERSPECTIVE:\n{opinion}\n\n"
            
            synthesis_prompt += """
Now, synthesize these diverse perspectives into a comprehensive analysis. Your synthesis should:
1. Identify common themes and insights across perspectives
2. Highlight unique contributions from each perspective
3. Note any contradictions or tensions between different viewpoints
4. Provide integrated recommendations that draw on the full range of expertise

Your synthesis:"""
        
        # Create the synthesis task
        synthesis_task = Task(
            name="Expert Panel Synthesis",
            description="Synthesize diverse expert perspectives",
            input_data={"query": synthesis_prompt},
            agent_id=synthesizer_agent_id or default_agent_id
        )
        
        # Execute the synthesis task
        synthesis_task_id = await task_manager.save_task(synthesis_task)
        synthesis_result = await executor.execute_task(synthesis_task_id)
        
        # Check for successful execution
        if synthesis_result.status.value != "completed":
            context.set_output("error", f"Synthesis failed: {synthesis_result.error}")
            context.set_output("synthesis", "[Failed to generate synthesis]")
            # Still return partial results (the expert opinions)
            return
            
        # Get synthesis
        synthesis = synthesis_result.output_data.get("result", "")
        
        # Set outputs
        context.set_output("synthesis", synthesis)
        context.set_output("response", synthesis)
        context.set_output("result", synthesis)  # For compatibility with other patterns
        
        # Add metadata
        context.metadata["num_perspectives"] = len(perspectives)
        context.metadata["perspectives"] = perspectives
        context.metadata["synthesis_task_id"] = synthesis_task_id
        context.metadata["prompt_style"] = prompt_style