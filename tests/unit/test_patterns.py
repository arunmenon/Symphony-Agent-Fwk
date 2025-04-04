"""Tests for Symphony Patterns Library.

This module contains tests for the Symphony Patterns Library components,
including patterns, registry, facade, and builder.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from symphony.patterns.base import Pattern, PatternContext, PatternConfig
from symphony.patterns.registry import PatternRegistry
from symphony.patterns.facade import PatternsFacade
from symphony.patterns.builder import PatternBuilder

from symphony.patterns.reasoning.chain_of_thought import ChainOfThoughtPattern
from symphony.patterns.verification.critic_review import CriticReviewPattern
from symphony.patterns.multi_agent.expert_panel import ExpertPanelPattern


@pytest.fixture
def pattern_config():
    """Create a pattern configuration for testing."""
    return PatternConfig(
        name="test_pattern",
        description="Test pattern",
        max_iterations=3,
        threshold=0.7,
        agent_roles={"agent1": "agent1_id", "agent2": "agent2_id"},
        metadata={"key": "value"}
    )


@pytest.fixture
def mock_registry():
    """Create a mock registry for testing."""
    registry = MagicMock()
    registry.get_service = MagicMock(return_value=MagicMock())
    registry.get_repository = MagicMock(return_value=MagicMock())
    return registry


class TestPatternBase:
    """Tests for the Pattern base classes."""
    
    class TestPattern(Pattern):
        """Test pattern implementation."""
        
        async def execute(self, context: PatternContext) -> None:
            """Execute test pattern."""
            inputs = context.inputs
            context.set_output("test_output", "test_value")
            context.set_output("input_echo", inputs.get("test_input", ""))
    
    def test_pattern_initialization(self, pattern_config):
        """Test pattern initialization."""
        pattern = self.TestPattern(pattern_config)
        assert pattern.config.name == "test_pattern"
        assert pattern.config.description == "Test pattern"
        assert pattern.config.max_iterations == 3
        assert pattern.config.threshold == 0.7
        assert pattern.config.agent_roles == {"agent1": "agent1_id", "agent2": "agent2_id"}
        assert pattern.config.metadata == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_pattern_run(self):
        """Test pattern run method."""
        pattern = self.TestPattern({
            "name": "test_pattern",
            "description": "Test pattern"
        })
        
        result = await pattern.run({"test_input": "hello"})
        assert result["test_output"] == "test_value"
        assert result["input_echo"] == "hello"
    
    def test_pattern_context_initialization(self):
        """Test pattern context initialization."""
        context = PatternContext(inputs={"test_input": "test_value"})
        
        assert context.inputs == {"test_input": "test_value"}
        assert context.outputs == {}
        assert "start_time" in context.metadata
        assert "context_id" in context.metadata
    
    def test_pattern_context_io(self):
        """Test pattern context input/output operations."""
        context = PatternContext(inputs={"test_input": "test_value"})
        
        # Test get_input
        assert context.get_input("test_input") == "test_value"
        assert context.get_input("missing", "default") == "default"
        
        # Test set_output
        context.set_output("test_output", "output_value")
        assert context.outputs == {"test_output": "output_value"}
        
        # Test get_output
        assert context.get_output("test_output") == "output_value"
        assert context.get_output("missing", "default") == "default"
    
    def test_pattern_context_child(self):
        """Test pattern context child creation."""
        parent = PatternContext(inputs={"parent_input": "parent_value"})
        child = parent.create_child_context({"child_input": "child_value"})
        
        assert child.parent_context is parent
        assert child in parent.child_contexts
        assert child.inputs == {"child_input": "child_value"}
        
        # Test child inherits services from parent
        assert child.service_registry is parent.service_registry


class TestPatternRegistry:
    """Tests for the PatternRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create a pattern registry for testing."""
        return PatternRegistry()
    
    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert registry.patterns == {}
    
    def test_register_pattern(self, registry):
        """Test registering a pattern."""
        factory = lambda config: TestPatternBase.TestPattern(config)
        
        registry.register_pattern(
            name="test_pattern",
            factory=factory,
            category="test",
            description="Test pattern",
            schema={"type": "object"},
            metadata={"key": "value"}
        )
        
        assert "test_pattern" in registry.patterns
        assert registry.patterns["test_pattern"]["factory"] is factory
        assert registry.patterns["test_pattern"]["category"] == "test"
        assert registry.patterns["test_pattern"]["description"] == "Test pattern"
        assert registry.patterns["test_pattern"]["schema"] == {"type": "object"}
        assert registry.patterns["test_pattern"]["metadata"] == {"key": "value"}
    
    def test_create_pattern(self, registry):
        """Test creating a pattern."""
        factory = lambda config: TestPatternBase.TestPattern(config)
        
        registry.register_pattern(
            name="test_pattern",
            factory=factory,
            category="test",
            description="Test pattern"
        )
        
        pattern = registry.create_pattern("test_pattern", {"max_iterations": 5})
        assert isinstance(pattern, TestPatternBase.TestPattern)
        assert pattern.config.name == "test_pattern"
        assert pattern.config.description == "Test pattern"
        assert pattern.config.max_iterations == 5
    
    def test_list_patterns(self, registry):
        """Test listing patterns."""
        registry.register_pattern(
            name="pattern1",
            factory=lambda config: None,
            category="category1",
            description="Description 1"
        )
        
        registry.register_pattern(
            name="pattern2",
            factory=lambda config: None,
            category="category2",
            description="Description 2"
        )
        
        registry.register_pattern(
            name="pattern3",
            factory=lambda config: None,
            category="category1",
            description="Description 3"
        )
        
        # List all patterns
        patterns = registry.list_patterns()
        assert len(patterns) == 3
        
        # List patterns by category
        patterns = registry.list_patterns(category="category1")
        assert len(patterns) == 2
        assert {p["name"] for p in patterns} == {"pattern1", "pattern3"}
    
    def test_get_categories(self, registry):
        """Test getting categories."""
        registry.register_pattern(
            name="pattern1",
            factory=lambda config: None,
            category="category1",
            description="Description 1"
        )
        
        registry.register_pattern(
            name="pattern2",
            factory=lambda config: None,
            category="category2",
            description="Description 2"
        )
        
        registry.register_pattern(
            name="pattern3",
            factory=lambda config: None,
            category="category1",
            description="Description 3"
        )
        
        categories = registry.get_categories()
        assert set(categories) == {"category1", "category2"}


class TestPatternImplementations:
    """Tests for specific pattern implementations."""
    
    @pytest.mark.asyncio
    async def test_chain_of_thought_pattern(self, mock_registry):
        """Test Chain of Thought pattern."""
        # Mock task manager and executor
        task_manager = AsyncMock()
        executor = AsyncMock()
        
        # Set up mock task result
        mock_task = MagicMock()
        mock_task.status.value = "completed"
        mock_task.output_data = {"result": "Step 1: First step\nStep 2: Second step\nStep 3: Final answer is 42"}
        
        # Configure mocks
        task_manager.save_task.return_value = "task_id"
        executor.execute_task.return_value = mock_task
        mock_registry.get_service.side_effect = lambda name: {
            "task_manager": task_manager,
            "enhanced_executor": executor
        }.get(name)
        
        # Create pattern
        pattern = ChainOfThoughtPattern({
            "name": "chain_of_thought",
            "description": "Chain of Thought pattern",
            "agent_roles": {"reasoner": "agent_id"}
        })
        
        # Create context
        context = PatternContext(
            inputs={"query": "What is 6 times 7?"},
            service_registry=mock_registry
        )
        
        # Execute pattern
        await pattern.execute(context)
        
        # Check task creation
        task_manager.save_task.assert_called_once()
        executor.execute_task.assert_called_once_with("task_id")
        
        # Check outputs
        assert "response" in context.outputs
        assert "steps" in context.outputs
        assert len(context.outputs["steps"]) == 3
        assert context.outputs["steps"][0]["content"] == "First step"
        assert context.outputs["steps"][1]["content"] == "Second step"
        assert context.outputs["steps"][2]["content"] == "Final answer is 42"
    
    @pytest.mark.asyncio
    async def test_critic_review_pattern(self, mock_registry):
        """Test Critic Review pattern."""
        # Mock task manager and executor
        task_manager = AsyncMock()
        executor = AsyncMock()
        
        # Set up mock task results
        mock_critic_task = MagicMock()
        mock_critic_task.status.value = "completed"
        mock_critic_task.output_data = {"result": "1. Factual error: Bitcoin was created in 2009, not 2004.\n2. Factual error: It was created by Satoshi Nakamoto, not Microsoft."}
        
        mock_revision_task = MagicMock()
        mock_revision_task.status.value = "completed"
        mock_revision_task.output_data = {"result": "Bitcoin was invented in 2009 by Satoshi Nakamoto as a digital currency. It has become one of the most well-known cryptocurrencies in the world."}
        
        # Configure mocks
        task_manager.save_task.side_effect = ["critic_task_id", "revision_task_id"]
        executor.execute_task.side_effect = [mock_critic_task, mock_revision_task]
        mock_registry.get_service.side_effect = lambda name: {
            "task_manager": task_manager,
            "enhanced_executor": executor
        }.get(name)
        
        # Create pattern
        pattern = CriticReviewPattern({
            "name": "critic_review_revise",
            "description": "Critic Review pattern",
            "agent_roles": {
                "critic": "critic_id",
                "reviser": "reviser_id"
            }
        })
        
        # Create context
        context = PatternContext(
            inputs={
                "content": "Bitcoin was invented in 2004 by Microsoft as a digital currency."
            },
            service_registry=mock_registry
        )
        
        # Execute pattern
        await pattern.execute(context)
        
        # Check task creation
        assert task_manager.save_task.call_count == 2
        assert executor.execute_task.call_count == 2
        
        # Check outputs
        assert context.outputs["initial_content"] == "Bitcoin was invented in 2004 by Microsoft as a digital currency."
        assert "criticism" in context.outputs
        assert "revised_content" in context.outputs
        assert "issues" in context.outputs
        assert len(context.outputs["issues"]) == 2
        assert "Bitcoin was created in 2009, not 2004" in context.outputs["issues"][0]


class TestPatternsFacade:
    """Tests for the PatternsFacade."""
    
    @pytest.fixture
    def facade(self, mock_registry):
        """Create a patterns facade for testing."""
        return PatternsFacade(mock_registry)
    
    @pytest.mark.asyncio
    async def test_apply_pattern(self, facade, mock_registry):
        """Test applying a pattern."""
        # Mock pattern registry
        pattern_registry = MagicMock()
        mock_pattern = AsyncMock()
        mock_pattern.run.return_value = {"result": "test_result"}
        pattern_registry.create_pattern.return_value = mock_pattern
        
        # Configure registry mock
        mock_registry.get_service.return_value = pattern_registry
        
        # Apply pattern
        result = await facade.apply_pattern(
            "test_pattern",
            {"input": "test_input"},
            {"config": "test_config"}
        )
        
        # Check results
        mock_registry.get_service.assert_called_with("pattern_registry")
        pattern_registry.create_pattern.assert_called_with("test_pattern", {"config": "test_config"})
        mock_pattern.run.assert_called_once()
        assert result == {"result": "test_result"}


class TestPatternBuilder:
    """Tests for the PatternBuilder."""
    
    @pytest.fixture
    def builder(self, mock_registry):
        """Create a pattern builder for testing."""
        return PatternBuilder(mock_registry)
    
    def test_builder_create(self, builder):
        """Test creating a pattern with builder."""
        result = builder.create("test_pattern")
        
        assert result is builder
        assert builder.pattern_name == "test_pattern"
    
    def test_builder_with_config(self, builder):
        """Test adding configuration with builder."""
        builder.create("test_pattern")
        result = builder.with_config("key", "value")
        
        assert result is builder
        assert builder.pattern_config["key"] == "value"
    
    def test_builder_with_agent(self, builder):
        """Test adding agent with builder."""
        builder.create("test_pattern")
        result = builder.with_agent("role", "agent_id")
        
        assert result is builder
        assert builder.pattern_config["agent_roles"]["role"] == "agent_id"
    
    def test_builder_with_iterations(self, builder):
        """Test setting iterations with builder."""
        builder.create("test_pattern")
        result = builder.with_iterations(5)
        
        assert result is builder
        assert builder.pattern_config["max_iterations"] == 5
    
    def test_builder_with_threshold(self, builder):
        """Test setting threshold with builder."""
        builder.create("test_pattern")
        result = builder.with_threshold(0.8)
        
        assert result is builder
        assert builder.pattern_config["threshold"] == 0.8
    
    def test_builder_with_input(self, builder):
        """Test adding input with builder."""
        builder.create("test_pattern")
        result = builder.with_input("key", "value")
        
        assert result is builder
        assert builder.pattern_inputs["key"] == "value"
    
    def test_builder_with_query(self, builder):
        """Test setting query with builder."""
        builder.create("test_pattern")
        result = builder.with_query("test query")
        
        assert result is builder
        assert builder.pattern_inputs["query"] == "test query"
    
    def test_builder_build(self, builder):
        """Test building pattern configuration."""
        config = builder.create("test_pattern").with_config("key", "value").build()
        
        assert config["name"] == "test_pattern"
        assert config["config"]["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_builder_execute(self, builder, mock_registry):
        """Test executing pattern with builder."""
        # Mock pattern registry
        pattern_registry = MagicMock()
        mock_pattern = AsyncMock()
        mock_pattern.run.return_value = {"result": "test_result"}
        pattern_registry.create_pattern.return_value = mock_pattern
        
        # Configure registry mock
        mock_registry.get_service.return_value = pattern_registry
        
        # Build and execute pattern
        builder.create("test_pattern").with_config("key", "value").with_query("test query")
        result = await builder.execute()
        
        # Check results
        mock_registry.get_service.assert_called_with("pattern_registry")
        pattern_registry.create_pattern.assert_called_with("test_pattern", {"key": "value"})
        mock_pattern.run.assert_called_once()
        assert result == {"result": "test_result"}