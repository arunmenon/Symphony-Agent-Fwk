"""Agent configuration domain model for Symphony.

This module provides configuration models for agents, allowing agent definitions
to be stored and retrieved independently of their runtime implementations.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator
import uuid
from pydantic.config import ConfigDict

class AgentCapabilities(BaseModel):
    """Agent capabilities definition.
    
    Capabilities define what an agent can do, including available tools,
    areas of expertise, and any limitations.
    """
    model_config = ConfigDict(extra="allow")
    
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    expertise: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)

class AgentConfig(BaseModel):
    """Agent configuration that can be persisted.
    
    An agent configuration defines all the parameters needed to create
    an agent instance. It can be stored and retrieved independently of
    the agent implementation.
    """
    model_config = ConfigDict(extra="allow")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str = ""
    description: str = ""
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    instruction_template: str
    config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def get_system_prompt(self, **kwargs) -> str:
        """Get system prompt with template variables filled in.
        
        Args:
            **kwargs: Variables to substitute in the template
            
        Returns:
            The rendered system prompt with variable substitutions
        """
        prompt = self.instruction_template
        for key, value in kwargs.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        return prompt