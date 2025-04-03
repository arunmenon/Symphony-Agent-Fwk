"""Environment interfaces for multi-agent interaction."""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from symphony.utils.types import Message


class EnvMessage(Message):
    """A message in an environment."""
    
    sender: str
    receiver: Optional[str] = None  # None means broadcast
    timestamp: float = Field(default_factory=lambda: __import__('time').time())
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class BaseEnvironment(ABC):
    """Base class for environments that allow agent interaction."""
    
    @abstractmethod
    def send_message(self, message: EnvMessage) -> None:
        """Send a message to the environment."""
        pass
    
    @abstractmethod
    def get_messages(
        self, 
        agent_id: str,
        since_timestamp: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[EnvMessage]:
        """Get messages for an agent."""
        pass
    
    @abstractmethod
    def store_state(self, key: str, value: Any) -> None:
        """Store a value in the environment state."""
        pass
    
    @abstractmethod
    def get_state(self, key: str) -> Optional[Any]:
        """Get a value from the environment state."""
        pass


class InMemoryEnvironment(BaseEnvironment):
    """Simple in-memory implementation of an environment."""
    
    def __init__(self):
        self.messages: List[EnvMessage] = []
        self.state: Dict[str, Any] = {}
    
    def send_message(self, message: EnvMessage) -> None:
        """Send a message to the environment."""
        self.messages.append(message)
    
    def get_messages(
        self, 
        agent_id: str,
        since_timestamp: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[EnvMessage]:
        """Get messages for an agent."""
        # Filter messages that are for this agent (direct or broadcast)
        agent_messages = [
            msg for msg in self.messages
            if msg.receiver is None or msg.receiver == agent_id
        ]
        
        # Filter by timestamp if provided
        if since_timestamp is not None:
            agent_messages = [
                msg for msg in agent_messages
                if msg.timestamp > since_timestamp
            ]
            
        # Sort by timestamp
        agent_messages = sorted(agent_messages, key=lambda msg: msg.timestamp)
        
        # Apply limit if provided
        if limit is not None:
            agent_messages = agent_messages[-limit:]
            
        return agent_messages
    
    def store_state(self, key: str, value: Any) -> None:
        """Store a value in the environment state."""
        self.state[key] = value
    
    def get_state(self, key: str) -> Optional[Any]:
        """Get a value from the environment state."""
        return self.state.get(key)
    
    def clear(self) -> None:
        """Clear all messages and state."""
        self.messages = []
        self.state = {}