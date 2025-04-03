"""Model Context Protocol (MCP) for dynamic context assembly."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Protocol, Union

from pydantic import BaseModel, Field
from symphony.utils.types import ContextItem, ContextPolicyType, Message


class TokenEstimator(Protocol):
    """Protocol for token estimation functions."""
    
    def __call__(self, text: str) -> int:
        """Estimate the number of tokens in the given text."""
        ...


def simple_token_estimator(text: str) -> int:
    """Simple token estimator that assumes 4 chars per token."""
    return len(text) // 4


class ContextPolicy(ABC):
    """Interface for context policies that determine how to fit context within token limits."""
    
    @abstractmethod
    def apply(
        self, 
        items: List[ContextItem], 
        max_tokens: int,
        estimator: TokenEstimator
    ) -> List[ContextItem]:
        """Apply the policy to fit items within token limits."""
        pass


class RecencyPolicy(ContextPolicy):
    """Policy that keeps the most recent items, dropping older ones."""
    
    def apply(
        self, 
        items: List[ContextItem], 
        max_tokens: int,
        estimator: TokenEstimator = simple_token_estimator
    ) -> List[ContextItem]:
        """Apply the policy to fit items within token limits."""
        total_tokens = 0
        result = []
        
        # Start from most recent (end of list) and work backwards
        for item in reversed(items):
            tokens = estimator(item.content)
            
            if total_tokens + tokens <= max_tokens:
                result.insert(0, item)  # Insert at beginning to maintain order
                total_tokens += tokens
            else:
                break
                
        return result


class ImportancePolicy(ContextPolicy):
    """Policy that keeps the most important items based on importance score."""
    
    def apply(
        self, 
        items: List[ContextItem], 
        max_tokens: int,
        estimator: TokenEstimator = simple_token_estimator
    ) -> List[ContextItem]:
        """Apply the policy to fit items within token limits."""
        # Sort by importance (descending)
        sorted_items = sorted(items, key=lambda x: x.importance, reverse=True)
        
        total_tokens = 0
        result = []
        item_map = {}  # Map original index to item
        
        # First pass: add as many items as possible by importance
        for i, item in enumerate(sorted_items):
            tokens = estimator(item.content)
            item_map[i] = (item, tokens)
            
            if total_tokens + tokens <= max_tokens:
                result.append(item)
                total_tokens += tokens
                
        # Sort result back to original order
        # (assuming the original order has some meaning, like chronology)
        original_indices = [items.index(item) for item in result]
        return [items[i] for i in sorted(original_indices)]


class ContextComposerConfig(BaseModel):
    """Configuration for context composer."""
    
    max_tokens: int = 4000
    policy_type: ContextPolicyType = ContextPolicyType.RECENCY
    token_estimator: Optional[TokenEstimator] = None
    system_prompt_max_tokens: int = 1000
    preserve_system_prompt: bool = True


class ContextComposer:
    """Assembles context for language model calls."""
    
    def __init__(self, config: Optional[ContextComposerConfig] = None):
        self.config = config or ContextComposerConfig()
        self.token_estimator = self.config.token_estimator or simple_token_estimator
        
        # Create the policy based on config
        if self.config.policy_type == ContextPolicyType.RECENCY:
            self.policy = RecencyPolicy()
        elif self.config.policy_type == ContextPolicyType.IMPORTANCE:
            self.policy = ImportancePolicy()
        else:
            # Default to recency for now
            self.policy = RecencyPolicy()
    
    def assemble_context(
        self,
        system_prompt: str,
        context_items: List[ContextItem]
    ) -> List[Message]:
        """Assemble context items into a list of messages."""
        messages = []
        
        # Always include system prompt
        system_tokens = self.token_estimator(system_prompt)
        
        # Adjust max tokens available for context items
        available_tokens = self.config.max_tokens - system_tokens
        
        if available_tokens <= 0:
            # System prompt is already too large, truncate it
            if self.config.preserve_system_prompt:
                # Keep system prompt but leave minimal space for context
                available_tokens = min(
                    self.config.max_tokens - self.config.system_prompt_max_tokens,
                    max(100, self.config.max_tokens // 5)  # At least 20% or 100 tokens
                )
                system_prompt = system_prompt[:self.config.system_prompt_max_tokens * 4]  # Rough char estimate
            else:
                # Truncate system prompt to fit
                system_prompt = system_prompt[:(self.config.max_tokens // 2) * 4]  # Rough char estimate
                available_tokens = self.config.max_tokens - self.token_estimator(system_prompt)
        
        # Apply policy to context items
        filtered_items = self.policy.apply(
            context_items, 
            available_tokens,
            self.token_estimator
        )
        
        # Construct messages
        messages.append(Message(role="system", content=system_prompt))
        
        for item in filtered_items:
            # Convert context items to messages
            # This is simplistic; in a real implementation, you might have
            # more complex logic for determining message roles
            role = item.metadata.get("role", "user")
            messages.append(Message(role=role, content=item.content))
            
        return messages