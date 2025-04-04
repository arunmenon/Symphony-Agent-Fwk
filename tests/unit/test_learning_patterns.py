"""Tests for learning patterns in Symphony.

This module contains tests for the learning patterns in Symphony.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from symphony.patterns.base import PatternContext
from symphony.patterns.learning.few_shot import FewShotPattern
from symphony.patterns.learning.reflection import ReflectionPattern, IterativeReflectionPattern


@pytest.fixture
def pattern_config():
    """Create a pattern configuration."""
    return {
        "name": "test_pattern",
        "description": "Test pattern",
        "max_iterations": 3,
        "agent_roles": {
            "performer": "test_performer",
            "reflector": "test_reflector"
        }
    }


@pytest.fixture
def pattern_context():
    """Create a pattern context."""
    # Create mock service registry with agent manager
    agent_manager = MagicMock()
    agent_manager.execute_agent = AsyncMock(return_value="Mock agent response")
    
    registry = MagicMock()
    registry.get_service = MagicMock(return_value=agent_manager)
    
    return PatternContext(
        inputs={
            "task": "test task",
            "query": "test query",
            "examples": [
                {"input": "example input", "output": "example output"}
            ],
            "criteria": ["Accuracy", "Clarity"]
        },
        service_registry=registry
    )


class AsyncMock(MagicMock):
    """Mock for async functions."""
    
    async def __call__(self, *args, **kwargs):
        """Execute the mock asynchronously."""
        return super(AsyncMock, self).__call__(*args, **kwargs)


@pytest.mark.asyncio
async def test_few_shot_pattern(pattern_config, pattern_context):
    """Test the few-shot pattern."""
    # Create pattern
    pattern = FewShotPattern(pattern_config)
    
    # Execute pattern
    await pattern.execute(pattern_context)
    
    # Verify outputs
    assert "result" in pattern_context.outputs
    
    # Verify agent manager was called
    agent_manager = pattern_context.get_service("agent_manager")
    agent_manager.execute_agent.assert_called_once()


@pytest.mark.asyncio
async def test_few_shot_standard_examples(pattern_config):
    """Test the few-shot pattern with standard examples."""
    # Create pattern with standard examples
    pattern = FewShotPattern.with_standard_examples(
        pattern_config, 
        task_type="summarization"
    )
    
    # Check if examples were added to metadata
    assert "examples" in pattern.config.metadata
    assert len(pattern.config.metadata["examples"]) > 0
    assert "task_type" in pattern.config.metadata
    assert pattern.config.metadata["task_type"] == "summarization"


@pytest.mark.asyncio
async def test_few_shot_missing_inputs(pattern_config, pattern_context):
    """Test the few-shot pattern with missing inputs."""
    # Create pattern
    pattern = FewShotPattern(pattern_config)
    
    # Remove required inputs
    pattern_context.inputs.pop("task")
    
    # Execute pattern
    await pattern.execute(pattern_context)
    
    # Verify error
    assert "error" in pattern_context.outputs
    assert "required" in pattern_context.outputs["error"].lower()


@pytest.mark.asyncio
async def test_reflection_pattern(pattern_config, pattern_context):
    """Test the reflection pattern."""
    # Create pattern
    pattern = ReflectionPattern(pattern_config)
    
    # Create mock agent manager with multiple responses
    agent_manager = MagicMock()
    agent_manager.execute_agent = AsyncMock(side_effect=[
        "Initial response",
        "Reflection analysis",
        "Improved response",
        "Improvement summary"
    ])
    
    # Update context
    pattern_context.service_registry.get_service = MagicMock(return_value=agent_manager)
    
    # Execute pattern
    await pattern.execute(pattern_context)
    
    # Verify outputs
    assert "initial_response" in pattern_context.outputs
    assert "reflection" in pattern_context.outputs
    assert "final_response" in pattern_context.outputs
    assert "improvement" in pattern_context.outputs
    
    # Verify agent manager was called multiple times
    assert agent_manager.execute_agent.call_count == 4


@pytest.mark.asyncio
async def test_iterative_reflection_pattern(pattern_config, pattern_context):
    """Test the iterative reflection pattern."""
    # Create pattern
    pattern = IterativeReflectionPattern(pattern_config)
    
    # Set iterations
    pattern_context.inputs["iterations"] = 2
    
    # Create mock agent manager with multiple responses
    agent_manager = MagicMock()
    agent_manager.execute_agent = AsyncMock(side_effect=[
        "Initial response",
        "Reflection 1",
        "Improved response 1",
        "Reflection 2",
        "Improved response 2",
        "Improvement trace 1",
        "Improvement trace 2"
    ])
    
    # Update context
    pattern_context.service_registry.get_service = MagicMock(return_value=agent_manager)
    
    # Execute pattern
    await pattern.execute(pattern_context)
    
    # Verify outputs
    assert "responses" in pattern_context.outputs
    assert len(pattern_context.outputs["responses"]) == 3  # Initial + 2 iterations
    assert "reflections" in pattern_context.outputs
    assert len(pattern_context.outputs["reflections"]) == 2
    assert "final_response" in pattern_context.outputs
    assert "improvement_trace" in pattern_context.outputs
    
    # Verify agent manager was called multiple times
    assert agent_manager.execute_agent.call_count >= 5