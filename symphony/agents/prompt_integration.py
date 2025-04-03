"""Integration of the enhanced prompt system with agents."""

from typing import Any, Dict, List, Optional, Type

from symphony.agents.base import AgentBase, AgentConfig, ReactiveAgent
from symphony.prompts.enhanced_registry import EnhancedPromptRegistry


class PromptEnhancedAgentMixin:
    """Mixin that adds enhanced prompt capabilities to agents."""
    
    def _load_system_prompt(self) -> None:
        """Load the system prompt with enhanced functionality."""
        # Get tool names for prompt formatting
        tool_names = list(self.tools.keys()) if hasattr(self, 'tools') else []
        
        # Check if we're using the enhanced registry
        if isinstance(self.prompt_registry, EnhancedPromptRegistry):
            # Use enhanced prompt formatting
            formatted_prompt = self.prompt_registry.get_formatted_prompt(
                prompt_type=self.config.system_prompt_type,
                agent_type=self.config.agent_type,
                agent_instance=self.config.name,
                tool_names=tool_names,
                extra_variables=self._get_prompt_variables()
            )
            
            if formatted_prompt:
                self.system_prompt = formatted_prompt
                return
        
        # Fallback to original prompt loading if not using enhanced registry
        # or if enhanced formatting failed
        prompt_template = self.prompt_registry.get_prompt(
            prompt_type=self.config.system_prompt_type,
            agent_type=self.config.agent_type,
            agent_instance=self.config.name
        )
        
        if prompt_template:
            self.system_prompt = prompt_template.content
        else:
            # Default system prompt if none found
            tools_text = f" with access to these tools: {', '.join(tool_names)}" if tool_names else ""
            self.system_prompt = (
                f"You are {self.config.name}, a helpful AI assistant{tools_text}. "
                f"{self.config.description or ''}"
            )
    
    def _get_prompt_variables(self) -> Dict[str, Any]:
        """Get variables for prompt formatting specific to this agent instance."""
        return {
            "agent_name": self.config.name,
            "agent_description": self.config.description or "",
            "agent_id": self.id
        }


class PromptEnhancedReactiveAgent(ReactiveAgent, PromptEnhancedAgentMixin):
    """Reactive agent with enhanced prompt capabilities."""
    
    def _load_system_prompt(self) -> None:
        """Load the system prompt with enhanced functionality."""
        # Use the mixin implementation
        PromptEnhancedAgentMixin._load_system_prompt(self)


# Factory function for creating prompt-enhanced agents
def create_prompt_enhanced_agent(
    agent_cls: Type[AgentBase],
    config: AgentConfig,
    **kwargs: Any
) -> AgentBase:
    """Create an agent with enhanced prompt capabilities.
    
    Args:
        agent_cls: The agent class to enhance
        config: Agent configuration
        **kwargs: Additional arguments for agent initialization
        
    Returns:
        An agent instance with enhanced prompt capabilities
    """
    # Create a dynamic subclass that mixes in the prompt enhancement
    if not issubclass(agent_cls, PromptEnhancedAgentMixin):
        enhanced_cls = type(
            f"PromptEnhanced{agent_cls.__name__}",
            (agent_cls, PromptEnhancedAgentMixin),
            {}
        )
        
        # Create the enhanced agent
        return enhanced_cls(config=config, **kwargs)
    else:
        # Already enhanced
        return agent_cls(config=config, **kwargs)