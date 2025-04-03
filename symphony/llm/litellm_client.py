"""LiteLLM-based client implementation for LLM providers."""

import asyncio
import json
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from litellm import acompletion, completion
from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field

from symphony.llm.base import LLMClient
from symphony.utils.types import Message


class LiteLLMConfig(BaseModel):
    """Configuration for LiteLLM client."""
    
    model: str  # Format: "provider/model_name" (e.g., "openai/gpt-4", "anthropic/claude-3-sonnet")
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 1.0
    timeout: Optional[int] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    litellm_params: Dict[str, Any] = Field(default_factory=dict)


class LiteLLMClient(LLMClient):
    """LLM client using LiteLLM for multi-provider support."""
    
    def __init__(self, config: LiteLLMConfig):
        """Initialize the LiteLLM client."""
        self.config = config
        
        # Set up common params for LiteLLM calls
        self.common_params = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
        }
        
        # Add optional params if provided
        if config.timeout is not None:
            self.common_params["request_timeout"] = config.timeout
        
        if config.api_key is not None:
            self.common_params["api_key"] = config.api_key
            
        if config.api_base is not None:
            self.common_params["api_base"] = config.api_base
            
        # Add any additional litellm-specific params
        self.common_params.update(config.litellm_params)
    
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from a prompt string."""
        messages = [{"role": "user", "content": prompt}]
        params = {**self.common_params, **kwargs, "messages": messages}
        
        response = await acompletion(**params)
        
        return response.choices[0].message.content
    
    async def chat(self, messages: List[Message], **kwargs: Any) -> Message:
        """Generate a response to a list of chat messages."""
        # Convert Symphony Message objects to LiteLLM format
        litellm_messages = [
            {"role": msg.role, "content": msg.content, **msg.additional_kwargs}
            for msg in messages
        ]
        
        params = {**self.common_params, **kwargs, "messages": litellm_messages}
        
        response = await acompletion(**params)
        
        # Convert LiteLLM response to Symphony Message format
        return Message(
            role="assistant",
            content=response.choices[0].message.content,
            additional_kwargs={"model": self.config.model}
        )
    
    async def chat_with_mcp(
        self, 
        messages: List[Message], 
        mcp_context: Context,
        **kwargs: Any
    ) -> Message:
        """Generate a response to chat messages with MCP context."""
        # Convert Symphony Message objects to LiteLLM format
        litellm_messages = [
            {"role": msg.role, "content": msg.content, **msg.additional_kwargs}
            for msg in messages
        ]
        
        # For a real implementation with MCP, we would set up the MCP context
        # in a way the LLM can use. This would depend on the specific LLM provider.
        # Here we're adding a header to indicate MCP is being used
        system_message = litellm_messages[0] if litellm_messages and litellm_messages[0]["role"] == "system" else None
        
        # If there's a system message, append MCP info
        if system_message:
            # Enhance system message with MCP context info
            system_message["content"] = f"{system_message['content']}\n\nContext is available via MCP."
        else:
            # Create a new system message
            litellm_messages.insert(0, {
                "role": "system", 
                "content": "Context is available via MCP."
            })
        
        params = {**self.common_params, **kwargs, "messages": litellm_messages}
        
        # In a real implementation, we would use MCP-specific headers or metadata
        # For now, we'll just make the regular call
        response = await acompletion(**params)
        
        # Convert LiteLLM response to Symphony Message format
        return Message(
            role="assistant",
            content=response.choices[0].message.content,
            additional_kwargs={"model": self.config.model}
        )
    
    async def stream_chat(
        self, messages: List[Message], **kwargs: Any
    ) -> AsyncIterator[Message]:
        """Stream a response to a list of chat messages."""
        # Convert Symphony Message objects to LiteLLM format
        litellm_messages = [
            {"role": msg.role, "content": msg.content, **msg.additional_kwargs}
            for msg in messages
        ]
        
        params = {
            **self.common_params, 
            **kwargs, 
            "messages": litellm_messages,
            "stream": True
        }
        
        # Get streaming response
        response_stream = await acompletion(**params)
        
        current_content = ""
        
        # Stream chunks
        async for chunk in response_stream:
            if hasattr(chunk.choices[0], "delta") and hasattr(chunk.choices[0].delta, "content"):
                delta_content = chunk.choices[0].delta.content
                if delta_content:
                    current_content += delta_content
                    yield Message(
                        role="assistant",
                        content=current_content,
                        additional_kwargs={"model": self.config.model}
                    )
    
    async def function_call(
        self, 
        messages: List[Message], 
        functions: List[Dict[str, Any]], 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute a function call via the language model."""
        # Convert Symphony Message objects to LiteLLM format
        litellm_messages = [
            {"role": msg.role, "content": msg.content, **msg.additional_kwargs}
            for msg in messages
        ]
        
        # Convert Symphony functions to LiteLLM's format (OpenAI-compatible)
        tools = [{"type": "function", "function": func} for func in functions]
        
        params = {
            **self.common_params, 
            **kwargs, 
            "messages": litellm_messages,
            "tools": tools,
            "tool_choice": "auto"  # Let the model decide
        }
        
        response = await acompletion(**params)
        
        # Check if the response contains a function call
        if (hasattr(response.choices[0].message, "tool_calls") and 
            response.choices[0].message.tool_calls):
            tool_call = response.choices[0].message.tool_calls[0]
            function_name = tool_call.function.name
            
            try:
                # Parse arguments from the JSON string
                arguments = json.loads(tool_call.function.arguments)
            except:
                arguments = {}
                
            return {
                "type": "function_call",
                "function_call": {
                    "name": function_name,
                    "arguments": arguments
                }
            }
        else:
            # No function call, just a regular message
            return {
                "type": "message",
                "message": Message(
                    role="assistant",
                    content=response.choices[0].message.content,
                    additional_kwargs={"model": self.config.model}
                )
            }