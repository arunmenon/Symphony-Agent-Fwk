"""Few-shot learning pattern for Symphony.

This module implements the few-shot learning pattern,
which uses examples to guide an agent's behavior.
"""

from typing import Dict, Any, List
import json

from symphony.patterns.base import Pattern, PatternContext


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
            
        # Prepare few-shot prompt
        few_shot_prompt = f"""
        Task: {task}
        
        {examples_text}
        {format_instructions}
        
        Input: {query}
        Output:
        """
        
        # Execute agent with few-shot prompt
        try:
            response = await agent_service.execute_agent(
                agent_role,
                few_shot_prompt
            )
            
            # Store result
            context.set_output("result", response)
            
        except Exception as e:
            context.set_output("error", f"Agent execution failed: {str(e)}")
            
    @classmethod
    def with_standard_examples(cls, config: Dict[str, Any], task_type: str, examples: List[Dict[str, Any]] = None) -> "FewShotPattern":
        """Create a few-shot pattern with standard examples.
        
        Args:
            config: Pattern configuration
            task_type: Type of task (summarization, classification, etc.)
            examples: Optional custom examples
            
        Returns:
            Few-shot pattern with standard examples
        """
        # Define standard examples for common tasks
        standard_examples = {
            "summarization": [
                {
                    "input": "The process of photosynthesis in plants involves capturing light energy to convert carbon dioxide and water into glucose and oxygen. This process takes place in the chloroplasts, primarily in the leaves. The glucose produced is used as energy for the plant's growth and functioning.",
                    "output": "Photosynthesis is the process where plants use light energy to convert CO2 and water into glucose and oxygen in their chloroplasts, providing energy for plant growth."
                },
                {
                    "input": "Machine learning is a subset of artificial intelligence that focuses on developing systems that learn from data. It involves algorithms that improve automatically through experience. Common applications include image recognition, recommendation systems, and natural language processing.",
                    "output": "Machine learning is an AI subset where systems use algorithms to learn from data and improve automatically, powering applications like image recognition and NLP."
                }
            ],
            "classification": [
                {
                    "input": "The customer service was excellent, and they resolved my issue quickly.",
                    "output": "Positive"
                },
                {
                    "input": "The product arrived broken and customer service never responded to my complaint.",
                    "output": "Negative"
                },
                {
                    "input": "The service was okay, not great but not terrible either.",
                    "output": "Neutral"
                }
            ],
            "extraction": [
                {
                    "input": "My name is John Smith and I need to schedule an appointment for March 15th at 2:30pm. My phone number is 555-123-4567.",
                    "output": "{'name': 'John Smith', 'date': '2023-03-15', 'time': '14:30', 'phone': '555-123-4567'}"
                },
                {
                    "input": "Please schedule a meeting with Jane Doe (jane.doe@example.com) next Monday at 10:00am to discuss the quarterly report.",
                    "output": "{'person': 'Jane Doe', 'email': 'jane.doe@example.com', 'day': 'Monday', 'time': '10:00', 'topic': 'quarterly report'}"
                }
            ]
        }
        
        # Use provided examples or fall back to standard examples
        task_examples = examples or standard_examples.get(task_type, [])
        
        # Include examples in config
        updated_config = config.copy()
        updated_config["metadata"] = updated_config.get("metadata", {})
        updated_config["metadata"]["task_type"] = task_type
        updated_config["metadata"]["examples"] = task_examples
        
        return cls(updated_config)