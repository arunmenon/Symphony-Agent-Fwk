"""Integration tests for the orchestration layer."""

import pytest
import os
import json
import asyncio
from unittest.mock import AsyncMock, patch

from symphony.core.registry import ServiceRegistry
from symphony.core.task import Task
from symphony.core.agent_config import AgentConfig, AgentCapabilities 
from symphony.agents.base import Agent
from symphony.execution.workflow_tracker import Workflow, WorkflowStatus
from symphony.orchestration.workflow_definition import WorkflowDefinition, WorkflowContext
from symphony.orchestration.steps import TaskStep, ConditionalStep, ParallelStep
from symphony.orchestration.templates import WorkflowTemplates
from symphony.persistence.memory_repository import InMemoryRepository
from symphony.orchestration import register_orchestration_components


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, name):
        self.name = name
        self.run_calls = []
        
    async def run(self, task_input):
        """Mock run method that returns a predefined result based on the task."""
        self.run_calls.append(task_input)
        
        if "reasoning" in task_input.lower() or "thinking" in task_input.lower():
            return "I've thought deeply about this problem and here's my reasoning..."
        elif "math" in task_input.lower():
            return "The answer to the math problem is 42."
        elif "write" in task_input.lower():
            return "Here's the content I've written as requested."
        elif "critique" in task_input.lower() or "review" in task_input.lower():
            return "Here's my critique: The content could be improved by..."
        elif "revise" in task_input.lower() or "improve" in task_input.lower():
            return "Here's the revised content with improvements..."
        else:
            return f"Response to: {task_input}"


@pytest.fixture
async def setup_registry():
    """Set up a registry with mocked components for testing."""
    # Create a fresh registry
    registry = ServiceRegistry()
    
    # Create repositories
    task_repo = InMemoryRepository(Task)
    workflow_repo = InMemoryRepository(Workflow)
    agent_config_repo = InMemoryRepository(AgentConfig)
    workflow_def_repo = InMemoryRepository(WorkflowDefinition)
    
    # Register repositories
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("workflow_definition", workflow_def_repo)
    
    # Create mocked agents
    general_agent = MockAgent("General Agent")
    specialist_agent = MockAgent("Specialist Agent")
    critic_agent = MockAgent("Critic Agent")
    
    # Create agent configurations
    general_config = AgentConfig(
        name="GeneralAgent",
        role="General Assistant",
        instruction_template="You are a helpful general assistant.",
        capabilities=AgentCapabilities(
            expertise=["general", "writing", "creativity"]
        )
    )
    
    specialist_config = AgentConfig(
        name="SpecialistAgent",
        role="Specialist",
        instruction_template="You are a specialist in specific domains.",
        capabilities=AgentCapabilities(
            expertise=["specialized", "technical", "analysis"]
        )
    )
    
    critic_config = AgentConfig(
        name="CriticAgent",
        role="Critic",
        instruction_template="You are a critical reviewer who provides feedback.",
        capabilities=AgentCapabilities(
            expertise=["critique", "review", "editing"]
        )
    )
    
    # Save agent configurations
    await agent_config_repo.save(general_config)
    await agent_config_repo.save(specialist_config)
    await agent_config_repo.save(critic_config)
    
    # Mock agent factory
    agent_factory = AsyncMock()
    agent_factory.create_agent_from_id.side_effect = lambda agent_id: asyncio.Future().set_result(
        general_agent if agent_id == general_config.id else
        specialist_agent if agent_id == specialist_config.id else
        critic_agent
    )
    
    # Register agent factory
    registry.register_service("agent_factory", agent_factory)
    
    # Register orchestration components
    register_orchestration_components(registry)
    
    # Return registry and agent instances
    return {
        "registry": registry,
        "general_agent": general_agent,
        "specialist_agent": specialist_agent,
        "critic_agent": critic_agent,
        "general_config": general_config,
        "specialist_config": specialist_config,
        "critic_config": critic_config
    }


class TestOrchestrationLayerIntegration:
    """Integration tests for the orchestration layer."""
    
    @pytest.mark.asyncio
    async def test_workflow_execution_with_context_passing(self, setup_registry):
        """Test workflow execution with context passing between steps."""
        registry = setup_registry["registry"]
        general_config = setup_registry["general_config"]
        
        # Create workflow definition
        workflow_def = WorkflowDefinition(
            name="Context Passing Test",
            description="Tests context passing between steps"
        )
        
        # Step 1: Initial reasoning
        step1 = TaskStep(
            name="Initial Reasoning",
            description="First reasoning step",
            task_template={
                "name": "Initial Reasoning",
                "description": "First reasoning step",
                "input_data": {
                    "query": "Think about the problem of climate change."
                }
            },
            agent_id=general_config.id
        )
        
        # Step 2: Follow-up that uses context from step 1
        step2 = TaskStep(
            name="Follow-up",
            description="Follow-up using previous reasoning",
            task_template={
                "name": "Follow-up",
                "description": "Follow-up question using previous reasoning",
                "input_data": {
                    "query": f"Based on the reasoning: {{{{step.{step1.id}.result}}}} - What actions can individuals take?"
                }
            },
            agent_id=general_config.id
        )
        
        # Add steps to workflow
        workflow_def = workflow_def.add_step(step1)
        workflow_def = workflow_def.add_step(step2)
        
        # Save workflow definition
        workflow_def_repo = registry.get_repository("workflow_definition")
        await workflow_def_repo.save(workflow_def)
        
        # Execute workflow
        workflow_engine = registry.get_service("workflow_engine")
        workflow = await workflow_engine.execute_workflow(workflow_def)
        
        # Verify workflow completed successfully
        assert workflow.status == WorkflowStatus.COMPLETED
        
        # Verify context was passed correctly
        context = workflow.metadata.get("context", {})
        step1_result = context.get(f"step.{step1.id}.result")
        assert step1_result is not None
        
        step2_input = setup_registry["general_agent"].run_calls[1]
        assert step1_result in step2_input
    
    @pytest.mark.asyncio
    async def test_conditional_workflow_execution(self, setup_registry):
        """Test workflow with conditional execution."""
        registry = setup_registry["registry"]
        general_config = setup_registry["general_config"]
        specialist_config = setup_registry["specialist_config"]
        
        # Create workflow definition
        workflow_def = WorkflowDefinition(
            name="Conditional Workflow Test",
            description="Tests conditional execution of steps"
        )
        
        # Step 1: Classification
        step1 = TaskStep(
            name="Classification",
            description="Classify the problem type",
            task_template={
                "name": "Classification",
                "description": "Classify if this is a technical or general problem",
                "input_data": {
                    "query": "Is the following a technical or general problem? Answer only with 'TECHNICAL' or 'GENERAL': How to implement a recursive algorithm?"
                }
            },
            agent_id=general_config.id
        )
        
        # Step 2a: Technical solution
        technical_step = TaskStep(
            name="Technical Solution",
            description="Provide technical solution",
            task_template={
                "name": "Technical Solution",
                "description": "Provide technical solution",
                "input_data": {
                    "query": "Provide a technical solution for implementing a recursive algorithm."
                }
            },
            agent_id=specialist_config.id
        )
        
        # Step 2b: General solution
        general_step = TaskStep(
            name="General Solution",
            description="Provide general guidance",
            task_template={
                "name": "General Solution",
                "description": "Provide general guidance",
                "input_data": {
                    "query": "Provide general guidance on understanding recursive algorithms."
                }
            },
            agent_id=general_config.id
        )
        
        # Conditional step
        conditional_step = ConditionalStep(
            name="Solution Path",
            description="Choose solution based on classification",
            condition=f"'TECHNICAL' in step.{step1.id}.result.upper()",
            if_branch=technical_step,
            else_branch=general_step
        )
        
        # Add steps to workflow
        workflow_def = workflow_def.add_step(step1)
        workflow_def = workflow_def.add_step(conditional_step)
        
        # Save workflow definition
        workflow_def_repo = registry.get_repository("workflow_definition")
        await workflow_def_repo.save(workflow_def)
        
        # Execute workflow
        workflow_engine = registry.get_service("workflow_engine")
        workflow = await workflow_engine.execute_workflow(workflow_def)
        
        # Verify workflow completed successfully
        assert workflow.status == WorkflowStatus.COMPLETED
        
        # Verify correct branch was executed
        context = workflow.metadata.get("context", {})
        classification = context.get(f"step.{step1.id}.result", "")
        
        # Mock always returns "Response to:" for unrecognized queries, which doesn't contain "TECHNICAL"
        # So the else branch (general_step) should be executed
        branch_taken = context.get(f"step.{conditional_step.id}.branch_taken")
        assert branch_taken is not None
        
        if "TECHNICAL" in classification.upper():
            assert branch_taken == "if"
            assert setup_registry["specialist_agent"].run_calls
        else:
            assert branch_taken == "else"
            assert len(setup_registry["general_agent"].run_calls) >= 2
    
    @pytest.mark.asyncio  
    async def test_parallel_workflow_execution(self, setup_registry):
        """Test workflow with parallel execution."""
        registry = setup_registry["registry"]
        general_config = setup_registry["general_config"]
        specialist_config = setup_registry["specialist_config"]
        critic_config = setup_registry["critic_config"]
        
        # Create workflow definition
        workflow_def = WorkflowDefinition(
            name="Parallel Workflow Test",
            description="Tests parallel execution of steps"
        )
        
        # Step 1: Initial content
        step1 = TaskStep(
            name="Initial Content",
            description="Create initial content",
            task_template={
                "name": "Create Content",
                "description": "Create initial content",
                "input_data": {
                    "query": "Write a short paragraph about machine learning."
                }
            },
            agent_id=general_config.id
        )
        
        # Step 2a: Technical review
        technical_review = TaskStep(
            name="Technical Review",
            description="Review content for technical accuracy",
            task_template={
                "name": "Technical Review",
                "description": "Review for technical accuracy",
                "input_data": {
                    "query": f"Review this content for technical accuracy: {{{{step.{step1.id}.result}}}}"
                }
            },
            agent_id=specialist_config.id
        )
        
        # Step 2b: Writing style review
        style_review = TaskStep(
            name="Style Review",
            description="Review writing style",
            task_template={
                "name": "Style Review",
                "description": "Review writing style",
                "input_data": {
                    "query": f"Review this content for writing style: {{{{step.{step1.id}.result}}}}"
                }
            },
            agent_id=critic_config.id
        )
        
        # Parallel step for reviews
        parallel_step = ParallelStep(
            name="Parallel Reviews",
            description="Parallel reviews of content",
            steps=[technical_review, style_review]
        )
        
        # Step 3: Final revision
        final_step = TaskStep(
            name="Final Revision",
            description="Revise content based on reviews",
            task_template={
                "name": "Final Revision",
                "description": "Revise based on reviews",
                "input_data": {
                    "query": f"""Revise this content based on these reviews:
                    
Original: {{{{step.{step1.id}.result}}}}

Technical Review: {{{{step.{parallel_step.id}.results.0.result}}}}

Style Review: {{{{step.{parallel_step.id}.results.1.result}}}}"""
                }
            },
            agent_id=general_config.id
        )
        
        # Add steps to workflow
        workflow_def = workflow_def.add_step(step1)
        workflow_def = workflow_def.add_step(parallel_step)
        workflow_def = workflow_def.add_step(final_step)
        
        # Save workflow definition
        workflow_def_repo = registry.get_repository("workflow_definition")
        await workflow_def_repo.save(workflow_def)
        
        # Execute workflow
        workflow_engine = registry.get_service("workflow_engine")
        workflow = await workflow_engine.execute_workflow(workflow_def)
        
        # Verify workflow completed successfully
        assert workflow.status == WorkflowStatus.COMPLETED
        
        # Verify parallel steps executed
        context = workflow.metadata.get("context", {})
        
        parallel_results = context.get(f"step.{parallel_step.id}.results")
        assert parallel_results is not None
        
        # Verify final step received all inputs
        final_result = context.get(f"step.{final_step.id}.result")
        assert final_result is not None
        
        # Verify all agents were called appropriately
        assert len(setup_registry["general_agent"].run_calls) >= 2  # Initial content + final revision
        assert len(setup_registry["specialist_agent"].run_calls) >= 1  # Technical review
        assert len(setup_registry["critic_agent"].run_calls) >= 1  # Style review
    
    @pytest.mark.asyncio
    async def test_workflow_template_execution(self, setup_registry):
        """Test execution of workflow created from template."""
        registry = setup_registry["registry"]
        general_config = setup_registry["general_config"]
        critic_config = setup_registry["critic_config"]
        
        # Get workflow templates
        templates = registry.get_service("workflow_templates")
        
        # Create a critic-revise workflow
        workflow_def = templates.critic_revise(
            name="Critic-Revise Test",
            main_prompt="Write a short explanation of how neural networks work.",
            critique_prompt="Critique this explanation for clarity, accuracy, and completeness.",
            revision_prompt="Revise the explanation based on the critique.",
            agent_id=general_config.id,
            critic_agent_id=critic_config.id
        )
        
        # Save workflow definition
        workflow_def_repo = registry.get_repository("workflow_definition")
        await workflow_def_repo.save(workflow_def)
        
        # Execute workflow
        workflow_engine = registry.get_service("workflow_engine")
        workflow = await workflow_engine.execute_workflow(workflow_def)
        
        # Verify workflow completed successfully
        assert workflow.status == WorkflowStatus.COMPLETED
        
        # Verify context contains expected data from all steps
        context = workflow.metadata.get("context", {})
        
        steps = workflow_def.get_steps()
        initial_response = context.get(f"step.{steps[0].id}.result")
        critique = context.get(f"step.{steps[1].id}.result")
        revision = context.get(f"step.{steps[2].id}.result")
        
        assert initial_response is not None
        assert critique is not None
        assert revision is not None
        
        # Verify agents were called appropriately
        assert len(setup_registry["general_agent"].run_calls) >= 2  # Initial + revision
        assert len(setup_registry["critic_agent"].run_calls) >= 1  # Critique