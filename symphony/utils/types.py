"""Common types used throughout Symphony."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A message in a conversation."""
    
    role: str
    content: str
    additional_kwargs: Dict[str, Any] = Field(default_factory=dict)


class ContextItem(BaseModel):
    """A single item of context to be included in a prompt."""
    
    content: str
    importance: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextPolicyType(str, Enum):
    """Types of context policies."""
    
    RECENCY = "recency"
    IMPORTANCE = "importance"
    HYBRID = "hybrid"
    CUSTOM = "custom"


class ToolCallResult(BaseModel):
    """Result of a tool call."""
    
    tool_name: str
    inputs: Dict[str, Any]
    outputs: Any
    is_success: bool = True
    error_message: Optional[str] = None