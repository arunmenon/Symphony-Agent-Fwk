"""Unit tests for the workflow templates."""

import pytest
from unittest.mock import MagicMock

from symphony.orchestration.workflow_definition import WorkflowDefinition
from symphony.orchestration.steps import TaskStep, ConditionalStep, ParallelStep, LoopStep
from symphony.orchestration.templates import WorkflowTemplates


class TestWorkflowTemplates:
    """Tests for WorkflowTemplates class."""
    
    def test_chain_of_thought(self):
        """Test creating a chain-of-thought workflow."""
        # Create workflow with template
        workflow = WorkflowTemplates.chain_of_thought(
            name="Test Chain of Thought",
            initial_prompt="What is the meaning of life?",
            follow_up_questions=[
                "Why is that important?",
                "How can we apply this knowledge?"
            ],
            agent_id="test_agent_id"
        )
        
        # Verify workflow properties
        assert isinstance(workflow, WorkflowDefinition)
        assert workflow.name == "Test Chain of Thought"
        assert "Chain of thought reasoning workflow" in workflow.description
        
        # Get steps
        steps = workflow.get_steps()
        
        # Verify steps
        assert len(steps) == 3
        assert all(isinstance(step, TaskStep) for step in steps)
        
        # Verify initial step
        assert steps[0].name == "Initial Reasoning"
        assert steps[0].agent_id == "test_agent_id"
        assert "What is the meaning of life?" in steps[0].task_template["input_data"]["query"]
        
        # Verify follow-up steps
        assert steps[1].name == "Follow-up 1"
        assert "Why is that important?" in steps[1].task_template["input_data"]["query"]
        assert steps[2].name == "Follow-up 2"
        assert "How can we apply this knowledge?" in steps[2].task_template["input_data"]["query"]
        
        # Verify context references
        assert f"step.{steps[0].id}.result" in steps[1].task_template["input_data"]["query"]
        
    def test_critic_revise(self):
        """Test creating a critic-revision workflow."""
        # Create workflow with template
        workflow = WorkflowTemplates.critic_revise(
            name="Test Critic Revise",
            main_prompt="Write a short story about robots.",
            critique_prompt="Critique this story for plot, character development, and style.",
            revision_prompt="Revise the story based on the critique.",
            agent_id="writer_agent_id",
            critic_agent_id="critic_agent_id"
        )
        
        # Verify workflow properties
        assert isinstance(workflow, WorkflowDefinition)
        assert workflow.name == "Test Critic Revise"
        assert "Critic-revision workflow" in workflow.description
        
        # Get steps
        steps = workflow.get_steps()
        
        # Verify steps
        assert len(steps) == 3
        assert all(isinstance(step, TaskStep) for step in steps)
        
        # Verify initial step
        assert steps[0].name == "Initial Response"
        assert steps[0].agent_id == "writer_agent_id"
        assert "Write a short story about robots." in steps[0].task_template["input_data"]["query"]
        
        # Verify critique step
        assert steps[1].name == "Critique"
        assert steps[1].agent_id == "critic_agent_id"
        assert "Critique this story" in steps[1].task_template["input_data"]["query"]
        assert f"step.{steps[0].id}.result" in steps[1].task_template["input_data"]["query"]
        
        # Verify revision step
        assert steps[2].name == "Revision"
        assert steps[2].agent_id == "writer_agent_id"
        assert "Revise the story" in steps[2].task_template["input_data"]["query"]
        assert f"step.{steps[0].id}.result" in steps[2].task_template["input_data"]["query"]
        assert f"step.{steps[1].id}.result" in steps[2].task_template["input_data"]["query"]
        
    def test_parallel_experts(self):
        """Test creating a parallel experts workflow."""
        # Create workflow with template
        workflow = WorkflowTemplates.parallel_experts(
            name="Test Parallel Experts",
            prompt="How might climate change affect agriculture?",
            expert_roles=["Climate Scientist", "Agricultural Expert", "Economist"],
            summary_prompt="Synthesize the expert opinions into a comprehensive analysis.",
            expert_agent_ids=["climate_agent_id", "agriculture_agent_id", "economist_agent_id"]
        )
        
        # Verify workflow properties
        assert isinstance(workflow, WorkflowDefinition)
        assert workflow.name == "Test Parallel Experts"
        assert "Parallel experts workflow" in workflow.description
        
        # Get steps
        steps = workflow.get_steps()
        
        # Verify steps
        assert len(steps) == 2
        assert isinstance(steps[0], ParallelStep)
        assert isinstance(steps[1], TaskStep)
        
        # Verify parallel step
        parallel_step = steps[0]
        assert parallel_step.name == "Expert Consultation"
        assert len(parallel_step.steps) == 3
        
        # Verify expert steps
        expert_steps = parallel_step.steps
        assert expert_steps[0].name == "Expert: Climate Scientist"
        assert expert_steps[0].agent_id == "climate_agent_id"
        assert "As an expert in Climate Scientist" in expert_steps[0].task_template["input_data"]["query"]
        
        assert expert_steps[1].name == "Expert: Agricultural Expert"
        assert expert_steps[1].agent_id == "agriculture_agent_id"
        assert "As an expert in Agricultural Expert" in expert_steps[1].task_template["input_data"]["query"]
        
        assert expert_steps[2].name == "Expert: Economist"
        assert expert_steps[2].agent_id == "economist_agent_id"
        assert "As an expert in Economist" in expert_steps[2].task_template["input_data"]["query"]
        
        # Verify summary step
        summary_step = steps[1]
        assert summary_step.name == "Response Synthesis"
        assert "Synthesize the expert opinions" in summary_step.task_template["input_data"]["query"]
        assert f"step.{parallel_step.id}.results.0.result" in summary_step.task_template["input_data"]["query"]
        assert f"step.{parallel_step.id}.results.1.result" in summary_step.task_template["input_data"]["query"]
        assert f"step.{parallel_step.id}.results.2.result" in summary_step.task_template["input_data"]["query"]
        
    def test_iterative_refinement(self):
        """Test creating an iterative refinement workflow."""
        # Create workflow with template
        workflow = WorkflowTemplates.iterative_refinement(
            name="Test Iterative Refinement",
            initial_prompt="Draft a business proposal for a new app.",
            feedback_prompt="Review the current draft and suggest improvements.",
            max_iterations=5,
            convergence_condition="'excellent' in step.result.lower()",
            agent_id="business_agent_id"
        )
        
        # Verify workflow properties
        assert isinstance(workflow, WorkflowDefinition)
        assert workflow.name == "Test Iterative Refinement"
        assert "Iterative refinement workflow" in workflow.description
        
        # Get steps
        steps = workflow.get_steps()
        
        # Verify steps
        assert len(steps) == 2
        assert isinstance(steps[0], TaskStep)
        assert isinstance(steps[1], LoopStep)
        
        # Verify initial step
        initial_step = steps[0]
        assert initial_step.name == "Initial Response"
        assert initial_step.agent_id == "business_agent_id"
        assert "Draft a business proposal" in initial_step.task_template["input_data"]["query"]
        
        # Verify loop step
        loop_step = steps[1]
        assert loop_step.name == "Refinement Loop"
        assert loop_step.max_iterations == 5
        assert loop_step.exit_condition == "'excellent' in step.result.lower()"
        
        # Verify refinement step inside loop
        refinement_step = loop_step.step
        assert refinement_step.name == "Refinement"
        assert refinement_step.agent_id == "business_agent_id"
        assert "Review the current draft" in refinement_step.task_template["input_data"]["query"]
        assert f"step.{initial_step.id}.current_iteration" in refinement_step.task_template["input_data"]["query"]
        assert f"step.{initial_step.id}.iterations" in refinement_step.task_template["input_data"]["query"]