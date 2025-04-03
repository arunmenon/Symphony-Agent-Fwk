"""Agent reflection system for improved decision quality."""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from symphony.agents.base import AgentBase
from symphony.utils.types import Message


class ReflectionResult(BaseModel):
    """Result of an agent's reflection."""
    
    original_thought: str
    reflection: str
    improved_thought: Optional[str] = None
    changes_made: bool = False
    confidence: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReflectionStrategy:
    """Strategy for agent reflection."""
    
    async def reflect(
        self, 
        agent: AgentBase, 
        thought: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ReflectionResult:
        """Reflect on a thought to potentially improve it.
        
        Args:
            agent: The agent doing the reflection
            thought: The original thought to reflect on
            context: Optional context information
            
        Returns:
            Result of the reflection process
        """
        # Default implementation - concrete strategies should override
        return ReflectionResult(
            original_thought=thought,
            reflection="No reflection performed.",
            improved_thought=None,
            changes_made=False,
            confidence=1.0
        )


class LLMSelfReflectionStrategy(ReflectionStrategy):
    """Reflection strategy using the agent's own LLM."""
    
    async def reflect(
        self, 
        agent: AgentBase, 
        thought: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ReflectionResult:
        """Use the agent's LLM to reflect on a thought."""
        context = context or {}
        
        # Construct reflection prompt
        reflection_prompt = self._build_reflection_prompt(thought, context)
        
        # Run reflection through the LLM
        reflection_message = await agent.llm_client.chat([
            Message(role="system", content="You are a reflection system that improves reasoning."),
            Message(role="user", content=reflection_prompt)
        ])
        
        reflection = reflection_message.content
        
        # Analyze if changes are suggested
        improved_thought, confidence = self._parse_reflection(reflection, thought)
        changes_made = improved_thought is not None and improved_thought != thought
        
        # Return reflection result
        return ReflectionResult(
            original_thought=thought,
            reflection=reflection,
            improved_thought=improved_thought,
            changes_made=changes_made,
            confidence=confidence,
            metadata={"context": context}
        )
    
    def _build_reflection_prompt(
        self, 
        thought: str, 
        context: Dict[str, Any]
    ) -> str:
        """Build a prompt for the reflection."""
        task = context.get("task", "the task")
        
        prompt = f"""Please reflect on the following reasoning:

ORIGINAL REASONING:
{thought}

Consider:
1. Are there any logical errors or inconsistencies?
2. Are there any unstated assumptions that should be examined?
3. Are there alternative approaches that could be more effective?
4. Is the reasoning complete and addressing all aspects of {task}?
5. Are there any biases that might be influencing the reasoning?

First, provide your reflection on the reasoning. Then, if improvements are needed, provide an improved version.

Format your response as:

REFLECTION:
[Your critical reflection on the original reasoning]

IMPROVED REASONING (if needed):
[Improved reasoning that addresses the issues you identified]

CONFIDENCE: [A number between 0 and 1 indicating your confidence in the improved reasoning]

If no improvements are needed, simply state that in the REFLECTION section and leave the IMPROVED REASONING section empty.
"""
        return prompt
    
    def _parse_reflection(
        self, 
        reflection: str, 
        original_thought: str
    ) -> Tuple[Optional[str], float]:
        """Parse the reflection response to extract improved thought and confidence."""
        improved_thought = None
        confidence = 1.0
        
        # Extract improved reasoning if present
        if "IMPROVED REASONING" in reflection:
            parts = reflection.split("IMPROVED REASONING")
            if len(parts) > 1:
                improved_section = parts[1].strip()
                if improved_section.startswith(":"):
                    improved_section = improved_section[1:].strip()
                    
                if improved_section and "CONFIDENCE" not in improved_section:
                    improved_thought = improved_section
        
        # Extract confidence if present
        if "CONFIDENCE:" in reflection:
            confidence_part = reflection.split("CONFIDENCE:")[1].split("\n")[0].strip()
            try:
                confidence_value = float(confidence_part)
                if 0 <= confidence_value <= 1:
                    confidence = confidence_value
            except (ValueError, IndexError):
                pass
        
        # If no improved thought found but reflection indicates no changes needed
        if not improved_thought and ("no improvements" in reflection.lower() or 
                                     "reasoning is sound" in reflection.lower()):
            return original_thought, confidence
            
        return improved_thought, confidence


class ReflectionPhase:
    """A phase that adds reflection capabilities to agent workflows."""
    
    def __init__(
        self, 
        strategy: Optional[ReflectionStrategy] = None,
        confidence_threshold: float = 0.7,
        logger = None
    ):
        self.strategy = strategy or LLMSelfReflectionStrategy()
        self.confidence_threshold = confidence_threshold
        self.logger = logger or logging.getLogger("symphony.reflection")
    
    async def reflect_on_thought(
        self, 
        agent: AgentBase, 
        thought: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Reflect on and potentially improve a thought.
        
        Args:
            agent: The agent doing the reflection
            thought: The thought to reflect on
            context: Optional context for the reflection
            
        Returns:
            The original or improved thought
        """
        context = context or {}
        
        # Skip reflection if thought is too short
        if len(thought) < 50:
            return thought
            
        try:
            # Perform reflection
            result = await self.strategy.reflect(agent, thought, context)
            
            # Log reflection
            self.logger.debug(f"Reflection by {getattr(agent, 'id', 'unknown')}:")
            self.logger.debug(f"Original: {thought[:100]}...")
            self.logger.debug(f"Reflection: {result.reflection[:100]}...")
            
            # Return improved thought if available and confidence is high enough
            if (result.improved_thought and 
                result.changes_made and 
                result.confidence >= self.confidence_threshold):
                self.logger.info(f"Using improved thought (confidence: {result.confidence:.2f})")
                return result.improved_thought
                
        except Exception as e:
            self.logger.warning(f"Reflection failed: {str(e)}")
            
        # Default to original thought
        return thought
    
    async def reflect_on_plan(
        self, 
        agent: AgentBase, 
        plan: str, 
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Reflect on and potentially improve a plan.
        
        Args:
            agent: The agent doing the reflection
            plan: The plan to reflect on
            task: The task the plan is addressing
            context: Optional additional context
            
        Returns:
            The original or improved plan
        """
        context = context or {}
        context["task"] = task
        context["is_plan"] = True
        
        return await self.reflect_on_thought(agent, plan, context)


class ReflectiveAgentMixin:
    """Mixin that adds reflection capabilities to agents."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize reflection phase
        self.reflection_phase = ReflectionPhase()
        
    async def reflect(
        self, 
        thought: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Reflect on a thought before acting on it."""
        return await self.reflection_phase.reflect_on_thought(self, thought, context)