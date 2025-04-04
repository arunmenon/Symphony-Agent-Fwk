"""Unit tests for the Symphony factory classes."""

import pytest
from unittest.mock import MagicMock, patch

from symphony.core.factory import (
    AgentFactory, 
    LLMClientFactory, 
    MemoryFactory, 
    MCPManagerFactory
)

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.base import MockLLMClient
from symphony.llm.litellm_client import LiteLLMConfig, LiteLLMClient
from symphony.memory.base import ConversationMemory
from symphony.mcp.base import MCPConfig, MCPManager


class TestAgentFactory:
    """Test suite for the AgentFactory class."""
    
    def test_register_agent_type(self):
        """Test registering a new agent type."""
        # Create a mock agent class
        MockAgent = MagicMock()
        
        # Register it
        initial_count = len(AgentFactory._agent_types)
        AgentFactory.register_agent_type("mock_agent", MockAgent)
        
        # Check it was registered
        assert len(AgentFactory._agent_types) == initial_count + 1
        assert AgentFactory._agent_types["mock_agent"] is MockAgent
        
        # Clean up
        del AgentFactory._agent_types["mock_agent"]
    
    @patch('symphony.agents.base.ReactiveAgent')
    def test_create_reactive_agent(self, MockReactiveAgent):
        """Test creating a reactive agent."""
        # Set up test data
        config = AgentConfig(
            name="TestAgent",
            agent_type="reactive",
            description="A test agent"
        )
        llm_client = MagicMock()
        prompt_registry = MagicMock()
        memory = MagicMock()
        mcp_manager = MagicMock()
        
        # Create the agent
        agent = AgentFactory.create(
            config=config,
            llm_client=llm_client,
            prompt_registry=prompt_registry,
            memory=memory,
            mcp_manager=mcp_manager
        )
        
        # Check the agent was created with the correct parameters
        MockReactiveAgent.assert_called_once_with(
            config=config,
            llm_client=llm_client,
            prompt_registry=prompt_registry,
            memory=memory,
            mcp_manager=mcp_manager
        )
    
    def test_create_unknown_agent_type(self):
        """Test creating an agent with an unknown type."""
        config = AgentConfig(
            name="TestAgent",
            agent_type="unknown",
            description="A test agent"
        )
        llm_client = MagicMock()
        prompt_registry = MagicMock()
        
        # Should raise ValueError
        with pytest.raises(ValueError) as excinfo:
            AgentFactory.create(
                config=config,
                llm_client=llm_client,
                prompt_registry=prompt_registry
            )
        
        assert "Unknown agent type" in str(excinfo.value)


class TestLLMClientFactory:
    """Test suite for the LLMClientFactory class."""
    
    def test_create_mock(self):
        """Test creating a mock LLM client."""
        responses = {"test": "response"}
        client = LLMClientFactory.create_mock(responses=responses)
        
        assert isinstance(client, MockLLMClient)
        assert client.responses == responses
    
    @patch('symphony.llm.litellm_client.LiteLLMClient')
    def test_create_from_litellm_config(self, MockLiteLLMClient):
        """Test creating a LiteLLM client from config."""
        config = LiteLLMConfig(
            model="openai/gpt-4",
            api_key="test-key"
        )
        
        client = LLMClientFactory.create_from_litellm_config(config)
        
        MockLiteLLMClient.assert_called_once_with(config=config)
    
    @patch('symphony.core.factory.LLMClientFactory.create_from_litellm_config')
    def test_create_from_provider(self, mock_create_from_config):
        """Test creating an LLM client for a specific provider."""
        LLMClientFactory.create_from_provider(
            provider="openai",
            model_name="gpt-4",
            api_key="test-key",
            temperature=0.7
        )
        
        # Check that create_from_litellm_config was called with the right config
        mock_create_from_config.assert_called_once()
        config = mock_create_from_config.call_args[0][0]
        
        assert config.model == "openai/gpt-4"
        assert config.api_key == "test-key"
        assert config.temperature == 0.7


class TestMemoryFactory:
    """Test suite for the MemoryFactory class."""
    
    def test_register_memory_type(self):
        """Test registering a new memory type."""
        MockMemory = MagicMock()
        
        initial_count = len(MemoryFactory._memory_types)
        MemoryFactory.register_memory_type("mock_memory", MockMemory)
        
        assert len(MemoryFactory._memory_types) == initial_count + 1
        assert MemoryFactory._memory_types["mock_memory"] is MockMemory
        
        # Clean up
        del MemoryFactory._memory_types["mock_memory"]
    
    def test_create_memory(self):
        """Test creating a memory instance."""
        memory = MemoryFactory.create("conversation")
        assert isinstance(memory, ConversationMemory)
    
    def test_create_unknown_memory_type(self):
        """Test creating memory with an unknown type."""
        with pytest.raises(ValueError) as excinfo:
            MemoryFactory.create("unknown")
        
        assert "Unknown memory type" in str(excinfo.value)
    
    def test_create_conversation_memory(self):
        """Test creating a conversation memory specifically."""
        memory = MemoryFactory.create_conversation_memory()
        assert isinstance(memory, ConversationMemory)


class TestMCPManagerFactory:
    """Test suite for the MCPManagerFactory class."""
    
    @patch('symphony.mcp.base.MCPManager')
    def test_create_mcp_manager(self, MockMCPManager):
        """Test creating an MCP manager."""
        config = MCPConfig(app_name="TestApp")
        
        manager = MCPManagerFactory.create(config=config)
        
        MockMCPManager.assert_called_once_with(config=config)
    
    @patch('symphony.mcp.base.MCPManager')
    def test_create_default_mcp_manager(self, MockMCPManager):
        """Test creating an MCP manager with default config."""
        manager = MCPManagerFactory.create()
        
        MockMCPManager.assert_called_once_with(config=None)