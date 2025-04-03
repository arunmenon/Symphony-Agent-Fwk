"""Unit tests for base agent functionality."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.base import MockLLMClient


class TestReactiveAgent:
    """Test suite for ReactiveAgent."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_llm_client, prompt_registry):
        """Test that the agent initializes correctly."""
        config = AgentConfig(
            name="TestAgent",
            agent_type="reactive",
            description="A test agent"
        )
        
        agent = ReactiveAgent(
            config=config,
            llm_client=mock_llm_client,
            prompt_registry=prompt_registry
        )
        
        assert agent.name == "TestAgent"
        assert agent.agent_type == "reactive"
        assert agent.description == "A test agent"
        assert agent.llm_client == mock_llm_client
        assert agent.prompt_registry == prompt_registry
        assert agent.system_prompt == "You are a helpful assistant for testing purposes."
    
    @pytest.mark.asyncio
    async def test_agent_run(self, reactive_agent):
        """Test that the agent can run a simple query."""
        response = await reactive_agent.run("Hello")
        assert response == "Hi there!"
        
        response = await reactive_agent.run("What is your name?")
        assert response == "I am Symphony, a test agent."
    
    @pytest.mark.asyncio
    async def test_agent_with_custom_system_prompt(self, mock_llm_client, prompt_registry):
        """Test that the agent uses a custom system prompt."""
        config = AgentConfig(
            name="CustomAgent",
            agent_type="reactive",
            description="A custom agent"
        )
        
        agent = ReactiveAgent(
            config=config,
            llm_client=mock_llm_client,
            prompt_registry=prompt_registry,
            system_prompt="You are a custom agent for testing."
        )
        
        assert agent.system_prompt == "You are a custom agent for testing."
    
    @pytest.mark.asyncio
    async def test_agent_with_memory(self, reactive_agent, vector_memory):
        """Test that the agent can use memory."""
        # Add memory to the agent
        reactive_agent.memory = vector_memory
        
        # Store something in memory
        await vector_memory.store("test_key", "test_value")
        
        # Check that the agent can access memory
        assert hasattr(reactive_agent, "memory")
        assert await reactive_agent.memory.retrieve("test_key") == "test_value"
    
    @pytest.mark.asyncio
    async def test_agent_with_tools(self, reactive_agent, mock_tool):
        """Test that the agent can use tools."""
        # Add tool to the agent
        reactive_agent.register_tool(mock_tool)
        
        # Check that the agent has the tool
        assert hasattr(reactive_agent, "tools")
        assert len(reactive_agent.tools) == 1
        assert reactive_agent.tools[0].name == "mock_tool"
        
        # Check that the agent can use the tool
        result = await reactive_agent.execute_tool(
            "mock_tool",
            param1="test",
            param2=42
        )
        
        assert "Executed mock tool with args" in result
        assert mock_tool.call_count == 1
        assert mock_tool.last_args["param1"] == "test"
        assert mock_tool.last_args["param2"] == 42