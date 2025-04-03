"""Enhanced prompt registry with fallback chain and template processing."""

import datetime
import string
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from symphony.prompts.registry import PromptRegistry, PromptTemplate
from symphony.prompts.templates import DEFAULT_PROMPTS, DEFAULT_VARIABLES


class PromptFormatter:
    """Strategy for formatting prompts with variables."""
    
    @staticmethod
    def format_prompt(
        prompt_content: str, 
        variables: Dict[str, Any], 
        tool_names: Optional[List[str]] = None
    ) -> str:
        """Format a prompt template with variables and tool information."""
        # Create a copy of variables to avoid modifying the original
        format_vars = dict(variables)
        
        # Add tool names if provided
        if tool_names:
            format_vars["tool_names"] = ", ".join(tool_names)
        else:
            format_vars["tool_names"] = "none available"
            
        # Add current date if not present
        if "current_date" not in format_vars:
            format_vars["current_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
            
        # Use string.Template for safer formatting (compared to .format())
        template = string.Template(prompt_content)
        try:
            return template.substitute(format_vars)
        except KeyError:
            # Fallback to safe_substitute which doesn't throw on missing keys
            return template.safe_substitute(format_vars)


class EnhancedPromptRegistry(PromptRegistry):
    """Enhanced prompt registry with fallback chain and template processing."""
    
    def __init__(self, registry_path: Optional[str] = None):
        """Initialize the enhanced prompt registry."""
        super().__init__(registry_path)
        self.formatter = PromptFormatter()
        self.variables = dict(DEFAULT_VARIABLES["all"])  # Start with global variables
        
    def register_variable(self, name: str, value: Any, agent_type: Optional[str] = None) -> None:
        """Register a variable for prompt formatting.
        
        Args:
            name: Variable name
            value: Variable value
            agent_type: Optional agent type to scope the variable
        """
        if agent_type:
            # Create agent type dict if it doesn't exist
            if agent_type not in self.variables:
                self.variables[agent_type] = {}
                
            # Register variable for specific agent type
            self.variables[agent_type][name] = value
        else:
            # Register global variable
            self.variables[name] = value
    
    def get_formatted_prompt(
        self,
        prompt_type: str,
        agent_type: Optional[str] = None,
        agent_instance: Optional[str] = None,
        tool_names: Optional[List[str]] = None,
        extra_variables: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Get a formatted prompt with fallback chain and variable substitution.
        
        The fallback chain is:
        1. Instance-specific prompt (if agent_instance provided)
        2. Agent-type prompt (if agent_type provided)
        3. Global prompt
        4. Default template
        5. Generic fallback
        
        Args:
            prompt_type: Type of prompt to retrieve
            agent_type: Optional agent type
            agent_instance: Optional agent instance name
            tool_names: Optional list of tool names for formatting
            extra_variables: Optional additional variables for formatting
            
        Returns:
            Formatted prompt content or None if not found
        """
        # Start with the prompt template from the registry (using original chain)
        prompt_template = self.get_prompt(
            prompt_type=prompt_type,
            agent_type=agent_type,
            agent_instance=agent_instance
        )
        
        prompt_content = None
        if prompt_template:
            prompt_content = prompt_template.content
        elif agent_type and agent_type.lower() in DEFAULT_PROMPTS:
            # Fallback to default template if available
            prompt_content = DEFAULT_PROMPTS[agent_type.lower()]
        else:
            # Ultimate fallback
            prompt_content = f"You are a helpful {agent_type or 'assistant'} designed to accomplish tasks effectively."
        
        # Collect variables for formatting
        format_variables = dict(self.variables)  # Start with global variables
        
        # Add agent-type specific variables if available
        if agent_type and agent_type in DEFAULT_VARIABLES:
            format_variables.update(DEFAULT_VARIABLES[agent_type])
            
        # Add extra variables if provided
        if extra_variables:
            format_variables.update(extra_variables)
            
        # Format the prompt
        formatted_prompt = self.formatter.format_prompt(
            prompt_content=prompt_content,
            variables=format_variables,
            tool_names=tool_names
        )
        
        return formatted_prompt
        
    def get_variables(self, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Get variables available for prompt formatting.
        
        Args:
            agent_type: Optional agent type to include type-specific variables
            
        Returns:
            Dictionary of variables
        """
        # Start with global variables
        result = dict(self.variables)
        
        # Add agent-type specific variables if available
        if agent_type:
            if agent_type in DEFAULT_VARIABLES:
                result.update(DEFAULT_VARIABLES[agent_type])
                
            # Add registered variables for this agent type
            if agent_type in self.variables:
                result.update(self.variables[agent_type])
                
        return result