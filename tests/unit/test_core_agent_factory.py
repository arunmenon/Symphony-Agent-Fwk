"""Unit tests for AgentFactory."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from symphony.core.agent_factory import AgentFactory
from symphony.core.agent_config import AgentConfig
from symphony.agents.base import Agent
from symphony.persistence.repository import Repository


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = AsyncMock(spec=Repository)
    
    # Setup find_by_id to return a config
    test_config = AgentConfig(
        id="test_config_id",
        name="TestAgent",
        role="Tester",
        description="A test agent",
        instruction_template="You are a test agent named {name}. Your role is {role}.",
        config={"model": "gpt-4"}
    )
    
    async def mock_find_by_id(id):
        if id == "test_config_id":
            return test_config
        return None
        
    repo.find_by_id.side_effect = mock_find_by_id
    
    # Setup save to return the ID
    async def mock_save(config):
        return config.id
        
    repo.save.side_effect = mock_save
    
    return repo, test_config


@pytest.fixture
def factory(mock_repository):
    """Create an agent factory with mock repository."""
    repo, _ = mock_repository
    return AgentFactory(repo)


@pytest.mark.asyncio
async def test_create_agent_success(factory, mock_repository):
    """Test creating an agent from a valid configuration."""
    repo, config = mock_repository
    
    # Create agent
    agent = await factory.create_agent("test_config_id", name="CustomName", role="custom role")
    
    # Verify repository was called
    repo.find_by_id.assert_called_once_with("test_config_id")
    
    # Verify agent properties
    assert agent.name == "CustomName"  # From kwargs, overrides config
    assert agent.system_prompt == config.instruction_template  # From config
    assert agent.model == "gpt-4"  # From config


@pytest.mark.asyncio
async def test_create_agent_no_repository(mock_repository):
    """Test creating an agent with no repository."""
    factory = AgentFactory(None)
    
    # Try to create agent without repository
    with pytest.raises(ValueError, match="Repository not configured"):
        await factory.create_agent("test_config_id")


@pytest.mark.asyncio
async def test_create_agent_config_not_found(factory):
    """Test creating an agent with non-existent configuration."""
    # Try to create agent with non-existent config
    with pytest.raises(ValueError, match="Agent configuration nonexistent_id not found"):
        await factory.create_agent("nonexistent_id")


@pytest.mark.asyncio
async def test_save_agent_config(factory, mock_repository):
    """Test saving agent configuration from an agent instance."""
    repo, _ = mock_repository
    
    # Create an agent
    agent = Agent(
        name="TestAgent",
        description="Test description",
        system_prompt="You are a test agent",
        model="gpt-4"
    )
    
    # Save config
    config_id = await factory.save_agent_config(agent)
    
    # Verify repository was called
    repo.save.assert_called_once()
    
    # Verify config properties
    saved_config = repo.save.call_args[0][0]
    assert saved_config.name == "TestAgent"
    assert saved_config.description == "Test description"
    assert saved_config.instruction_template == "You are a test agent"
    assert saved_config.config == {"model": "gpt-4"}


@pytest.mark.asyncio
async def test_save_agent_config_no_repository():
    """Test saving agent configuration with no repository."""
    factory = AgentFactory(None)
    agent = Agent(name="TestAgent", system_prompt="Test")
    
    # Try to save config without repository
    with pytest.raises(ValueError, match="Repository not configured"):
        await factory.save_agent_config(agent)