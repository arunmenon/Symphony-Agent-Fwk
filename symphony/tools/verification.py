"""Tool verification and reliability system for Symphony."""

import asyncio
import functools
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ValidationError

from symphony.core.events import Event
from symphony.tools.base import Tool, ToolRegistry


class ToolExecutionStatus(str, Enum):
    """Status of a tool execution."""
    
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"
    RETRY_SUCCESS = "retry_success"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"


class ToolExecutionResult(BaseModel):
    """Result of a tool execution with metadata."""
    
    tool_name: str
    status: ToolExecutionStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 1
    execution_time: float = 0.0
    timestamp: str = datetime.now().isoformat()


class ToolVerifier(ABC):
    """Abstract base class for tool verifiers."""
    
    @abstractmethod
    async def verify(
        self, 
        tool: Tool, 
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Verify tool arguments before execution.
        
        Args:
            tool: The tool to verify
            args: The arguments to verify
            context: Optional execution context
            
        Returns:
            Dictionary of validated arguments, potentially modified
        """
        pass


class SchemaToolVerifier(ToolVerifier):
    """Verifier that uses the tool's schema to validate arguments."""
    
    async def verify(
        self, 
        tool: Tool, 
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Verify tool arguments using the tool's schema."""
        if not tool.schema:
            # No schema to verify against
            return args
            
        try:
            # Validate arguments using the tool's schema
            validated = tool.schema(**args)
            return validated.dict()
        except ValidationError as e:
            # Re-raise with more context
            raise ValidationError(
                errors=e.errors(),
                model=e.model,
                extra={"tool_name": tool.name}
            )


class SafetyToolVerifier(ToolVerifier):
    """Verifier that checks for potentially harmful arguments."""
    
    def __init__(self, blocklist: Optional[List[str]] = None):
        self.blocklist = blocklist or ["rm -rf", "DROP TABLE", "DELETE FROM", "FORMAT", "shutdown"]
    
    async def verify(
        self, 
        tool: Tool, 
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Verify tool arguments for potential safety issues."""
        # Check string arguments against blocklist
        for key, value in args.items():
            if isinstance(value, str):
                for blocked in self.blocklist:
                    if blocked.lower() in value.lower():
                        raise ValueError(
                            f"Potentially harmful argument detected in '{key}': '{value}'"
                        )
        
        return args


class ChainVerifier(ToolVerifier):
    """Chain of responsibility for multiple verifiers."""
    
    def __init__(self, verifiers: List[ToolVerifier]):
        self.verifiers = verifiers
    
    async def verify(
        self, 
        tool: Tool, 
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run all verifiers in sequence."""
        current_args = args
        
        for verifier in self.verifiers:
            current_args = await verifier.verify(tool, current_args, context)
            
        return current_args


class ToolRecoveryStrategy(ABC):
    """Abstract base class for tool recovery strategies."""
    
    @abstractmethod
    async def recover(
        self, 
        tool: Tool, 
        args: Dict[str, Any], 
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Attempt to recover from a tool execution error.
        
        Args:
            tool: The tool that failed
            args: The arguments that caused the failure
            error: The exception that was raised
            context: Optional execution context
            
        Returns:
            Fixed arguments if recovery is possible, None otherwise
        """
        pass


class LLMToolRecoveryStrategy(ToolRecoveryStrategy):
    """Recovery strategy that uses an LLM to fix arguments."""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def recover(
        self, 
        tool: Tool, 
        args: Dict[str, Any], 
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to fix invalid tool arguments."""
        # Format original arguments as JSON string
        args_str = json.dumps(args, indent=2)
        
        # Prepare prompt for the LLM
        prompt = f"""You are tasked with fixing invalid arguments for a tool call.

Tool Name: {tool.name}
Tool Description: {tool.description}

Original Arguments:
```json
{args_str}
```

Error:
{str(error)}

Please provide corrected arguments in valid JSON format that will resolve this error.
Only respond with the corrected JSON and nothing else.
"""
        
        try:
            # Call LLM to get fixed arguments
            response = await self.llm_client.generate(prompt)
            
            # Extract JSON from response
            # Look for JSON between code fences, or just take the whole response
            json_str = response
            if "```json" in response and "```" in response.split("```json", 1)[1]:
                json_str = response.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in response and "```" in response.split("```", 1)[1]:
                json_str = response.split("```", 1)[1].split("```", 1)[0].strip()
            
            # Parse the JSON
            fixed_args = json.loads(json_str)
            
            # Validate the fixed arguments against the tool schema
            if tool.schema:
                try:
                    validated = tool.schema(**fixed_args)
                    return validated.dict()
                except ValidationError:
                    # If still invalid, give up
                    return None
            
            return fixed_args
        except Exception as e:
            # Recovery failed
            logging.warning(f"LLM recovery failed for {tool.name}: {str(e)}")
            return None


class ChainRecoveryStrategy(ToolRecoveryStrategy):
    """Chain of responsibility for multiple recovery strategies."""
    
    def __init__(self, strategies: List[ToolRecoveryStrategy]):
        self.strategies = strategies
    
    async def recover(
        self, 
        tool: Tool, 
        args: Dict[str, Any], 
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Try all recovery strategies in sequence."""
        for strategy in self.strategies:
            fixed_args = await strategy.recover(tool, args, error, context)
            if fixed_args is not None:
                return fixed_args
                
        # No strategy could recover
        return None


class ToolExecutionMiddleware:
    """Middleware for tool execution with verification, recovery, and retry."""
    
    def __init__(
        self,
        verifier: Optional[ToolVerifier] = None,
        recovery_strategy: Optional[ToolRecoveryStrategy] = None,
        max_retries: int = 2,
        timeout: Optional[float] = None,
        event_bus = None
    ):
        self.verifier = verifier or SchemaToolVerifier()
        self.recovery_strategy = recovery_strategy
        self.max_retries = max_retries
        self.timeout = timeout
        self.event_bus = event_bus
        
    async def execute(
        self,
        tool_name: str,
        args: Dict[str, Any],
        agent = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ToolExecutionResult:
        """Execute a tool with verification, recovery, and retry.
        
        Args:
            tool_name: Name of the tool to execute
            args: Arguments for the tool
            agent: Optional agent for recovery or context
            context: Optional execution context
            
        Returns:
            ToolExecutionResult with status and result or error
        """
        # Get the tool
        tool = ToolRegistry.get(tool_name)
        if not tool:
            return ToolExecutionResult(
                tool_name=tool_name,
                status=ToolExecutionStatus.EXECUTION_ERROR,
                error=f"Tool '{tool_name}' not found"
            )
            
        start_time = datetime.now()
        attempts = 0
        
        # Track context if not provided
        if context is None:
            context = {}
            
        # Add agent information to context
        if agent:
            context["agent_id"] = getattr(agent, "id", None)
            context["agent_name"] = getattr(agent, "config", {}).get("name", None)
            
        # Try to execute with retries
        last_error = None
        for attempt in range(self.max_retries + 1):
            attempts += 1
            
            try:
                # Publish tool_called event
                if self.event_bus:
                    self.event_bus.publish(Event.create(
                        type="tool:called",
                        source=context.get("agent_name", "unknown"),
                        tool_name=tool_name,
                        args=args,
                        attempt=attempt
                    ))
                
                # Verify arguments
                try:
                    validated_args = await self.verifier.verify(tool, args, context)
                except Exception as e:
                    # Arguments failed validation
                    last_error = e
                    
                    # Attempt recovery if available
                    if self.recovery_strategy and attempt < self.max_retries:
                        fixed_args = await self.recovery_strategy.recover(tool, args, e, context)
                        if fixed_args:
                            # Try again with fixed arguments
                            args = fixed_args
                            continue
                    
                    # Can't recover, return error
                    return ToolExecutionResult(
                        tool_name=tool_name,
                        status=ToolExecutionStatus.VALIDATION_ERROR,
                        error=str(e),
                        attempts=attempts,
                        execution_time=(datetime.now() - start_time).total_seconds()
                    )
                
                # Execute tool with timeout if specified
                if self.timeout:
                    try:
                        result = await asyncio.wait_for(
                            asyncio.to_thread(functools.partial(tool, **validated_args)),
                            timeout=self.timeout
                        )
                    except asyncio.TimeoutError:
                        # Tool execution timed out
                        if attempt >= self.max_retries:
                            return ToolExecutionResult(
                                tool_name=tool_name,
                                status=ToolExecutionStatus.TIMEOUT,
                                error=f"Tool execution timed out after {self.timeout}s",
                                attempts=attempts,
                                execution_time=self.timeout
                            )
                        last_error = asyncio.TimeoutError(f"Timeout after {self.timeout}s")
                        continue
                else:
                    # Execute without timeout
                    result = await asyncio.to_thread(functools.partial(tool, **validated_args))
                
                # Publish tool_succeeded event
                if self.event_bus:
                    self.event_bus.publish(Event.create(
                        type="tool:succeeded",
                        source=context.get("agent_name", "unknown"),
                        tool_name=tool_name,
                        args=args,
                        result=result
                    ))
                
                # Return successful result
                status = (
                    ToolExecutionStatus.RETRY_SUCCESS if attempt > 0 
                    else ToolExecutionStatus.SUCCESS
                )
                
                return ToolExecutionResult(
                    tool_name=tool_name,
                    status=status,
                    result=result,
                    attempts=attempts,
                    execution_time=(datetime.now() - start_time).total_seconds()
                )
                
            except Exception as e:
                # Tool execution failed
                last_error = e
                
                # Publish tool_failed event
                if self.event_bus:
                    self.event_bus.publish(Event.create(
                        type="tool:failed",
                        source=context.get("agent_name", "unknown"),
                        tool_name=tool_name,
                        args=args,
                        error=str(e),
                        attempt=attempt
                    ))
                
                # Try recovery if available
                if self.recovery_strategy and attempt < self.max_retries:
                    fixed_args = await self.recovery_strategy.recover(tool, args, e, context)
                    if fixed_args:
                        # Try again with fixed arguments
                        args = fixed_args
                        continue
        
        # Max retries exceeded
        return ToolExecutionResult(
            tool_name=tool_name,
            status=ToolExecutionStatus.MAX_RETRIES_EXCEEDED,
            error=str(last_error),
            attempts=attempts,
            execution_time=(datetime.now() - start_time).total_seconds()
        )