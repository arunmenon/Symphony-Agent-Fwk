"""
Symphony Benchmarking Example

This script performs benchmarking of different aspects of the Symphony framework:
1. Agent response time
2. Memory operations
3. Tool execution
4. Multi-agent coordination
5. MCP overhead analysis

The benchmarks compare different configurations and options to help
users understand performance characteristics of Symphony.

Run with:
    python examples/benchmarking.py
"""

import asyncio
import time
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path so we can import symphony
sys.path.append(str(Path(__file__).parent.parent))

from symphony.agents.base import AgentConfig, ReactiveAgent
from symphony.agents.planning import PlannerAgent
from symphony.core import (
    ConfigLoader,
    Event,
    EventType,
    LLMClientFactory,
    MCPManagerFactory,
    MemoryFactory,
    Plugin,
    SymphonyConfig,
    Symphony,
)
from symphony.llm.litellm_client import LiteLLMConfig
from symphony.mcp.base import MCPConfig, MCPManager
from symphony.memory.base import BaseMemory, ConversationMemory, InMemoryMemory
from symphony.prompts.registry import PromptRegistry
from symphony.tools.base import tool
from symphony.orchestration.base import MultiAgentOrchestrator, OrchestratorConfig, TurnType


# ----------------------
# Benchmark Tools
# ----------------------

@tool(name="fast_tool", description="A fast-executing tool for benchmarking")
def fast_tool(param: str) -> str:
    """A tool that executes quickly (under 5ms)."""
    return f"Processed: {param}"


@tool(name="medium_tool", description="A medium-speed tool for benchmarking")
def medium_tool(param: str) -> str:
    """A tool that takes a moderate amount of time (about 50ms)."""
    time.sleep(0.05)  # Simulate medium processing time
    return f"Medium processing complete for: {param}"


@tool(name="slow_tool", description="A slow-executing tool for benchmarking")
def slow_tool(param: str) -> str:
    """A tool that takes significant time (about 200ms)."""
    time.sleep(0.2)  # Simulate slower processing time
    return f"Slow processing complete for: {param}"


# ----------------------
# Benchmarking Functions
# ----------------------

async def benchmark_agent_response_time(
    agent_types: List[str],
    prompt_lengths: List[int],
    trials: int = 5
) -> Dict[str, Dict[int, List[float]]]:
    """Benchmark agent response times with different configurations.
    
    Args:
        agent_types: List of agent types to benchmark
        prompt_lengths: List of prompt lengths to test
        trials: Number of trials for each configuration
        
    Returns:
        Dictionary of results by agent type and prompt length
    """
    print("\n=== Benchmarking Agent Response Time ===")
    
    results: Dict[str, Dict[int, List[float]]] = {}
    
    # Create mock responses for different lengths
    mock_responses = {}
    for length in prompt_lengths:
        # Create input and output of appropriate length
        input_text = f"Generate a response of about {length} characters"
        output_text = "A" * length
        mock_responses[input_text] = output_text
    
    # Create LLM client with mock responses
    llm_client = LLMClientFactory.create_mock(responses=mock_responses)
    
    # Create prompt registry
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content="You are a benchmark test agent.",
        agent_type="reactive"
    )
    registry.register_prompt(
        prompt_type="system",
        content="You are a benchmark test planner that creates and follows plans.",
        agent_type="planner"
    )
    
    # Test each agent type
    for agent_type in agent_types:
        results[agent_type] = {}
        
        for length in prompt_lengths:
            times = []
            
            # Create agent config
            config = AgentConfig(
                name=f"Benchmark{agent_type.capitalize()}",
                agent_type=agent_type,
                description=f"A {agent_type} agent for benchmarking"
            )
            
            # Create the appropriate agent type
            if agent_type == "reactive":
                agent = ReactiveAgent(
                    config=config,
                    llm_client=llm_client,
                    prompt_registry=registry
                )
            elif agent_type == "planner":
                agent = PlannerAgent(
                    config=config,
                    llm_client=llm_client,
                    prompt_registry=registry
                )
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            # Run trials
            for _ in range(trials):
                input_text = f"Generate a response of about {length} characters"
                
                start_time = time.time()
                await agent.run(input_text)
                end_time = time.time()
                
                elapsed = end_time - start_time
                times.append(elapsed)
                
            # Record results
            results[agent_type][length] = times
            avg_time = sum(times) / len(times)
            print(f"  {agent_type.capitalize()} agent, {length} chars: {avg_time:.4f}s avg")
    
    return results


async def benchmark_memory_operations(
    memory_types: List[str],
    operation_counts: List[int],
    trials: int = 5
) -> Dict[str, Dict[str, Dict[int, List[float]]]]:
    """Benchmark memory operations with different memory implementations.
    
    Args:
        memory_types: List of memory types to benchmark
        operation_counts: List of operation counts to test
        trials: Number of trials for each configuration
        
    Returns:
        Dictionary of results by memory type, operation, and count
    """
    print("\n=== Benchmarking Memory Operations ===")
    
    results: Dict[str, Dict[str, Dict[int, List[float]]]] = {}
    
    for memory_type in memory_types:
        results[memory_type] = {
            "store": {},
            "retrieve": {},
            "search": {}
        }
        
        for count in operation_counts:
            # Create memory instance
            memory = MemoryFactory.create(memory_type)
            
            # Store operation benchmark
            store_times = []
            for _ in range(trials):
                start_time = time.time()
                
                for i in range(count):
                    memory.store(f"key_{i}", f"value_{i}")
                    
                end_time = time.time()
                elapsed = end_time - start_time
                store_times.append(elapsed)
            
            results[memory_type]["store"][count] = store_times
            avg_store = sum(store_times) / len(store_times)
            print(f"  {memory_type} memory, store {count} items: {avg_store:.4f}s avg")
            
            # Retrieve operation benchmark
            retrieve_times = []
            for _ in range(trials):
                start_time = time.time()
                
                for i in range(count):
                    memory.retrieve(f"key_{i}")
                    
                end_time = time.time()
                elapsed = end_time - start_time
                retrieve_times.append(elapsed)
            
            results[memory_type]["retrieve"][count] = retrieve_times
            avg_retrieve = sum(retrieve_times) / len(retrieve_times)
            print(f"  {memory_type} memory, retrieve {count} items: {avg_retrieve:.4f}s avg")
            
            # Search operation benchmark
            search_times = []
            for _ in range(trials):
                start_time = time.time()
                
                for i in range(min(count, 10)):  # Limit searches to avoid too many
                    memory.search(f"value_{i}", limit=10)
                    
                end_time = time.time()
                elapsed = end_time - start_time
                search_times.append(elapsed)
            
            results[memory_type]["search"][count] = search_times
            avg_search = sum(search_times) / len(search_times)
            print(f"  {memory_type} memory, search {min(count, 10)} items: {avg_search:.4f}s avg")
    
    return results


async def benchmark_tool_execution(
    tool_names: List[str],
    call_counts: List[int],
    trials: int = 5
) -> Dict[str, Dict[int, List[float]]]:
    """Benchmark tool execution times.
    
    Args:
        tool_names: List of tool names to benchmark
        call_counts: List of call counts to test
        trials: Number of trials for each configuration
        
    Returns:
        Dictionary of results by tool name and call count
    """
    print("\n=== Benchmarking Tool Execution ===")
    
    results: Dict[str, Dict[int, List[float]]] = {}
    
    # Create agent with all tools
    config = AgentConfig(
        name="ToolBenchmarkAgent",
        agent_type="reactive",
        description="An agent for benchmarking tools",
        tools=tool_names
    )
    
    # Create mock LLM client (we won't actually use it for tool benchmarking)
    llm_client = LLMClientFactory.create_mock()
    
    # Create prompt registry
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content="You are a tool benchmark agent.",
        agent_type="reactive"
    )
    
    # Create agent
    agent = ReactiveAgent(
        config=config,
        llm_client=llm_client,
        prompt_registry=registry
    )
    
    for tool_name in tool_names:
        results[tool_name] = {}
        
        for count in call_counts:
            times = []
            
            for _ in range(trials):
                start_time = time.time()
                
                for i in range(count):
                    await agent.call_tool(tool_name, param=f"benchmark_{i}")
                    
                end_time = time.time()
                elapsed = end_time - start_time
                times.append(elapsed)
            
            results[tool_name][count] = times
            avg_time = sum(times) / len(times)
            print(f"  {tool_name}, {count} calls: {avg_time:.4f}s avg")
    
    return results


async def benchmark_multi_agent_coordination(
    agent_counts: List[int],
    turn_types: List[TurnType],
    trials: int = 3
) -> Dict[int, Dict[str, List[float]]]:
    """Benchmark multi-agent coordination with different configurations.
    
    Args:
        agent_counts: List of agent counts to test
        turn_types: List of turn types to test
        trials: Number of trials for each configuration
        
    Returns:
        Dictionary of results by agent count and turn type
    """
    print("\n=== Benchmarking Multi-Agent Coordination ===")
    
    results: Dict[int, Dict[str, List[float]]] = {}
    
    # Create mock LLM client with simple responses
    mock_responses = {
        "process this data": "I've processed the data and found interesting patterns."
    }
    llm_client = LLMClientFactory.create_mock(responses=mock_responses)
    
    # Create prompt registry
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content="You are a benchmark agent that processes data.",
        agent_type="reactive"
    )
    
    for count in agent_counts:
        results[count] = {}
        
        for turn_type in turn_types:
            times = []
            
            for _ in range(trials):
                # Create agent configs
                agent_configs = []
                for i in range(count):
                    agent_configs.append(AgentConfig(
                        name=f"Agent{i+1}",
                        agent_type="reactive",
                        description=f"Benchmark agent {i+1}"
                    ))
                
                # Create orchestrator config
                orchestrator_config = OrchestratorConfig(
                    agent_configs=agent_configs,
                    max_steps=count * 2  # Allow enough steps for all agents
                )
                
                # Create orchestrator
                orchestrator = MultiAgentOrchestrator(
                    config=orchestrator_config,
                    llm_client=llm_client,
                    prompt_registry=registry,
                    turn_type=turn_type
                )
                
                # Run benchmark
                start_time = time.time()
                await orchestrator.run("process this data")
                end_time = time.time()
                
                elapsed = end_time - start_time
                times.append(elapsed)
            
            results[count][turn_type] = times
            avg_time = sum(times) / len(times)
            print(f"  {count} agents, {turn_type} turn type: {avg_time:.4f}s avg")
    
    return results


async def benchmark_mcp_overhead(
    with_mcp: List[bool],
    resource_counts: List[int],
    trials: int = 5
) -> Dict[bool, Dict[int, List[float]]]:
    """Benchmark MCP overhead with different resource counts.
    
    Args:
        with_mcp: List of boolean flags for MCP enabled/disabled
        resource_counts: List of resource counts to test
        trials: Number of trials for each configuration
        
    Returns:
        Dictionary of results by MCP status and resource count
    """
    print("\n=== Benchmarking MCP Overhead ===")
    
    results: Dict[bool, Dict[int, List[float]]] = {}
    
    # Create mock LLM client
    llm_client = LLMClientFactory.create_mock(responses={
        "test mcp": "I've processed using MCP context."
    })
    
    # Create prompt registry
    registry = PromptRegistry()
    registry.register_prompt(
        prompt_type="system",
        content="You are a benchmark agent testing MCP.",
        agent_type="reactive"
    )
    
    for mcp_enabled in with_mcp:
        results[mcp_enabled] = {}
        
        for resource_count in resource_counts:
            times = []
            
            for _ in range(trials):
                # Create MCP manager if enabled
                mcp_manager = None
                if mcp_enabled:
                    mcp_config = MCPConfig(app_name="MCP Benchmark")
                    mcp_manager = MCPManager(config=mcp_config)
                    
                    # Register test resources
                    for i in range(resource_count):
                        @mcp_manager.mcp.resource(f"test://resource/{i}")
                        def get_resource(ctx):
                            return f"Resource {i} data"
                
                # Create agent config
                agent_config = AgentConfig(
                    name="MCPBenchmarkAgent",
                    agent_type="reactive",
                    description="An agent for benchmarking MCP",
                    mcp_enabled=mcp_enabled
                )
                
                # Create agent
                agent = ReactiveAgent(
                    config=agent_config,
                    llm_client=llm_client,
                    prompt_registry=registry,
                    mcp_manager=mcp_manager
                )
                
                # Run benchmark
                start_time = time.time()
                await agent.run("test mcp")
                end_time = time.time()
                
                elapsed = end_time - start_time
                times.append(elapsed)
            
            results[mcp_enabled][resource_count] = times
            avg_time = sum(times) / len(times)
            print(f"  MCP {'enabled' if mcp_enabled else 'disabled'}, {resource_count} resources: {avg_time:.4f}s avg")
    
    return results


# ----------------------
# Result Analysis
# ----------------------

def analyze_results(
    agent_results: Dict[str, Dict[int, List[float]]],
    memory_results: Dict[str, Dict[str, Dict[int, List[float]]]],
    tool_results: Dict[str, Dict[int, List[float]]],
    orchestration_results: Dict[int, Dict[str, List[float]]],
    mcp_results: Dict[bool, Dict[int, List[float]]]
) -> None:
    """Analyze and summarize benchmark results.
    
    Args:
        agent_results: Results from agent benchmarks
        memory_results: Results from memory benchmarks
        tool_results: Results from tool benchmarks
        orchestration_results: Results from orchestration benchmarks
        mcp_results: Results from MCP benchmarks
    """
    print("\n=== Benchmark Results Analysis ===")
    
    # Agent response time analysis
    print("\nAgent Response Time Analysis:")
    for agent_type, lengths in agent_results.items():
        print(f"  {agent_type.capitalize()} Agent:")
        for length, times in lengths.items():
            mean = statistics.mean(times)
            if len(times) > 1:
                stdev = statistics.stdev(times)
                print(f"    {length} chars: {mean:.4f}s avg, ±{stdev:.4f}s stdev")
            else:
                print(f"    {length} chars: {mean:.4f}s avg")
    
    # Memory operation analysis
    print("\nMemory Operation Analysis:")
    for memory_type, operations in memory_results.items():
        print(f"  {memory_type.capitalize()} Memory:")
        for operation, counts in operations.items():
            print(f"    {operation.capitalize()} operation:")
            for count, times in counts.items():
                mean = statistics.mean(times)
                ops_per_sec = count / mean if mean > 0 else float('inf')
                print(f"      {count} items: {mean:.4f}s avg ({ops_per_sec:.1f} ops/s)")
    
    # Tool execution analysis
    print("\nTool Execution Analysis:")
    for tool_name, counts in tool_results.items():
        print(f"  {tool_name}:")
        for count, times in counts.items():
            mean = statistics.mean(times)
            calls_per_sec = count / mean if mean > 0 else float('inf')
            print(f"    {count} calls: {mean:.4f}s avg ({calls_per_sec:.1f} calls/s)")
    
    # Multi-agent coordination analysis
    print("\nMulti-Agent Coordination Analysis:")
    for count, turn_types in orchestration_results.items():
        print(f"  {count} Agents:")
        for turn_type, times in turn_types.items():
            mean = statistics.mean(times)
            if len(times) > 1:
                stdev = statistics.stdev(times)
                print(f"    {turn_type} turn type: {mean:.4f}s avg, ±{stdev:.4f}s stdev")
            else:
                print(f"    {turn_type} turn type: {mean:.4f}s avg")
    
    # MCP overhead analysis
    print("\nMCP Overhead Analysis:")
    if True in mcp_results and False in mcp_results:
        print("  Overhead comparison (MCP enabled vs. disabled):")
        for resource_count in mcp_results[True].keys():
            if resource_count in mcp_results[False]:
                enabled_mean = statistics.mean(mcp_results[True][resource_count])
                disabled_mean = statistics.mean(mcp_results[False][resource_count])
                overhead = (enabled_mean - disabled_mean) / disabled_mean * 100 if disabled_mean > 0 else float('inf')
                print(f"    {resource_count} resources: {overhead:.1f}% overhead")
    
    for enabled, resource_counts in mcp_results.items():
        status = "enabled" if enabled else "disabled"
        print(f"  MCP {status}:")
        for count, times in resource_counts.items():
            mean = statistics.mean(times)
            if len(times) > 1:
                stdev = statistics.stdev(times)
                print(f"    {count} resources: {mean:.4f}s avg, ±{stdev:.4f}s stdev")
            else:
                print(f"    {count} resources: {mean:.4f}s avg")


# ----------------------
# Main Function
# ----------------------

async def main():
    """Run the Symphony benchmarks."""
    print("=== Symphony Framework Benchmarks ===")
    
    # 1. Agent response time
    agent_results = await benchmark_agent_response_time(
        agent_types=["reactive", "planner"],
        prompt_lengths=[50, 200, 1000],
        trials=3
    )
    
    # 2. Memory operations
    memory_results = await benchmark_memory_operations(
        memory_types=["in_memory", "conversation"],
        operation_counts=[10, 100, 1000],
        trials=3
    )
    
    # 3. Tool execution
    tool_results = await benchmark_tool_execution(
        tool_names=["fast_tool", "medium_tool", "slow_tool"],
        call_counts=[1, 10, 50],
        trials=3
    )
    
    # 4. Multi-agent coordination
    orchestration_results = await benchmark_multi_agent_coordination(
        agent_counts=[2, 5, 10],
        turn_types=[TurnType.SEQUENTIAL, TurnType.ROUND_ROBIN],
        trials=2
    )
    
    # 5. MCP overhead
    mcp_results = await benchmark_mcp_overhead(
        with_mcp=[False, True],
        resource_counts=[0, 5, 20],
        trials=3
    )
    
    # Analyze results
    analyze_results(
        agent_results,
        memory_results,
        tool_results,
        orchestration_results,
        mcp_results
    )
    
    print("\nBenchmarking complete.")


if __name__ == "__main__":
    asyncio.run(main())