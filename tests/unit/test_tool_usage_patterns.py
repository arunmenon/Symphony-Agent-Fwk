"""Tests for tool usage patterns in Symphony.

This module contains tests for the tool usage patterns in Symphony.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from symphony.patterns.base import PatternContext
from symphony.patterns.tool_usage.multi_tool_chain import MultiToolChainPattern
from symphony.patterns.tool_usage.verify_execute import VerifyExecutePattern
from symphony.patterns.tool_usage.recursive_tool_use import RecursiveToolUsePattern


@pytest.fixture
def pattern_config():
    """Create a pattern configuration."""
    return {
        "name": "test_pattern",
        "description": "Test pattern",
        "max_iterations": 3,
        "agent_roles": {
            "executor": "test_executor",
            "verifier": "test_verifier",
            "dispatcher": "test_dispatcher"
        }
    }


@pytest.fixture
def pattern_context():
    """Create a pattern context."""
    # Create mock service registry with tool manager
    tool_manager = MagicMock()
    tool_manager.execute_tool = AsyncMock(return_value={"result": "mock_result"})
    
    registry = MagicMock()
    registry.get_service = MagicMock(return_value=tool_manager)
    
    return PatternContext(
        inputs={
            "query": "test query",
            "tools": [
                {
                    "name": "test_tool",
                    "config": {"param": "value"},
                    "input_mapping": {"input": "query"},
                    "output_mapping": {"result": "output"}
                }
            ]
        },
        service_registry=registry
    )


class AsyncMock(MagicMock):
    """Mock for async functions."""
    
    async def __call__(self, *args, **kwargs):
        """Execute the mock asynchronously."""
        return super(AsyncMock, self).__call__(*args, **kwargs)


@pytest.mark.asyncio
async def test_multi_tool_chain_pattern(pattern_config, pattern_context):
    """Test the multi-tool chain pattern."""
    # Create pattern
    pattern = MultiToolChainPattern(pattern_config)
    
    # Execute pattern
    await pattern.execute(pattern_context)
    
    # Verify outputs
    assert "results" in pattern_context.outputs
    assert "final_result" in pattern_context.outputs
    
    # Verify tool manager was called
    tool_manager = pattern_context.get_service("tool_manager")
    tool_manager.execute_tool.assert_called_once()


@pytest.mark.asyncio
async def test_multi_tool_chain_empty_tools(pattern_config, pattern_context):
    """Test the multi-tool chain pattern with empty tools."""
    # Create pattern
    pattern = MultiToolChainPattern(pattern_config)
    
    # Set empty tools
    pattern_context.inputs["tools"] = []
    
    # Execute pattern
    await pattern.execute(pattern_context)
    
    # Verify error
    assert "error" in pattern_context.outputs
    assert pattern_context.outputs["error"] == "No tools provided for execution"


@pytest.mark.asyncio
async def test_verify_execute_pattern(pattern_config, pattern_context):
    """Test the verify-execute pattern."""
    # Create mock agent service
    agent_service = MagicMock()
    agent_service.execute_agent = AsyncMock(return_value="APPROVED: The plan is safe and relevant.")
    
    # Add agent service to context
    pattern_context.service_registry.get_service = MagicMock(
        side_effect=lambda name: (
            agent_service if name == "agent_manager" 
            else pattern_context.service_registry.get_service.return_value
        )
    )
    
    # Add verification criteria
    pattern_context.inputs["verification_criteria"] = ["Safety", "Relevance"]
    
    # Create pattern
    pattern = VerifyExecutePattern(pattern_config)
    
    # Execute pattern
    await pattern.execute(pattern_context)
    
    # Verify outputs
    assert "verification_result" in pattern_context.outputs
    assert pattern_context.outputs["verified"] is True
    assert "execution_result" in pattern_context.outputs
    
    # Verify agent service was called
    agent_service.execute_agent.assert_called_once()


@pytest.mark.asyncio
async def test_verify_execute_rejected(pattern_config, pattern_context):
    """Test the verify-execute pattern with rejected verification."""
    # Create mock agent service
    agent_service = MagicMock()
    agent_service.execute_agent = AsyncMock(return_value="REJECTED: The plan is unsafe.")
    
    # Add agent service to context
    pattern_context.service_registry.get_service = MagicMock(
        side_effect=lambda name: (
            agent_service if name == "agent_manager" 
            else pattern_context.service_registry.get_service.return_value
        )
    )
    
    # Create pattern
    pattern = VerifyExecutePattern(pattern_config)
    
    # Execute pattern
    await pattern.execute(pattern_context)
    
    # Verify outputs
    assert "verification_result" in pattern_context.outputs
    assert pattern_context.outputs["verified"] is False
    assert pattern_context.outputs["execution_result"] is None


@pytest.mark.asyncio
async def test_recursive_tool_use_pattern(pattern_config, pattern_context):
    """Test the recursive tool use pattern."""
    # Create mock agent service
    agent_service = MagicMock()
    agent_service.execute_agent = AsyncMock(return_value='{"can_solve_directly": true, "tool_to_use": "test_tool", "tool_inputs": {"param": "value"}}')
    
    # Add agent service to context
    pattern_context.service_registry.get_service = MagicMock(
        side_effect=lambda name: (
            agent_service if name == "agent_manager" 
            else pattern_context.service_registry.get_service.return_value
        )
    )
    
    # Update pattern context
    pattern_context.inputs["max_depth"] = 2
    
    # Create pattern
    pattern = RecursiveToolUsePattern(pattern_config)
    
    # Execute pattern
    await pattern.execute(pattern_context)
    
    # Verify outputs
    assert "result" in pattern_context.outputs
    assert "decomposition" in pattern_context.outputs
    
    # Verify agent service was called
    assert agent_service.execute_agent.called


@pytest.mark.asyncio
async def test_recursive_tool_use_decomposition(pattern_config, pattern_context):
    """Test the recursive tool use pattern with decomposition."""
    # Create mock agent service with decomposition
    agent_service = MagicMock()
    # First call returns decomposition, second call for synthesis
    agent_service.execute_agent = AsyncMock(side_effect=[
        '{"can_solve_directly": false, "sub_problems": [{"query": "sub-problem 1", "explanation": "test"}]}',
        '{"can_solve_directly": true, "tool_to_use": "test_tool", "tool_inputs": {"param": "value"}}',
        "Synthesized result"
    ])
    
    # Add agent service to context
    pattern_context.service_registry.get_service = MagicMock(
        side_effect=lambda name: (
            agent_service if name == "agent_manager" 
            else pattern_context.service_registry.get_service.return_value
        )
    )
    
    # Create pattern
    pattern = RecursiveToolUsePattern(pattern_config)
    
    # Execute pattern
    await pattern.execute(pattern_context)
    
    # Verify outputs
    assert "result" in pattern_context.outputs
    assert "decomposition" in pattern_context.outputs
    
    # Check decomposition structure
    decomposition = pattern_context.outputs["decomposition"]
    assert "sub_problems" in decomposition
    assert len(decomposition["sub_problems"]) > 0