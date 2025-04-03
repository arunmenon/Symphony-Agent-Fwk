"""DAG-based workflow orchestration."""

import asyncio
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from symphony.agents.base import AgentBase
from symphony.orchestration.base import Orchestrator, OrchestratorConfig
from symphony.utils.types import Message


class NodeType(str, Enum):
    """Types of nodes in a workflow DAG."""
    
    AGENT = "agent"  # Run an agent
    TOOL = "tool"    # Run a tool
    CONDITION = "condition"  # Branch based on a condition
    MERGE = "merge"  # Merge multiple paths
    START = "start"  # Start node
    END = "end"      # End node


class Edge(BaseModel):
    """An edge in a workflow DAG."""
    
    source: str
    target: str
    condition: Optional[str] = None  # Condition for conditional edges


class Node(BaseModel):
    """A node in a workflow DAG."""
    
    id: str
    type: NodeType
    config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DAG(BaseModel):
    """A directed acyclic graph representing a workflow."""
    
    nodes: Dict[str, Node] = Field(default_factory=dict)
    edges: List[Edge] = Field(default_factory=list)
    
    def add_node(self, node: Node) -> None:
        """Add a node to the DAG."""
        self.nodes[node.id] = node
    
    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the DAG."""
        self.edges.append(edge)
    
    def get_start_nodes(self) -> List[Node]:
        """Get all start nodes in the DAG."""
        # Find nodes that are of type START
        return [node for node in self.nodes.values() if node.type == NodeType.START]
    
    def get_end_nodes(self) -> List[Node]:
        """Get all end nodes in the DAG."""
        # Find nodes that are of type END
        return [node for node in self.nodes.values() if node.type == NodeType.END]
    
    def get_children(self, node_id: str) -> List[Node]:
        """Get all child nodes of a node."""
        child_ids = [edge.target for edge in self.edges if edge.source == node_id]
        return [self.nodes[node_id] for node_id in child_ids if node_id in self.nodes]
    
    def get_parents(self, node_id: str) -> List[Node]:
        """Get all parent nodes of a node."""
        parent_ids = [edge.source for edge in self.edges if edge.target == node_id]
        return [self.nodes[node_id] for node_id in parent_ids if node_id in self.nodes]
    
    def get_outgoing_edges(self, node_id: str) -> List[Edge]:
        """Get all outgoing edges of a node."""
        return [edge for edge in self.edges if edge.source == node_id]


class NodeResult(BaseModel):
    """Result of executing a node."""
    
    node_id: str
    output: Any
    success: bool = True
    error: Optional[str] = None


class DAGExecutionState(BaseModel):
    """State of a DAG execution."""
    
    dag: DAG
    results: Dict[str, NodeResult] = Field(default_factory=dict)
    completed_nodes: Set[str] = Field(default_factory=set)
    ready_nodes: Set[str] = Field(default_factory=set)
    active_nodes: Set[str] = Field(default_factory=set)
    error_nodes: Set[str] = Field(default_factory=set)
    
    def mark_completed(self, node_id: str, result: NodeResult) -> None:
        """Mark a node as completed."""
        self.results[node_id] = result
        self.completed_nodes.add(node_id)
        self.active_nodes.discard(node_id)
        
        if not result.success:
            self.error_nodes.add(node_id)
    
    def mark_ready(self, node_id: str) -> None:
        """Mark a node as ready to execute."""
        self.ready_nodes.add(node_id)
    
    def mark_active(self, node_id: str) -> None:
        """Mark a node as currently executing."""
        self.ready_nodes.discard(node_id)
        self.active_nodes.add(node_id)
    
    def is_complete(self) -> bool:
        """Check if the DAG execution is complete."""
        # Either all nodes are completed, or we have errors and no more active/ready nodes
        all_nodes_complete = len(self.completed_nodes) == len(self.dag.nodes)
        no_more_progress = (not self.ready_nodes and not self.active_nodes) and self.error_nodes
        
        return all_nodes_complete or no_more_progress
    
    def get_next_ready_node(self) -> Optional[str]:
        """Get the next ready node to execute."""
        if not self.ready_nodes:
            return None
        return next(iter(self.ready_nodes))


class DAGOrchestrator(Orchestrator):
    """An orchestrator that executes a workflow defined as a DAG."""
    
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.dag: Optional[DAG] = None
        
    def set_dag(self, dag: DAG) -> None:
        """Set the DAG to execute."""
        self.dag = dag
    
    async def run(self, input_message: str) -> str:
        """Run the DAG workflow with an input message."""
        if not self.dag:
            return "No DAG configured"
            
        # Initialize execution state
        state = DAGExecutionState(dag=self.dag)
        
        # Find start nodes and mark them as ready
        start_nodes = self.dag.get_start_nodes()
        for node in start_nodes:
            state.mark_ready(node.id)
        
        # Execute until complete
        while not state.is_complete() and state.ready_nodes:
            # Get a ready node
            node_id = state.get_next_ready_node()
            if not node_id:
                break
                
            # Mark as active
            state.mark_active(node_id)
            
            # Execute the node
            try:
                node = self.dag.nodes[node_id]
                result = await self._execute_node(node, input_message, state)
                state.mark_completed(node_id, result)
                
                # If successful, mark child nodes as ready if all their parents are complete
                if result.success:
                    child_nodes = self.dag.get_children(node_id)
                    for child in child_nodes:
                        # Check if all parents are complete
                        parents = self.dag.get_parents(child.id)
                        parents_complete = all(parent.id in state.completed_nodes for parent in parents)
                        
                        if parents_complete:
                            state.mark_ready(child.id)
            except Exception as e:
                state.mark_completed(
                    node_id, 
                    NodeResult(
                        node_id=node_id,
                        output=None,
                        success=False,
                        error=str(e)
                    )
                )
        
        # Return final result
        end_nodes = self.dag.get_end_nodes()
        for node in end_nodes:
            if node.id in state.results:
                return str(state.results[node.id].output)
                
        # If no end node was reached, return a summary
        success_count = len(state.completed_nodes) - len(state.error_nodes)
        error_count = len(state.error_nodes)
        
        return f"Workflow completed with {success_count} successful nodes and {error_count} errors."
    
    async def _execute_node(
        self, 
        node: Node, 
        input_message: str, 
        state: DAGExecutionState
    ) -> NodeResult:
        """Execute a single node based on its type."""
        if node.type == NodeType.START:
            return NodeResult(node_id=node.id, output=input_message)
            
        elif node.type == NodeType.END:
            # Get output from direct parent nodes
            parent_results = [state.results[parent.id] for parent in self.dag.get_parents(node.id)]
            outputs = [result.output for result in parent_results if result.success]
            
            # Combine outputs
            combined_output = "\n".join(str(output) for output in outputs)
            return NodeResult(node_id=node.id, output=combined_output)
            
        elif node.type == NodeType.AGENT:
            agent_name = node.config.get("agent_name")
            if not agent_name or agent_name not in self.agents:
                return NodeResult(
                    node_id=node.id,
                    output=None,
                    success=False,
                    error=f"Agent '{agent_name}' not found"
                )
                
            agent = self.agents[agent_name]
            
            # Get input from parent nodes
            parent_results = [state.results[parent.id] for parent in self.dag.get_parents(node.id)]
            
            # If there's only one parent, use its output directly
            if len(parent_results) == 1:
                agent_input = str(parent_results[0].output)
            else:
                # Otherwise, combine all parent outputs
                agent_input = "\n".join(str(result.output) for result in parent_results if result.success)
                
            # Run the agent
            agent_output = await agent.run(agent_input)
            return NodeResult(node_id=node.id, output=agent_output)
            
        elif node.type == NodeType.CONDITION:
            # Get input from parent node
            parent_results = [state.results[parent.id] for parent in self.dag.get_parents(node.id)]
            if not parent_results:
                return NodeResult(
                    node_id=node.id,
                    output=None,
                    success=False,
                    error="Condition node has no parent"
                )
                
            # Use the first successful parent result
            parent_result = next((r for r in parent_results if r.success), None)
            if not parent_result:
                return NodeResult(
                    node_id=node.id,
                    output=None,
                    success=False,
                    error="All parent nodes failed"
                )
                
            input_value = parent_result.output
            
            # Evaluate condition
            condition_result = self._evaluate_condition(input_value, node.config.get("condition", ""))
            
            # Set result
            return NodeResult(node_id=node.id, output=condition_result)
            
        else:
            return NodeResult(
                node_id=node.id,
                output=None,
                success=False,
                error=f"Unsupported node type: {node.type}"
            )
    
    def _evaluate_condition(self, input_value: Any, condition: str) -> bool:
        """Evaluate a condition on an input value."""
        # This is a simple implementation that just checks if a condition string is in the input
        if isinstance(input_value, str) and condition:
            return condition.lower() in input_value.lower()
        return False