"""Test configuration and fixtures for Symphony tests."""

import os
import sys
import pytest
import asyncio
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from unittest.mock import MagicMock

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.llm.base import MockLLMClient, LLMClient
from symphony.prompts.registry import PromptRegistry
from symphony.memory.base import BaseMemory
from symphony.memory.vector_memory import VectorMemory
from symphony.memory.local_kg_memory import (
    LocalKnowledgeGraphMemory, SimpleEmbeddingModel
)
from symphony.tools.base import Tool

# Import the MCP manager class for mocking
from symphony.mcp.base import MCPManager, MCPConfig, Context


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
    
    
@pytest.fixture
def mock_mcp_manager():
    """Create a mock MCP manager for testing."""
    # Create a mock context
    mock_context = MagicMock(spec=Context)
    mock_context.state = {}
    
    # Create a mock MCPManager
    mock_manager = MagicMock(spec=MCPManager)
    
    # Setup methods to return sensible values
    mock_manager.get_context.return_value = mock_context
    mock_manager.prepare_agent_context.return_value = mock_context
    
    # Make update_context_state actually update the state
    def update_state(ctx, key, value):
        ctx.state[key] = value
    
    mock_manager.update_context_state.side_effect = update_state
    
    return mock_manager


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """Create a mock LLM client for testing."""
    responses = {
        "Hello": "Hi there!",
        "What is your name?": "I am Symphony, a test agent.",
        "Tell me about Symphony": "Symphony is a powerful agent framework for orchestrating multiple AI agents.",
        "Extract factual knowledge triplets": """
{"subject": "Symphony", "predicate": "is", "object": "an agent framework", "confidence": 0.95}
{"subject": "Symphony", "predicate": "supports", "object": "multiple agents", "confidence": 0.9}
{"subject": "Symphony", "predicate": "uses", "object": "LLM", "confidence": 0.85}
        """
    }
    return MockLLMClient(responses=responses)


@pytest.fixture
def prompt_registry() -> PromptRegistry:
    """Create a prompt registry for testing."""
    registry = PromptRegistry()
    
    # Register some test prompts
    registry.register_prompt(
        prompt_type="system",
        content="You are a helpful assistant for testing purposes.",
        agent_type="reactive"
    )
    
    registry.register_prompt(
        prompt_type="system",
        content="You are a planning agent that breaks down tasks into steps.",
        agent_type="planning"
    )
    
    return registry


@pytest.fixture
def vector_memory() -> VectorMemory:
    """Create a vector memory instance for testing."""
    return VectorMemory()


@pytest.fixture
def kg_memory(mock_llm_client) -> LocalKnowledgeGraphMemory:
    """Create a knowledge graph memory instance for testing."""
    embedding_model = SimpleEmbeddingModel(dimension=128)
    return LocalKnowledgeGraphMemory(
        llm_client=mock_llm_client,
        embedding_model=embedding_model,
        auto_extract=True
    )


@pytest.fixture
def mock_tool() -> Tool:
    """Create a mock tool for testing."""
    class MockTool:
        def __init__(self):
            self.name = "mock_tool"
            self.description = "A mock tool for testing"
            self.call_count = 0
            self.last_args = None
            
        async def execute(self, **kwargs):
            self.call_count += 1
            self.last_args = kwargs
            return f"Executed mock tool with args: {kwargs}"
    
    mt = MockTool()
    return Tool(
        name=mt.name,
        description=mt.description,
        function=mt.execute
    )


@pytest.fixture
def reactive_agent(mock_llm_client, prompt_registry, mock_mcp_manager) -> ReactiveAgent:
    """Create a reactive agent for testing."""
    config = AgentConfig(
        name="TestAgent",
        agent_type="reactive",
        description="A test agent"
    )
    
    agent = ReactiveAgent(
        config=config,
        llm_client=mock_llm_client,
        prompt_registry=prompt_registry,
        mcp_manager=mock_mcp_manager
    )
    
    # Set system prompt directly for testing
    agent.system_prompt = "You are a helpful assistant for testing purposes."
    
    return agent