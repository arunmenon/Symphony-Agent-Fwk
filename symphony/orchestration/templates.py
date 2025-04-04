"""Workflow templates for Symphony orchestration.

This module provides predefined workflow patterns that can be used to create
common orchestration scenarios like chain-of-thought reasoning, critic-revision
cycles, and multi-agent collaboration.
"""

from typing import List, Dict, Any, Optional

from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.orchestration.steps import TaskStep, ConditionalStep, ParallelStep, LoopStep


class WorkflowTemplates:
    """Factory for common workflow patterns.
    
    This class provides factory methods for creating common workflow patterns
    that can be used as building blocks for more complex workflows.
    """
    
    @staticmethod
    def chain_of_thought(
            name: str, 
            initial_prompt: str, 
            follow_up_questions: List[str], 
            agent_id: Optional[str] = None) -> WorkflowDefinition:
        """Create a chain-of-thought reasoning workflow.
        
        This pattern implements a chain-of-thought reasoning process where an
        initial reasoning step is followed by a series of follow-up questions
        that build on previous answers.
        
        Args:
            name: Name of the workflow
            initial_prompt: The initial reasoning prompt
            follow_up_questions: List of follow-up questions to ask
            agent_id: Optional ID of agent to use for all steps
            
        Returns:
            A workflow definition for chain-of-thought reasoning
        """
        workflow = WorkflowDefinition(
            name=name, 
            description="Chain of thought reasoning workflow"
        )
        
        # Initial reasoning step
        initial_step = TaskStep(
            name="Initial Reasoning",
            description="First reasoning step to establish initial thoughts",
            task_template={
                "name": "Initial Reasoning",
                "description": "First reasoning step",
                "input_data": {
                    "query": initial_prompt
                }
            },
            agent_id=agent_id
        )
        
        # Add initial step to workflow
        workflow = workflow.add_step(initial_step)
        
        # Add follow-up steps
        for i, question in enumerate(follow_up_questions):
            follow_up_step = TaskStep(
                name=f"Follow-up {i+1}",
                description=f"Follow-up question {i+1} building on previous reasoning",
                task_template={
                    "name": f"Follow-up Question {i+1}",
                    "description": f"Follow-up question {i+1}",
                    "input_data": {
                        "query": f"{question}\n\nContext from previous steps:\n{{{{step.{initial_step.id}.result}}}}"
                    }
                },
                agent_id=agent_id
            )
            
            # Add follow-up step to workflow
            workflow = workflow.add_step(follow_up_step)
            
        return workflow
        
    @staticmethod
    def critic_revise(
            name: str, 
            main_prompt: str, 
            critique_prompt: str, 
            revision_prompt: str,
            agent_id: Optional[str] = None,
            critic_agent_id: Optional[str] = None) -> WorkflowDefinition:
        """Create a critic-revision workflow.
        
        This pattern implements a self-improvement process where an initial
        response is critiqued and then revised based on the critique.
        
        Args:
            name: Name of the workflow
            main_prompt: The main task prompt
            critique_prompt: Prompt for the critique step
            revision_prompt: Prompt for the revision step
            agent_id: Optional ID of agent for initial and revision steps
            critic_agent_id: Optional ID of agent for critique step
            
        Returns:
            A workflow definition for critic-revision process
        """
        workflow = WorkflowDefinition(
            name=name, 
            description="Critic-revision workflow"
        )
        
        # Initial attempt
        initial_step = TaskStep(
            name="Initial Response",
            description="Initial response to the prompt",
            task_template={
                "name": "Initial Response",
                "description": "Initial response to the prompt",
                "input_data": {
                    "query": main_prompt
                }
            },
            agent_id=agent_id
        )
        
        # Critique step
        critique_step = TaskStep(
            name="Critique",
            description="Critical evaluation of the initial response",
            task_template={
                "name": "Critique",
                "description": "Critique the initial response",
                "input_data": {
                    "query": f"{critique_prompt}\n\nOriginal response:\n{{{{step.{initial_step.id}.result}}}}"
                }
            },
            agent_id=critic_agent_id or agent_id
        )
        
        # Revision step
        revision_step = TaskStep(
            name="Revision",
            description="Revised response based on critique",
            task_template={
                "name": "Revision",
                "description": "Revise the initial response based on critique",
                "input_data": {
                    "query": f"{revision_prompt}\n\nOriginal response:\n{{{{step.{initial_step.id}.result}}}}\n\nCritique:\n{{{{step.{critique_step.id}.result}}}}"
                }
            },
            agent_id=agent_id
        )
        
        # Add steps to workflow
        workflow = workflow.add_step(initial_step)
        workflow = workflow.add_step(critique_step)
        workflow = workflow.add_step(revision_step)
        
        return workflow
    
    @staticmethod
    def parallel_experts(
            name: str,
            prompt: str,
            expert_roles: List[str],
            summary_prompt: str,
            expert_agent_ids: Optional[List[str]] = None) -> WorkflowDefinition:
        """Create a parallel experts workflow.
        
        This pattern asks multiple expert agents to solve a problem in parallel,
        then synthesizes their responses into a final answer.
        
        Args:
            name: Name of the workflow
            prompt: The main task prompt
            expert_roles: List of expert roles (used in prompts)
            summary_prompt: Prompt for synthesizing expert responses
            expert_agent_ids: Optional list of agent IDs for experts
            
        Returns:
            A workflow definition for parallel experts pattern
        """
        workflow = WorkflowDefinition(
            name=name, 
            description="Parallel experts workflow"
        )
        
        # Create expert steps
        expert_steps = []
        for i, role in enumerate(expert_roles):
            agent_id = None
            if expert_agent_ids and i < len(expert_agent_ids):
                agent_id = expert_agent_ids[i]
                
            expert_step = TaskStep(
                name=f"Expert: {role}",
                description=f"Response from {role} perspective",
                task_template={
                    "name": f"Expert: {role}",
                    "description": f"Response from {role} perspective",
                    "input_data": {
                        "query": f"As an expert in {role}, please respond to the following:\n\n{prompt}"
                    }
                },
                agent_id=agent_id
            )
            expert_steps.append(expert_step)
        
        # Create parallel step for experts
        parallel_step = ParallelStep(
            name="Expert Consultation",
            description="Parallel consultation with multiple experts",
            steps=expert_steps
        )
        
        # Create template for summary prompt that includes all expert responses
        summary_template = {
            "name": "Summary",
            "description": "Synthesize expert responses",
            "input_data": {
                "query": f"{summary_prompt}\n\nExpert Responses:\n"
            }
        }
        
        # Add expert responses to summary prompt
        for i, role in enumerate(expert_roles):
            summary_template["input_data"]["query"] += (
                f"\n## {role} Expert:\n"
                f"{{{{step.{parallel_step.id}.results.{i}.result}}}}\n"
            )
        
        # Create summary step
        summary_step = TaskStep(
            name="Response Synthesis",
            description="Synthesize expert responses into final answer",
            task_template=summary_template
        )
        
        # Add steps to workflow
        workflow = workflow.add_step(parallel_step)
        workflow = workflow.add_step(summary_step)
        
        return workflow
    
    @staticmethod
    def iterative_refinement(
            name: str,
            initial_prompt: str,
            feedback_prompt: str,
            max_iterations: int = 3,
            convergence_condition: str = "False",
            agent_id: Optional[str] = None) -> WorkflowDefinition:
        """Create an iterative refinement workflow.
        
        This pattern implements an iterative refinement process where a response
        is progressively improved based on feedback until either a maximum number
        of iterations is reached or a convergence condition is met.
        
        Args:
            name: Name of the workflow
            initial_prompt: The initial task prompt
            feedback_prompt: Prompt for generating feedback on previous iteration
            max_iterations: Maximum number of refinement iterations
            convergence_condition: Condition for early stopping
            agent_id: Optional ID of agent to use for all steps
            
        Returns:
            A workflow definition for iterative refinement
        """
        workflow = WorkflowDefinition(
            name=name, 
            description="Iterative refinement workflow"
        )
        
        # Initial step
        initial_step = TaskStep(
            name="Initial Response",
            description="Initial response to the prompt",
            task_template={
                "name": "Initial Response",
                "description": "Initial response",
                "input_data": {
                    "query": initial_prompt
                }
            },
            agent_id=agent_id
        )
        
        # Refinement step (will be executed in a loop)
        refinement_step = TaskStep(
            name="Refinement",
            description="Refined response based on feedback",
            task_template={
                "name": "Refinement",
                "description": "Refine previous response",
                "input_data": {
                    "query": f"{feedback_prompt}\n\nPrevious response (iteration {{{{step.{initial_step.id}.current_iteration}}}} of {max_iterations}):\n\n{{{{step.{initial_step.id}.iterations.{{{{step.{initial_step.id}.current_iteration}}}}.result}}}}"
                }
            },
            agent_id=agent_id
        )
        
        # Loop step for refinements
        loop_step = LoopStep(
            name="Refinement Loop",
            description=f"Iterative refinement (max {max_iterations} iterations)",
            step=refinement_step,
            exit_condition=convergence_condition,
            max_iterations=max_iterations
        )
        
        # Add steps to workflow
        workflow = workflow.add_step(initial_step)
        workflow = workflow.add_step(loop_step)
        
        return workflow