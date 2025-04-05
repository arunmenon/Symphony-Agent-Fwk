"""Self Consistency pattern.

This module implements the Self Consistency pattern,
which generates multiple responses and selects the most consistent one.
"""

from typing import Dict, Any, List, Optional
import json
import re
from collections import Counter

from symphony.patterns.base import Pattern, PatternContext, PatternConfig
from symphony.patterns.prompts import get_registry
from symphony.core.task import Task


class SelfConsistencyPattern(Pattern):
    """Self Consistency pattern.
    
    This pattern generates multiple responses to the same query
    and selects the most consistent answer, which can help with
    factual correctness and reliability.
    """
    
    async def execute(self, context: PatternContext) -> None:
        """Execute the self consistency pattern.
        
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
        
        # Get number of samples and threshold
        num_samples = min(self.config.metadata.get("num_samples", 3), 10)  # Limit to 10 max
        threshold = max(0.0, min(1.0, self.config.metadata.get("threshold", 0.7)))  # Clamp to [0.0, 1.0]
        
        # Get task manager
        task_manager = context.get_service("task_manager")
        executor = context.get_service("enhanced_executor")
        
        # Get prompt template
        prompt_registry = get_registry()
        prompt_style = self.config.metadata.get("prompt_style", "default")
        
        # Format the prompt to encourage clear answers
        try:
            # Get prompt template and render it with query
            prompt = prompt_registry.render_template(
                "verification.self_consistency",
                {"query": query},
                version=prompt_style
            )
        except ValueError:
            # Fallback to default prompt if template not found
            prompt = f"""Please answer the following question clearly and concisely:

{query}

Your answer:"""
        
        # Create and execute multiple tasks
        tasks = []
        for i in range(num_samples):
            task = Task(
                name=f"Self Consistency Sample {i+1}",
                description=f"Generate sample {i+1} for self-consistency",
                input_data={"query": prompt},
                agent_id=agent_id
            )
            task_id = await task_manager.save_task(task)
            tasks.append(task_id)
        
        # Execute all tasks
        results = []
        for task_id in tasks:
            result = await executor.execute_task(task_id)
            if result.status.value == "completed":
                results.append(result.output_data.get("result", ""))
        
        # Check if we have enough results
        if len(results) == 0:
            context.set_output("error", "All tasks failed to execute")
            return
        
        # Extract answers from results
        answers = [self._extract_answer(result) for result in results]
        
        # Count answer frequencies
        answer_counts = Counter(answers)
        most_common = answer_counts.most_common()
        
        # Calculate consistency score
        top_answer, top_count = most_common[0]
        consistency_score = top_count / len(answers)
        
        # Check if consistency score meets threshold
        is_consistent = consistency_score >= threshold
        
        # Set outputs
        context.set_output("samples", results)
        context.set_output("answers", answers)
        context.set_output("answer_counts", dict(answer_counts))
        context.set_output("top_answer", top_answer)
        context.set_output("consistency_score", consistency_score)
        context.set_output("is_consistent", is_consistent)
        context.set_output("response", top_answer)
        context.set_output("result", top_answer)  # For compatibility with other patterns
        
        # Add metadata
        context.metadata["num_samples"] = len(results)
        context.metadata["threshold"] = threshold
        context.metadata["is_consistent"] = is_consistent
    
    def _extract_answer(self, text: str) -> str:
        """Extract a clean answer from text.
        
        Args:
            text: Response text
            
        Returns:
            Cleaned answer
        """
        # Remove any explanations or reasoning
        lines = text.strip().split("\n")
        
        # If we have multiple lines, take the shortest non-empty line
        # that has more than 2 words (likely to be the direct answer)
        if len(lines) > 1:
            candidates = []
            for line in lines:
                line = line.strip()
                if line and len(line.split()) > 1:
                    candidates.append((len(line), line))
            
            if candidates:
                candidates.sort()
                return candidates[0][1]
        
        # Otherwise, use the first line or full text if it's just one line
        return lines[0].strip()