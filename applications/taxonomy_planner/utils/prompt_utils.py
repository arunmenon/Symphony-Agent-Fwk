"""Generic prompt template loading and formatting utilities.

This module provides a clean abstraction for loading and formatting prompt templates
from external files, without hardcoded knowledge of folder structures or template content.
"""

import os
import logging
import re
from string import Template
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

class PromptLoader:
    """Generic loader for prompt templates.
    
    This class provides utilities for loading prompt templates from files
    and formatting them with variables, without hardcoding template content.
    """
    
    # Singleton instance for application-wide access
    _instance = None
    
    @classmethod
    def get_instance(cls, template_dirs=None):
        """Get the singleton instance, optionally configuring it.
        
        Args:
            template_dirs: Optional template directories to set if the instance
                          hasn't been created yet
                          
        Returns:
            Singleton PromptLoader instance
        """
        if cls._instance is None:
            cls._instance = PromptLoader(template_dirs=template_dirs)
        return cls._instance
    
    def __init__(self, template_dirs: Optional[Union[str, List[str]]] = None, default_extension: str = ".txt"):
        """Initialize a PromptLoader.
        
        Args:
            template_dirs: Directory or list of directories to search for templates.
                           If None, no directories are pre-configured.
            default_extension: Default file extension for templates
        """
        self.template_dirs = []
        if template_dirs:
            if isinstance(template_dirs, str):
                self.template_dirs = [template_dirs]
            else:
                self.template_dirs = template_dirs
                
        self.default_extension = default_extension
        self.template_cache = {}  # Cache to avoid reloading templates
        self._template_vars_cache = {}  # Cache for template variables
        
    def add_template_dir(self, template_dir: str) -> None:
        """Add a directory to search for templates.
        
        Args:
            template_dir: Directory path to add
        """
        if os.path.exists(template_dir) and template_dir not in self.template_dirs:
            self.template_dirs.append(template_dir)
            # Clear cache when adding new directories
            self.template_cache = {}
            self._template_vars_cache = {}
        else:
            logger.warning(f"Template directory does not exist: {template_dir}")
            
    def find_template_file(self, template_name: str) -> Optional[str]:
        """Find a template file by name.
        
        Args:
            template_name: Name of template to find
            
        Returns:
            Full path to template file or None if not found
        """
        # First check if the template_name is already a full path
        if os.path.exists(template_name):
            return template_name
            
        # Check if we need to add default extension
        filename = template_name
        if not any(template_name.endswith(ext) for ext in ['.txt', '.md', '.yaml', '.yml', '.j2']):
            filename = f"{template_name}{self.default_extension}"
            
        # Search in configured directories
        for directory in self.template_dirs:
            path = os.path.join(directory, filename)
            if os.path.exists(path):
                return path
                
        return None
        
    def load_template(self, template_name: str) -> Optional[str]:
        """Load a template by name.
        
        Args:
            template_name: Name or path of template to load
            
        Returns:
            Template content or None if not found
        """
        # Check cache first
        if template_name in self.template_cache:
            return self.template_cache[template_name]
            
        # Find file
        template_path = self.find_template_file(template_name)
        if not template_path:
            logger.warning(f"Template not found: {template_name}")
            return None
            
        # Load template
        try:
            with open(template_path, 'r') as f:
                content = f.read().strip()
                self.template_cache[template_name] = content
                return content
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {e}")
            return None
            
    def format_template(self, template_name: str, **variables) -> Optional[str]:
        """Load and format a template with variables.
        
        Args:
            template_name: Name or path of template to load and format
            **variables: Variables to substitute in the template
            
        Returns:
            Formatted template or None if template not found
        """
        template_content = self.load_template(template_name)
        if not template_content:
            return None
            
        return self.format_template_string(template_content, **variables)
        
    def format_template_string(self, template_content: str, **variables) -> str:
        """Format a template string with variables.
        
        Supports both ${var} syntax (for string.Template) and
        {{var}} syntax (Handlebars-style) by converting the latter.
        
        Args:
            template_content: Template content string
            **variables: Variables to substitute
            
        Returns:
            Formatted template string
        """
        # Convert {{var}} syntax to ${var} syntax if needed
        if '{{' in template_content and '}}' in template_content:
            template_content = template_content.replace('{{', '${').replace('}}', '}')
            
        # Use string.Template for variable substitution
        template = Template(template_content)
        try:
            return template.substitute(**variables)
        except KeyError as e:
            # Fallback to safe_substitute which doesn't raise on missing keys
            result = template.safe_substitute(**variables)
            logger.warning(f"Missing variable in template: {e}. Using safe_substitute.")
            return result
            
    def get_template_variables(self, template_name: str) -> List[str]:
        """Extract variable names required by a template.
        
        Args:
            template_name: Name or path of template
            
        Returns:
            List of variable names required by the template
        """
        # Check cache first
        if template_name in self._template_vars_cache:
            return self._template_vars_cache[template_name]
            
        template_content = self.load_template(template_name)
        if not template_content:
            return []
            
        variables = self._extract_variables(template_content)
        self._template_vars_cache[template_name] = variables
        return variables
        
    def _extract_variables(self, template_content: str) -> List[str]:
        """Extract variable names from a template string.
        
        Args:
            template_content: Template content string
            
        Returns:
            List of variable names
        """
        # Handle both ${var} and {{var}} syntax
        patterns = [
            r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}',  # ${var} syntax
            r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}'  # {{var}} syntax
        ]
        
        variables = set()
        for pattern in patterns:
            matches = re.findall(pattern, template_content)
            variables.update(matches)
            
        return sorted(list(variables))
        
    def validate_variables(self, template_name: str, variables: Dict[str, Any]) -> List[str]:
        """Validate that all variables required by a template are provided.
        
        Args:
            template_name: Name or path of template
            variables: Dictionary of variables to validate
            
        Returns:
            List of missing variable names (empty if all are provided)
        """
        required_vars = self.get_template_variables(template_name)
        missing_vars = [var for var in required_vars if var not in variables]
        return missing_vars


def get_app_template_loader() -> PromptLoader:
    """Get application-wide template loader.
    
    This function configures a PromptLoader for the Taxonomy Planner application.
    
    Returns:
        A PromptLoader configured for this application
    """
    # Get path to task-prompts directory
    current_dir = os.path.dirname(os.path.dirname(__file__))
    task_prompts_dir = os.path.join(current_dir, "task-prompts")
    
    # Get or create the singleton instance
    loader = PromptLoader.get_instance(template_dirs=[task_prompts_dir])
    return loader