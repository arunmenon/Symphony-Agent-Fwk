"""Base interfaces for language model clients."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from symphony.utils.types import Message


class LLMClient(ABC):
    """Interface for language model clients."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from a prompt string."""
        pass
    
    @abstractmethod
    async def chat(self, messages: List[Message], **kwargs: Any) -> Message:
        """Generate a response to a list of chat messages."""
        pass
    
    @abstractmethod
    async def stream_chat(
        self, messages: List[Message], **kwargs: Any
    ) -> AsyncIterator[Message]:
        """Stream a response to a list of chat messages."""
        pass
    
    @abstractmethod
    async def function_call(
        self, 
        messages: List[Message], 
        functions: List[Dict[str, Any]], 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute a function call via the language model."""
        pass


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""
    
    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}
        
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from a prompt string."""
        # For testing, just return a fixed response based on prompt
        return self.responses.get(prompt, f"Mock response to: {prompt[:20]}...")
    
    async def chat(self, messages: List[Message], **kwargs: Any) -> Message:
        """Generate a response to a list of chat messages."""
        last_message = messages[-1] if messages else Message(role="user", content="")
        
        if last_message.content in self.responses:
            return Message(
                role="assistant",
                content=self.responses[last_message.content]
            )
        
        return Message(
            role="assistant",
            content=f"Mock response to: {last_message.content[:20]}..."
        )
    
    async def stream_chat(
        self, messages: List[Message], **kwargs: Any
    ) -> AsyncIterator[Message]:
        """Stream a response to a list of chat messages."""
        response = await self.chat(messages, **kwargs)
        words = response.content.split(" ")
        
        for i in range(len(words)):
            partial = " ".join(words[:i+1])
            yield Message(role="assistant", content=partial)
            await asyncio.sleep(0.01)  # Simulate streaming delay
    
    async def function_call(
        self, 
        messages: List[Message], 
        functions: List[Dict[str, Any]], 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute a function call via the language model."""
        # For mock, just return a call to the first function with empty params
        if not functions:
            return {"type": "message", "message": Message(role="assistant", content="No functions available")}
            
        function = functions[0]
        return {
            "type": "function_call",
            "function_call": {
                "name": function["name"],
                "arguments": {}
            }
        }