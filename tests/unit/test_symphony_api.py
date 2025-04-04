"""Tests for Symphony API class.

This module contains tests for the Symphony API class, which serves as
the main entry point for the Symphony framework.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from symphony.api import Symphony
from symphony.facade.agents import AgentFacade
from symphony.facade.tasks import TaskFacade
from symphony.facade.workflows import WorkflowFacade
from symphony.builder.agent_builder import AgentBuilder
from symphony.builder.task_builder import TaskBuilder
from symphony.builder.workflow_builder import WorkflowBuilder


@pytest.fixture
def symphony():
    """Create a Symphony instance for testing."""
    return Symphony()


class TestSymphonyAPI:
    """Tests for the Symphony API."""
    
    def test_initialization(self, symphony):
        """Test Symphony instance initialization."""
        assert symphony is not None
        assert symphony.registry is not None
    
    def test_properties(self, symphony):
        """Test Symphony properties."""
        assert isinstance(symphony.agents, AgentFacade)
        assert isinstance(symphony.tasks, TaskFacade)
        assert isinstance(symphony.workflows, WorkflowFacade)
    
    def test_builder_methods(self, symphony):
        """Test Symphony builder methods."""
        assert isinstance(symphony.build_agent(), AgentBuilder)
        assert isinstance(symphony.build_task(), TaskBuilder)
        assert isinstance(symphony.build_workflow(), WorkflowBuilder)
    
    @pytest.mark.asyncio
    async def test_setup_memory(self, symphony):
        """Test Symphony setup with memory persistence."""
        await symphony.setup(persistence_type="memory")
        
        assert "task" in symphony.registry.repositories
        assert "workflow" in symphony.registry.repositories
        assert "agent_config" in symphony.registry.repositories
        assert "workflow_definition" in symphony.registry.repositories
    
    @pytest.mark.asyncio
    async def test_setup_file(self, symphony, tmp_path):
        """Test Symphony setup with file persistence."""
        await symphony.setup(persistence_type="file", base_dir=str(tmp_path))
        
        assert "task" in symphony.registry.repositories
        assert "workflow" in symphony.registry.repositories
        assert "agent_config" in symphony.registry.repositories
        assert "workflow_definition" in symphony.registry.repositories
    
    def test_get_registry(self, symphony):
        """Test getting the underlying registry."""
        registry = symphony.get_registry()
        assert registry is symphony.registry