"""Integration tests for DAG-based workflows."""

import pytest
import asyncio
from typing import Dict, List, Optional, Any, Set
import networkx as nx

from symphony.orchestration.dag import (
    WorkflowStep, WorkflowDAG, DAGExecutionResult
)
from symphony.agents.base import AgentConfig, ReactiveAgent


class TestDAGWorkflow:
    """Test suite for DAG-based workflows."""
    
    @pytest.fixture
    def specialized_agents(self, mock_llm_client, prompt_registry):
        """Create specialized agents for workflow testing."""
        data_agent = ReactiveAgent(
            config=AgentConfig(
                name="DataAgent",
                agent_type="reactive",
                description="Handles data processing tasks"
            ),
            llm_client=mock_llm_client,
            prompt_registry=prompt_registry
        )
        
        analysis_agent = ReactiveAgent(
            config=AgentConfig(
                name="AnalysisAgent",
                agent_type="reactive",
                description="Handles data analysis tasks"
            ),
            llm_client=mock_llm_client,
            prompt_registry=prompt_registry
        )
        
        vis_agent = ReactiveAgent(
            config=AgentConfig(
                name="VisualizationAgent",
                agent_type="reactive",
                description="Handles data visualization tasks"
            ),
            llm_client=mock_llm_client,
            prompt_registry=prompt_registry
        )
        
        report_agent = ReactiveAgent(
            config=AgentConfig(
                name="ReportAgent",
                agent_type="reactive",
                description="Handles report generation tasks"
            ),
            llm_client=mock_llm_client,
            prompt_registry=prompt_registry
        )
        
        return {
            "DataAgent": data_agent,
            "AnalysisAgent": analysis_agent,
            "VisualizationAgent": vis_agent,
            "ReportAgent": report_agent
        }
    
    @pytest.fixture
    def workflow_dag(self, specialized_agents):
        """Create a workflow DAG for testing."""
        # Define steps
        data_step = WorkflowStep(
            id="collect_data",
            description="Collect data for analysis",
            agent=specialized_agents["DataAgent"],
            input_template="Collect and prepare data for {topic}"
        )
        
        analysis_step = WorkflowStep(
            id="analyze_data",
            description="Analyze the collected data",
            agent=specialized_agents["AnalysisAgent"],
            input_template="Analyze the following data: {collect_data}",
            depends_on=["collect_data"]
        )
        
        vis_step = WorkflowStep(
            id="visualize_data",
            description="Create visualizations for the analysis",
            agent=specialized_agents["VisualizationAgent"],
            input_template="Create visualizations for this analysis: {analyze_data}",
            depends_on=["analyze_data"]
        )
        
        report_step = WorkflowStep(
            id="generate_report",
            description="Generate a final report",
            agent=specialized_agents["ReportAgent"],
            input_template="Generate a report with these visualizations: {visualize_data} and this analysis: {analyze_data}",
            depends_on=["analyze_data", "visualize_data"]
        )
        
        # Create DAG with steps
        dag = WorkflowDAG()
        dag.add_step(data_step)
        dag.add_step(analysis_step)
        dag.add_step(vis_step)
        dag.add_step(report_step)
        
        return dag
    
    def test_dag_structure(self, workflow_dag):
        """Test that the DAG structure is created correctly."""
        graph = workflow_dag.graph
        
        # Check nodes (steps)
        assert len(graph.nodes()) == 4
        assert "collect_data" in graph.nodes()
        assert "analyze_data" in graph.nodes()
        assert "visualize_data" in graph.nodes()
        assert "generate_report" in graph.nodes()
        
        # Check edges (dependencies)
        edges = list(graph.edges())
        assert ("collect_data", "analyze_data") in edges
        assert ("analyze_data", "visualize_data") in edges
        assert ("analyze_data", "generate_report") in edges
        assert ("visualize_data", "generate_report") in edges
        
        # Check that we have a valid DAG (no cycles)
        assert nx.is_directed_acyclic_graph(graph)
        
        # Check topological sort
        topo_order = list(nx.topological_sort(graph))
        assert topo_order.index("collect_data") < topo_order.index("analyze_data")
        assert topo_order.index("analyze_data") < topo_order.index("visualize_data")
        assert topo_order.index("visualize_data") < topo_order.index("generate_report")
    
    @pytest.mark.asyncio
    async def test_execution_order(self, workflow_dag):
        """Test that the DAG executes steps in the correct order."""
        execution_order = []
        
        # Mock the agent run method to track execution order
        for step_id, step in workflow_dag.steps.items():
            original_run = step.agent.run
            
            async def mock_run(input_str, step_id=step_id):
                execution_order.append(step_id)
                return f"Result for {step_id}"
            
            step.agent.run = mock_run
        
        # Execute workflow
        result = await workflow_dag.execute({"topic": "climate change"})
        
        # Check execution order follows dependencies
        assert execution_order[0] == "collect_data"
        assert execution_order[1] == "analyze_data"
        assert execution_order[2] == "visualize_data"
        assert execution_order[3] == "generate_report"
        
        # Check workflow results
        assert result.success
        assert len(result.step_results) == 4
        
        # Check step output is passed to dependent steps
        collect_output = result.step_results["collect_data"].output
        analyze_output = result.step_results["analyze_data"].output
        vis_output = result.step_results["visualize_data"].output
        report_output = result.step_results["generate_report"].output
        
        assert collect_output == "Result for collect_data"
        assert analyze_output == "Result for analyze_data"
        assert vis_output == "Result for visualize_data"
        assert report_output == "Result for generate_report"
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, specialized_agents):
        """Test that the DAG executes independent steps in parallel."""
        # Create a DAG with parallel steps
        dag = WorkflowDAG()
        
        # Initial step
        start_step = WorkflowStep(
            id="start",
            description="Starting point",
            agent=specialized_agents["DataAgent"],
            input_template="Start workflow for {topic}"
        )
        
        # Two parallel steps
        parallel_1 = WorkflowStep(
            id="parallel_1",
            description="First parallel step",
            agent=specialized_agents["AnalysisAgent"],
            input_template="Process part 1 of {start}",
            depends_on=["start"]
        )
        
        parallel_2 = WorkflowStep(
            id="parallel_2",
            description="Second parallel step",
            agent=specialized_agents["VisualizationAgent"],
            input_template="Process part 2 of {start}",
            depends_on=["start"]
        )
        
        # Final step depending on both parallel steps
        end_step = WorkflowStep(
            id="end",
            description="Final step",
            agent=specialized_agents["ReportAgent"],
            input_template="Combine results: {parallel_1} and {parallel_2}",
            depends_on=["parallel_1", "parallel_2"]
        )
        
        # Add steps to DAG
        dag.add_step(start_step)
        dag.add_step(parallel_1)
        dag.add_step(parallel_2)
        dag.add_step(end_step)
        
        # Track execution with timestamps
        execution_times = {}
        
        for step_id, step in dag.steps.items():
            original_run = step.agent.run
            
            async def mock_run(input_str, step_id=step_id):
                execution_times[step_id] = {"start": asyncio.get_event_loop().time()}
                
                # Simulate work
                if step_id == "start":
                    await asyncio.sleep(0.1)
                elif step_id in ["parallel_1", "parallel_2"]:
                    await asyncio.sleep(0.2)
                else:
                    await asyncio.sleep(0.1)
                
                execution_times[step_id]["end"] = asyncio.get_event_loop().time()
                return f"Result for {step_id}"
            
            step.agent.run = mock_run
        
        # Execute workflow
        result = await dag.execute({"topic": "parallel test"})
        
        # Check parallel execution
        p1_start = execution_times["parallel_1"]["start"]
        p1_end = execution_times["parallel_1"]["end"]
        p2_start = execution_times["parallel_2"]["start"]
        p2_end = execution_times["parallel_2"]["end"]
        
        # Both parallel steps should have overlapping execution times
        assert p1_start < p2_end
        assert p2_start < p1_end
        
        # The end step should start after both parallel steps are done
        end_start = execution_times["end"]["start"]
        assert end_start > p1_end
        assert end_start > p2_end
    
    @pytest.mark.asyncio
    async def test_error_handling(self, workflow_dag):
        """Test that the DAG handles errors gracefully."""
        # Make one step fail
        analyze_step = workflow_dag.steps["analyze_data"]
        original_run = analyze_step.agent.run
        
        async def failing_run(input_str):
            raise Exception("Analysis failed due to invalid data")
        
        analyze_step.agent.run = failing_run
        
        # Execute workflow
        result = await workflow_dag.execute({"topic": "error test"})
        
        # The workflow should not be successful
        assert not result.success
        
        # Check step results
        assert result.step_results["collect_data"].success
        assert not result.step_results["analyze_data"].success
        assert "Analysis failed" in result.step_results["analyze_data"].error
        
        # Dependent steps should be skipped
        assert not result.step_results["visualize_data"].success
        assert "skipped" in result.step_results["visualize_data"].error.lower()
        assert not result.step_results["generate_report"].success
        assert "skipped" in result.step_results["generate_report"].error.lower()