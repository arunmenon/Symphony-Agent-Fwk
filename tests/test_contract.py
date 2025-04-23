"""Symphony API contract tests.

These tests validate that the Symphony API contract is maintained. These tests
should be considered minimal contract tests, not exhaustive functional tests.

If these tests pass, integrations built against Symphony's API should continue
to function correctly.
"""

import os
import pytest
import asyncio
from typing import Dict, Any, List

from symphony import Symphony
from symphony.utils.annotations import is_stable_api, get_api_info


# Simple tool for testing
def simple_search_tool(query: str) -> str:
    """A simple mock search tool."""
    return f"Search results for: {query}"


class MockLLMClient:
    """Mock LLM client that returns predefined responses."""
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate a response."""
        return {
            "choices": [
                {
                    "message": {
                        "content": f"Response to: {prompt[:30]}..."
                    }
                }
            ]
        }


@pytest.fixture
def mock_litellm():
    """Mock the LiteLLM client."""
    import sys
    import unittest.mock as mock
    
    # Create mock module
    mock_litellm = mock.MagicMock()
    mock_litellm.Completion.acreate = mock.AsyncMock(
        return_value={
            "choices": [
                {
                    "message": {
                        "content": "Mocked response from LiteLLM"
                    }
                }
            ]
        }
    )
    
    # Add to sys.modules
    sys.modules["litellm"] = mock_litellm
    yield mock_litellm
    
    # Cleanup
    del sys.modules["litellm"]


@pytest.mark.asyncio
async def test_api_contract_minimal_dag(mock_litellm):
    """Test that the minimal DAG example works."""
    # Step 1: Initialize Symphony
    symphony = Symphony(persistence_enabled=True)
    await symphony.setup(state_dir=".symphony_test_contract")
    
    # Step 2: Register a tool
    tool_register = {
        "search": simple_search_tool
    }
    symphony._custom_tools = tool_register
    
    # Step 3: Create two agents
    planner_agent = (symphony.build_agent()
        .name("Planner")
        .description("Plans tasks")
        .with_model("gpt-3.5-turbo")
        .build()
    )
    
    executor_agent = (symphony.build_agent()
        .name("Executor")
        .description("Executes tasks")
        .with_model("gpt-3.5-turbo")
        .with_tools(["search"])
        .build()
    )
    
    # Step 4: Build a workflow
    workflow_builder = symphony.build_workflow()
    workflow = (workflow_builder.create(
        name="Contract Test DAG",
        description="A contract test DAG workflow"
    ))
    
    # Step 5: Create step 1 - Planning
    planning_step = (workflow_builder.build_step()
        .name("Planning")
        .description("Plan the task")
        .agent(planner_agent)
        .task("Create a plan to research Symphony orchestration frameworks")
        .context_data({})
        .output_key("plan")
        .build()
    )
    workflow_builder.add_step(planning_step)
    
    # Step 6: Create step 2 - Execution
    execution_step = (workflow_builder.build_step()
        .name("Execution")
        .description("Execute the plan")
        .agent(executor_agent)
        .task("Execute this plan: {{plan}}")
        .context_data({
            "plan": "{{plan}}",
            "tools": ["search"]
        })
        .output_key("result")
        .build()
    )
    workflow_builder.add_step(execution_step)
    
    # Step 7: Build and execute the workflow
    workflow_definition = workflow_builder.build()
    result = await symphony.workflows.execute_workflow(
        workflow=workflow_definition,
        initial_context={},
        auto_checkpoint=True
    )
    
    # Step 8: Check the results
    context = result.metadata.get("context", {})
    final_result = context.get("result")
    
    # Assertions
    assert final_result is not None, "Final result should not be None"
    assert isinstance(final_result, str), "Final result should be a string"
    assert len(final_result) > 0, "Final result should not be empty"


@pytest.mark.asyncio
async def test_api_facades_and_builders():
    """Test that the Symphony API facades and builders are working."""
    # Initialize Symphony
    symphony = Symphony()
    await symphony.setup()
    
    # Test facades
    assert symphony.agents is not None, "Agent facade should be available"
    assert symphony.tasks is not None, "Task facade should be available"
    assert symphony.workflows is not None, "Workflow facade should be available"
    assert symphony.patterns is not None, "Patterns facade should be available"
    
    # Test builders
    agent_builder = symphony.build_agent()
    assert agent_builder is not None, "Agent builder should be available"
    
    task_builder = symphony.build_task()
    assert task_builder is not None, "Task builder should be available"
    
    workflow_builder = symphony.build_workflow()
    assert workflow_builder is not None, "Workflow builder should be available"
    
    pattern_builder = symphony.build_pattern() 
    assert pattern_builder is not None, "Pattern builder should be available"


def test_api_stability_annotations():
    """Test that all public API elements are annotated as stable."""
    from symphony import api
    
    # Check the Symphony class itself
    assert is_stable_api(Symphony), "Symphony class should be marked as stable"
    
    # Check all items in __all__
    for name in api.__all__:
        if hasattr(api, name):
            item = getattr(api, name)
            assert is_stable_api(item), f"{name} should be marked as stable"
            
            # Check that it has version info
            info = get_api_info(item)
            assert "since_version" in info, f"{name} should have version info"
            assert info["since_version"] == "0.1.0", f"{name} should be version 0.1.0"


if __name__ == "__main__":
    # Run the tests
    pytest.main(["-xvs", __file__])