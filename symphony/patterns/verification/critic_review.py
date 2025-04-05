"""Critic Review Revise pattern.

This module implements the Critic Review Revise pattern,
which uses specialized agents for critique and revision.
"""

from typing import Dict, Any, List, Optional
import json

from symphony.patterns.base import Pattern, PatternContext, PatternConfig
from symphony.core.task import Task
from symphony.patterns.prompts import get_registry


class CriticReviewPattern(Pattern):
    """Critic Review Revise pattern.
    
    This pattern uses a multi-agent approach with specialized roles:
    1. Creator - Creates the initial content
    2. Critic - Reviews the content and provides feedback
    3. Reviser - Revises the content based on the feedback
    """
    
    async def execute(self, context: PatternContext) -> None:
        """Execute the critic review revise pattern.
        
        Args:
            context: Pattern execution context
            
        Returns:
            None
        """
        # Get inputs
        content = context.get_input("content")
        query = context.get_input("query")
        criteria = context.get_input("criteria", [])
        
        # Initial content can come from input or need to be generated
        has_initial_content = bool(content)
        
        # Get agent IDs from config
        creator_agent_id = self.config.agent_roles.get("creator")
        critic_agent_id = self.config.agent_roles.get("critic")
        reviser_agent_id = self.config.agent_roles.get("reviser")
        
        # If no separate reviser, use creator
        if not reviser_agent_id:
            reviser_agent_id = creator_agent_id
        
        # Get task manager
        task_manager = context.get_service("task_manager")
        executor = context.get_service("enhanced_executor")
        
        # Get prompt template registry
        prompt_registry = get_registry()
        prompt_style = self.config.metadata.get("prompt_style", "default")
        
        # Step 1: Create initial content if not provided
        if not has_initial_content:
            if not query:
                context.set_output("error", "No content or query provided")
                return
                
            if not creator_agent_id:
                context.set_output("error", "No creator agent specified")
                return
                
            # Create the content creation task
            creation_task = Task(
                name="Content Creation",
                description="Create initial content",
                input_data={"query": query},
                agent_id=creator_agent_id
            )
            
            # Execute the task
            creation_task_id = await task_manager.save_task(creation_task)
            creation_result = await executor.execute_task(creation_task_id)
            
            # Check for successful execution
            if creation_result.status.value != "completed":
                context.set_output("error", f"Content creation failed: {creation_result.error}")
                return
                
            # Get created content
            content = creation_result.output_data.get("result", "")
            context.set_output("original_content", content)
        else:
            context.set_output("original_content", content)
        
        # Step 2: Critic review
        if not critic_agent_id:
            context.set_output("error", "No critic agent specified")
            return
            
        # Format criteria if provided
        criteria_text = ""
        if criteria:
            criteria_text = "Focus on these specific criteria:\n" + "\n".join([f"- {c}" for c in criteria])
        
        try:
            # Get critic prompt template
            critic_prompt_template = prompt_registry.get_template(
                "verification.critic_review",
                version=prompt_style
            )["critic"]["content"]
            
            # Replace variables
            critic_prompt = critic_prompt_template.replace("{content}", content)
            critic_prompt = critic_prompt.replace("{criteria_text}", criteria_text)
        except (ValueError, KeyError):
            # Fallback to default prompt if template not found
            critic_prompt = f"""Review the following content critically. Identify issues, errors, or areas for improvement.
{criteria_text}

Content to review:
{content}

Critical review:"""
        
        critic_task = Task(
            name="Critical Review",
            description="Review content critically",
            input_data={"query": critic_prompt},
            agent_id=critic_agent_id
        )
        
        # Execute the task
        critic_task_id = await task_manager.save_task(critic_task)
        critic_result = await executor.execute_task(critic_task_id)
        
        # Check for successful execution
        if critic_result.status.value != "completed":
            context.set_output("error", f"Critical review failed: {critic_result.error}")
            return
            
        # Get criticism
        criticism = critic_result.output_data.get("result", "")
        context.set_output("critique", criticism)
        
        # Step 3: Revision based on critique
        if not reviser_agent_id:
            context.set_output("error", "No reviser agent specified")
            return
        
        try:
            # Get revision prompt template
            revision_prompt_template = prompt_registry.get_template(
                "verification.critic_review",
                version=prompt_style
            )["revision"]["content"]
            
            # Replace variables
            revision_prompt = revision_prompt_template.replace("{content}", content)
            revision_prompt = revision_prompt.replace("{criticism}", criticism)
        except (ValueError, KeyError):
            # Fallback to default prompt if template not found
            revision_prompt = f"""Revise the following content based on the critical feedback.

Original content:
{content}

Critical feedback:
{criticism}

Revised content:"""
        
        revision_task = Task(
            name="Content Revision",
            description="Revise content based on feedback",
            input_data={"query": revision_prompt},
            agent_id=reviser_agent_id
        )
        
        # Execute the task
        revision_task_id = await task_manager.save_task(revision_task)
        revision_result = await executor.execute_task(revision_task_id)
        
        # Check for successful execution
        if revision_result.status.value != "completed":
            context.set_output("error", f"Content revision failed: {revision_result.error}")
            return
            
        # Get revised content
        revised_content = revision_result.output_data.get("result", "")
        
        # Set outputs
        context.set_output("revised_content", revised_content)
        context.set_output("response", revised_content)
        context.set_output("result", revised_content)  # For compatibility with other patterns
        
        # Extract issues from criticism
        issues = self._extract_issues(criticism)
        context.set_output("issues", issues)
        
        # Add metadata
        context.metadata["had_initial_content"] = has_initial_content
        context.metadata["critic_task_id"] = critic_task_id
        context.metadata["revision_task_id"] = revision_task_id
        context.metadata["prompt_style"] = prompt_style
        if not has_initial_content:
            context.metadata["creation_task_id"] = creation_task_id
    
    def _extract_issues(self, criticism: str) -> List[str]:
        """Extract issues from criticism text.
        
        Args:
            criticism: Criticism text
            
        Returns:
            List of issues
        """
        lines = criticism.split("\n")
        issues = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for bullet points, numbers, etc.
            if line.startswith("-") or line.startswith("*") or (line[0].isdigit() and line[1:3] in [". ", ") "]):
                issues.append(line[line.find(" ")+1:].strip())
            elif len(issues) == 0 or (len(line) > 20 and "." in line):
                # If no issues found yet or this looks like a substantial standalone sentence
                issues.append(line)
                
        return issues