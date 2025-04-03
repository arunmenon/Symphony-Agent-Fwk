"""Integration tests for multi-agent orchestration."""

import pytest
import asyncio
from typing import Dict, List, Optional, Any
from unittest.mock import patch, MagicMock

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.agents.planning import PlanningAgent
from symphony.orchestration.base import AgentGroup, OrchestrationConfig
from symphony.llm.base import MockLLMClient


class TestAgentOrchestration:
    """Test suite for agent orchestration."""
    
    @pytest.fixture
    def planning_agent(self, mock_llm_client, prompt_registry):
        """Create a planning agent for testing."""
        # Extend mock responses for planning
        additional_responses = {
            "Create a plan to build a simple website": """
1. Define the website requirements
2. Design the website layout
3. Create HTML structure
4. Add CSS styling
5. Implement basic JavaScript functionality
6. Test the website
7. Deploy the website
            """,
            "Which agent should handle defining website requirements?": "Research Agent",
            "Which agent should handle designing website layout?": "Design Agent",
            "Which agent should handle creating HTML structure?": "Development Agent",
            "Which agent should handle adding CSS styling?": "Development Agent",
            "Which agent should handle implementing JavaScript?": "Development Agent",
            "Which agent should handle testing the website?": "QA Agent",
            "Which agent should handle deploying the website?": "DevOps Agent",
        }
        
        # Create new mock client with combined responses
        responses = {**mock_llm_client.responses, **additional_responses}
        planning_llm = MockLLMClient(responses=responses)
        
        config = AgentConfig(
            name="PlanningAgent",
            agent_type="planning",
            description="An agent that creates plans"
        )
        
        return PlanningAgent(
            config=config,
            llm_client=planning_llm,
            prompt_registry=prompt_registry
        )
    
    @pytest.fixture
    def agent_group(self, mock_llm_client, prompt_registry, planning_agent):
        """Create a group of agents for testing orchestration."""
        # Create specialized agents
        research_agent = ReactiveAgent(
            config=AgentConfig(
                name="ResearchAgent",
                agent_type="reactive",
                description="Handles research tasks"
            ),
            llm_client=mock_llm_client,
            prompt_registry=prompt_registry
        )
        
        design_agent = ReactiveAgent(
            config=AgentConfig(
                name="DesignAgent",
                agent_type="reactive",
                description="Handles design tasks"
            ),
            llm_client=mock_llm_client,
            prompt_registry=prompt_registry
        )
        
        dev_agent = ReactiveAgent(
            config=AgentConfig(
                name="DevelopmentAgent",
                agent_type="reactive", 
                description="Handles development tasks"
            ),
            llm_client=mock_llm_client,
            prompt_registry=prompt_registry
        )
        
        qa_agent = ReactiveAgent(
            config=AgentConfig(
                name="QAAgent",
                agent_type="reactive",
                description="Handles QA tasks"
            ),
            llm_client=mock_llm_client,
            prompt_registry=prompt_registry
        )
        
        devops_agent = ReactiveAgent(
            config=AgentConfig(
                name="DevOpsAgent",
                agent_type="reactive",
                description="Handles DevOps tasks"
            ),
            llm_client=mock_llm_client,
            prompt_registry=prompt_registry
        )
        
        # Create agent group
        agents = {
            "PlanningAgent": planning_agent,
            "ResearchAgent": research_agent,
            "DesignAgent": design_agent,
            "DevelopmentAgent": dev_agent,
            "QAAgent": qa_agent,
            "DevOpsAgent": devops_agent
        }
        
        orchestration_config = OrchestrationConfig(
            coordinator="PlanningAgent",
            max_iterations=10,
            timeout=60
        )
        
        return AgentGroup(
            agents=agents,
            config=orchestration_config
        )
    
    @pytest.mark.asyncio
    async def test_planning_agent_creates_plan(self, planning_agent):
        """Test that the planning agent can create a plan."""
        plan = await planning_agent.create_plan("Create a plan to build a simple website")
        
        # Check that we have a valid plan
        assert len(plan.steps) == 7
        assert plan.steps[0].description == "Define the website requirements"
        assert plan.steps[0].assigned_agent == "Research Agent"
        assert plan.steps[1].description == "Design the website layout"
        assert plan.steps[1].assigned_agent == "Design Agent"
        
        # Check the full plan
        expected_assignments = [
            "Research Agent",
            "Design Agent",
            "Development Agent",
            "Development Agent",
            "Development Agent",
            "QA Agent",
            "DevOps Agent"
        ]
        
        for i, step in enumerate(plan.steps):
            assert step.assigned_agent == expected_assignments[i]
    
    @pytest.mark.asyncio
    async def test_agent_group_execution(self, agent_group):
        """Test that the agent group can execute a task."""
        result = await agent_group.execute_task("Create a plan to build a simple website")
        
        # Check overall result
        assert result.success is True
        assert result.coordinator_agent == "PlanningAgent"
        
        # Check plan details
        assert len(result.plan.steps) == 7
        assert result.plan.steps[0].description == "Define the website requirements"
        
        # Check step results
        assert len(result.step_results) == 7
        
        # Each step should have been completed by the right agent
        expected_agents = [
            "ResearchAgent",
            "DesignAgent",
            "DevelopmentAgent",
            "DevelopmentAgent",
            "DevelopmentAgent",
            "QAAgent",
            "DevOpsAgent"
        ]
        
        for i, step_result in enumerate(result.step_results):
            assert step_result.agent_name == expected_agents[i]
            assert step_result.success is True
    
    @pytest.mark.asyncio
    async def test_agent_group_handles_failures(self, agent_group):
        """Test that the agent group can handle failures."""
        # Patch one agent to simulate failure
        dev_agent = agent_group.agents["DevelopmentAgent"]
        original_run = dev_agent.run
        
        async def failing_run(input_str):
            if "HTML" in input_str:
                raise Exception("Failed to create HTML structure")
            return await original_run(input_str)
        
        with patch.object(dev_agent, 'run', side_effect=failing_run):
            result = await agent_group.execute_task("Create a plan to build a simple website")
            
            # Overall execution should still finish but with some failures
            assert len(result.step_results) == 7
            
            # The HTML step should have failed
            html_step_result = result.step_results[2]  # 3rd step is HTML
            assert html_step_result.success is False
            assert "Failed to create HTML structure" in html_step_result.error