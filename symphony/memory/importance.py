"""Importance evaluation strategies for memory management."""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Union

from symphony.utils.types import Message


class ImportanceStrategy(ABC):
    """Abstract base class for importance calculation strategies."""
    
    @abstractmethod
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance score (0.0-1.0) for the given content.
        
        Args:
            content: The content to evaluate for importance
            context: Optional context about the agent, task, etc.
            
        Returns:
            Importance score between 0.0 and 1.0
        """
        pass


class RuleBasedStrategy(ImportanceStrategy):
    """Rule-based importance evaluation using keywords and patterns."""
    
    def __init__(
        self,
        action_keywords: Optional[List[str]] = None,
        question_bonus: float = 0.2,
        action_bonus: float = 0.3,
        user_bonus: float = 0.1,
        base_importance: float = 0.5
    ):
        """Initialize rule-based importance strategy with configurable parameters.
        
        Args:
            action_keywords: List of keywords that indicate important actions
            question_bonus: Importance bonus for questions
            action_bonus: Importance bonus for content with action keywords
            user_bonus: Importance bonus for user messages
            base_importance: Base importance value for all content
        """
        self.action_keywords = action_keywords or [
            "must", "should", "need to", "important", "critical", "decide", 
            "remember", "don't forget", "deadline", "urgent", "priority"
        ]
        self.question_bonus = question_bonus
        self.action_bonus = action_bonus
        self.user_bonus = user_bonus
        self.base_importance = base_importance
    
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance using rule-based heuristics."""
        if not content:
            return 0.0
            
        importance = self.base_importance
        content_lower = content.lower()
        
        # Check for questions
        if "?" in content:
            importance += self.question_bonus
            
        # Check for action keywords
        if any(keyword in content_lower for keyword in self.action_keywords):
            importance += self.action_bonus
            
        # Check message role if available in context
        if context and context.get("role") == "user":
            importance += self.user_bonus
            
        # Cap importance at 1.0
        return min(importance, 1.0)


class LLMBasedStrategy(ImportanceStrategy):
    """Calculate importance using an LLM for semantic understanding."""
    
    def __init__(
        self,
        llm_client,
        prompt_registry = None,
        prompt_key: str = "memory.importance_assessment",
        default_prompt: Optional[str] = None
    ):
        """Initialize LLM-based importance strategy.
        
        Args:
            llm_client: Client for LLM access
            prompt_registry: Optional registry for prompt templates
            prompt_key: Key to retrieve prompt from registry
            default_prompt: Default prompt to use if registry is unavailable
        """
        self.llm_client = llm_client
        self.prompt_registry = prompt_registry
        self.prompt_key = prompt_key
        self.default_prompt = default_prompt or (
            "Evaluate the importance of this information for an agent's memory on a scale of 0-10."
            "\nConsider how critical this information is for completing tasks and achieving goals."
            "\n\nContent: {content}"
            "\n\nImportance score (0-10):"
        )
    
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance using LLM evaluation."""
        if not content:
            return 0.0
            
        # Get prompt template (from registry or default)
        prompt_template = self._get_prompt_template(context)
        
        # Format prompt with content and context
        prompt_context = {"content": content}
        if context:
            prompt_context.update(context)
            
        prompt = prompt_template.format(**prompt_context)
        
        # Send to LLM
        response = await self.llm_client.generate(prompt)
        
        # Extract score from response
        score = self._extract_score(response)
        
        # Normalize to 0.0-1.0 range
        return score / 10.0
    
    def _get_prompt_template(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Get appropriate prompt template from registry or use default."""
        if self.prompt_registry:
            try:
                return self.prompt_registry.get_prompt(self.prompt_key, context or {})
            except:
                pass
        return self.default_prompt
    
    def _extract_score(self, response: str) -> float:
        """Extract numeric score from LLM response."""
        # Try to find a number in the response
        match = re.search(r'(\d+(\.\d+)?)', response)
        if match:
            score = float(match.group(1))
            return min(max(score, 0.0), 10.0)  # Clamp between 0-10
            
        # Default score if no number found
        return 5.0  # Neutral importance


class HybridStrategy(ImportanceStrategy):
    """Combine multiple importance strategies with weighted averaging."""
    
    def __init__(self, strategies: List[tuple[ImportanceStrategy, float]]):
        """Initialize hybrid strategy with weighted component strategies.
        
        Args:
            strategies: List of (strategy, weight) tuples
        """
        self.strategies = strategies
    
    async def calculate_importance(
        self, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate importance by combining multiple strategies."""
        if not content or not self.strategies:
            return 0.0
            
        # Calculate weighted scores from all strategies
        total_weight = sum(weight for _, weight in self.strategies)
        if total_weight == 0:
            return 0.0
            
        weighted_sum = 0.0
        for strategy, weight in self.strategies:
            score = await strategy.calculate_importance(content, context)
            weighted_sum += score * weight
            
        # Return weighted average
        return weighted_sum / total_weight


# Default strategy for backward compatibility
default_strategy = RuleBasedStrategy()