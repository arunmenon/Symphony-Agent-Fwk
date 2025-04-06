"""Few-shot learning pattern for Symphony.

This module implements the few-shot learning pattern,
which uses examples to guide an agent's behavior.
"""

from typing import Dict, Any, List
import json
import yaml
import os

from symphony.patterns.base import Pattern, PatternContext
from symphony.patterns.prompts import get_registry


class FewShotPattern(Pattern):
    """Few-shot learning pattern.
    
    This pattern uses examples to guide an agent's behavior
    for improved performance on specific tasks.
    """
    
    async def execute(self, context: PatternContext) -> None:
        """Execute the few-shot learning pattern.
        
        Args:
            context: Execution context
                
        Inputs:
            task: Description of the task
            examples: List of examples, each with input and output
            query: The input query to process
            format_instructions: Optional formatting instructions
            
        Outputs:
            result: The result of applying the pattern
        """
        # Get inputs
        task = context.get_input("task")
        examples = context.get_input("examples", [])
        query = context.get_input("query")
        format_instructions = context.get_input("format_instructions", "")
        
        if not task or not query:
            context.set_output("error", "Task and query are required")
            return
            
        # Get agent service
        agent_service = context.get_service("agent_manager")
        if not agent_service:
            context.set_output("error", "Agent service not found")
            return
        
        # Get agent role
        agent_role = self.config.agent_roles.get("performer")
        if not agent_role:
            context.set_output("error", "Agent role not configured")
            return
            
        # Format examples
        examples_text = ""
        for i, example in enumerate(examples):
            # Validate example format
            if not isinstance(example, dict) or "input" not in example or "output" not in example:
                continue
                
            examples_text += f"Example {i+1}:\nInput: {example['input']}\nOutput: {example['output']}\n\n"
        
        # Get prompt template
        prompt_registry = get_registry()
        prompt_style = self.config.metadata.get("prompt_style", "default")
        
        # Prepare few-shot prompt
        few_shot_prompt = prompt_registry.render_template(
            "learning.few_shot",
            {
                "task": task,
                "examples_text": examples_text,
                "format_instructions": format_instructions,
                "query": query
            },
            version=prompt_style
        )
        
        # Execute agent with few-shot prompt
        try:
            response = await agent_service.execute_agent(
                agent_role,
                few_shot_prompt
            )
            
            # Store result
            context.set_output("result", response)
            
            # Add metadata
            context.metadata["prompt_style"] = prompt_style
            context.metadata["num_examples"] = len(examples)
            
        except Exception as e:
            context.set_output("error", f"Agent execution failed: {str(e)}")
            
    @classmethod
    def with_standard_examples(cls, config: Dict[str, Any], task_type: str, 
                              examples: List[Dict[str, Any]] = None,
                              prompt_style: str = "default") -> "FewShotPattern":
        """Create a few-shot pattern with standard examples.
        
        Args:
            config: Pattern configuration
            task_type: Type of task (summarization, classification, etc.)
            examples: Optional custom examples
            prompt_style: Style of prompt to use (default, concise, academic, etc.)
            
        Returns:
            Few-shot pattern with standard examples
        """
        # Try to load standard examples from the template file
        standard_examples = {}
        prompt_registry = get_registry()
        template_data = prompt_registry.get_template("learning.few_shot")
        
        # Extract standard examples from template
        standard_examples = template_data["standard_examples"]
        
        # Use provided examples or fall back to standard examples
        task_examples = examples or standard_examples.get(task_type, [])
        
        # Include examples in config
        updated_config = config.copy()
        updated_config["metadata"] = updated_config.get("metadata", {})
        updated_config["metadata"]["task_type"] = task_type
        updated_config["metadata"]["examples"] = task_examples
        updated_config["metadata"]["prompt_style"] = prompt_style
        
        return cls(updated_config)