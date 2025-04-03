"""Agent enhancements for robust tool execution."""

import logging
from typing import Any, Dict, Optional

from symphony.agents.base import AgentBase, ReactiveAgent
from symphony.core.events import Event, EventType
from symphony.tools.verification import (
    ChainRecoveryStrategy,
    ChainVerifier,
    LLMToolRecoveryStrategy,
    SafetyToolVerifier,
    SchemaToolVerifier,
    ToolExecutionMiddleware,
    ToolExecutionResult,
    ToolExecutionStatus,
)


class ToolVerificationMixin:
    """Mixin that adds robust tool verification capabilities to agents."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Extract relevant components from the agent
        llm_client = getattr(self, "llm_client", None)
        event_bus = kwargs.get("event_bus", None)
        
        # Set up the tool verification chain
        verifier = ChainVerifier([
            SchemaToolVerifier(),
            SafetyToolVerifier()
        ])
        
        # Set up recovery strategy if LLM client is available
        recovery_strategy = None
        if llm_client:
            recovery_strategy = ChainRecoveryStrategy([
                LLMToolRecoveryStrategy(llm_client)
            ])
        
        # Create middleware
        self.tool_middleware = ToolExecutionMiddleware(
            verifier=verifier,
            recovery_strategy=recovery_strategy,
            max_retries=2,
            timeout=10.0,
            event_bus=event_bus
        )
        
        # Add logger
        self.logger = logging.getLogger(f"symphony.agent.{self.id}")
    
    async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Call a tool with verification, recovery, and retry.
        
        Overrides the base call_tool method to add verification.
        """
        # Create an execution context
        context = {
            "agent_id": self.id,
            "agent_name": getattr(self, "config", {}).get("name", "unknown"),
            "agent_type": getattr(self, "config", {}).get("agent_type", "unknown")
        }
        
        # Execute with middleware
        result = await self.tool_middleware.execute(
            tool_name=tool_name,
            args=kwargs,
            agent=self,
            context=context
        )
        
        # Log the execution
        log_level = logging.INFO if result.status == ToolExecutionStatus.SUCCESS else logging.WARNING
        self.logger.log(log_level, f"Tool {tool_name} execution: {result.status} in {result.execution_time:.3f}s")
        
        # Handle result based on status
        if result.status in (ToolExecutionStatus.SUCCESS, ToolExecutionStatus.RETRY_SUCCESS):
            return result.result
        else:
            # Raise exception for failed execution
            error_msg = (
                f"Tool '{tool_name}' failed after {result.attempts} attempts: "
                f"{result.error or 'Unknown error'}"
            )
            raise RuntimeError(error_msg)


class ToolVerifiedReactiveAgent(ReactiveAgent, ToolVerificationMixin):
    """A reactive agent with tool verification capabilities."""
    
    async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Call a tool with verification."""
        # Use the mixin implementation
        return await ToolVerificationMixin.call_tool(self, tool_name, **kwargs)