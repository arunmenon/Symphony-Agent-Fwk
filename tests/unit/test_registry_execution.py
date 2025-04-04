"""Unit tests for ServiceRegistry with execution components."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from symphony.core.registry import ServiceRegistry
from symphony.persistence.repository import Repository
from symphony.persistence.memory_repository import InMemoryRepository
from symphony.core.agent_config import AgentConfig
from symphony.core.task import Task
from symphony.execution.workflow_tracker import Workflow, WorkflowTracker
from symphony.execution.enhanced_agent import EnhancedExecutor
from symphony.execution.router import TaskRouter, RoutingStrategy


@pytest.fixture
def registry():
    """Create a fresh registry for testing."""
    registry = ServiceRegistry()
    return registry


@pytest.fixture
def repositories():
    """Create repositories for testing."""
    agent_config_repo = InMemoryRepository(AgentConfig)
    task_repo = InMemoryRepository(Task)
    workflow_repo = InMemoryRepository(Workflow)
    return agent_config_repo, task_repo, workflow_repo


def test_register_repositories(registry, repositories):
    """Test registering repositories."""
    agent_config_repo, task_repo, workflow_repo = repositories
    
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    
    assert registry.repositories["agent_config"] == agent_config_repo
    assert registry.repositories["task"] == task_repo
    assert registry.repositories["workflow"] == workflow_repo


def test_get_workflow_tracker(registry, repositories):
    """Test getting workflow tracker."""
    agent_config_repo, task_repo, workflow_repo = repositories
    
    # Register repositories
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    
    # Get workflow tracker
    workflow_tracker = registry.get_workflow_tracker()
    
    # Verify type and repository assignment
    assert isinstance(workflow_tracker, WorkflowTracker)
    assert workflow_tracker.task_repository == task_repo
    assert workflow_tracker.workflow_repository == workflow_repo
    
    # Verify it's registered as a service
    assert registry.services["workflow_tracker"] == workflow_tracker
    
    # Verify getting same instance when called again
    workflow_tracker2 = registry.get_workflow_tracker()
    assert workflow_tracker2 is workflow_tracker


def test_get_workflow_tracker_missing_repo(registry, repositories):
    """Test getting workflow tracker with missing repository."""
    agent_config_repo, task_repo, workflow_repo = repositories
    
    # Register only one repository
    registry.register_repository("task", task_repo)
    
    # Workflow repository is missing, should raise ValueError
    with pytest.raises(ValueError, match="Workflow repository not registered"):
        registry.get_workflow_tracker()
    
    # Register only workflow repository
    registry.repositories = {}
    registry.register_repository("workflow", workflow_repo)
    
    # Task repository is missing, should raise ValueError
    with pytest.raises(ValueError, match="Task repository not registered"):
        registry.get_workflow_tracker()


def test_get_enhanced_executor(registry, repositories):
    """Test getting enhanced executor."""
    agent_config_repo, task_repo, workflow_repo = repositories
    
    # Register repositories
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    
    # Get enhanced executor
    executor = registry.get_enhanced_executor()
    
    # Verify type and repository assignment
    assert isinstance(executor, EnhancedExecutor)
    assert executor.task_repository == task_repo
    
    # Verify workflow_tracker was created and assigned
    assert executor.workflow_tracker is not None
    assert isinstance(executor.workflow_tracker, WorkflowTracker)
    
    # Verify it's registered as a service
    assert registry.services["enhanced_executor"] == executor
    
    # Verify getting same instance when called again
    executor2 = registry.get_enhanced_executor()
    assert executor2 is executor


def test_get_enhanced_executor_missing_repo(registry, repositories):
    """Test getting enhanced executor with missing repository."""
    agent_config_repo, task_repo, workflow_repo = repositories
    
    # Task repository is missing, should raise ValueError
    with pytest.raises(ValueError, match="Task repository not registered"):
        registry.get_enhanced_executor()


def test_get_enhanced_executor_optional_workflow_tracker(registry, repositories):
    """Test getting enhanced executor without workflow tracker."""
    agent_config_repo, task_repo, workflow_repo = repositories
    
    # Register only task repository
    registry.register_repository("task", task_repo)
    
    # Get enhanced executor
    executor = registry.get_enhanced_executor()
    
    # Verify type and repository assignment
    assert isinstance(executor, EnhancedExecutor)
    assert executor.task_repository == task_repo
    
    # Verify workflow_tracker is None
    assert executor.workflow_tracker is None


def test_get_task_router(registry, repositories):
    """Test getting task router."""
    agent_config_repo, task_repo, workflow_repo = repositories
    
    # Register repository
    registry.register_repository("agent_config", agent_config_repo)
    
    # Get task router with default strategy
    router = registry.get_task_router()
    
    # Verify type, repository, and strategy
    assert isinstance(router, TaskRouter)
    assert router.agent_config_repository == agent_config_repo
    assert router.strategy == RoutingStrategy.CAPABILITY_MATCH
    
    # Verify it's registered as a service
    assert registry.services["task_router"] == router
    
    # Verify getting same instance when called again
    router2 = registry.get_task_router()
    assert router2 is router
    
    # Get with different strategy (should return same instance with updated strategy)
    router3 = registry.get_task_router(RoutingStrategy.ROUND_ROBIN)
    assert router3 is router
    assert router3.strategy == RoutingStrategy.ROUND_ROBIN


def test_get_task_router_missing_repo(registry, repositories):
    """Test getting task router with missing repository."""
    agent_config_repo, task_repo, workflow_repo = repositories
    
    # Agent config repository is missing, should raise ValueError
    with pytest.raises(ValueError, match="Agent config repository not registered"):
        registry.get_task_router()


def test_registry_services_integration(registry, repositories):
    """Test integration between registry services."""
    agent_config_repo, task_repo, workflow_repo = repositories
    
    # Register repositories
    registry.register_repository("agent_config", agent_config_repo)
    registry.register_repository("task", task_repo)
    registry.register_repository("workflow", workflow_repo)
    
    # Get all services
    task_manager = registry.get_task_manager()
    workflow_tracker = registry.get_workflow_tracker()
    executor = registry.get_enhanced_executor()
    router = registry.get_task_router()
    
    # Verify all services are properly initialized
    assert task_manager.repository == task_repo
    assert workflow_tracker.task_repository == task_repo
    assert workflow_tracker.workflow_repository == workflow_repo
    assert executor.task_repository == task_repo
    assert executor.workflow_tracker is workflow_tracker
    assert router.agent_config_repository == agent_config_repo