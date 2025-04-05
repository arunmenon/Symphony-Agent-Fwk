"""Prompt templates for Symphony patterns.

This module provides a registry for loading and managing pattern prompt templates.
Templates are stored in YAML files in the prompts directory structure.
"""

import os
import yaml
from typing import Dict, Any, Optional, List

# Constants
DEFAULT_VERSION = "default"
PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


class PromptTemplateRegistry:
    """Registry for pattern prompt templates.
    
    This class provides a central registry for loading, managing, and rendering
    prompt templates used by patterns. Templates are stored in YAML files
    with support for multiple versions.
    """
    
    def __init__(self, templates_dir: str = None):
        """Initialize prompt template registry.
        
        Args:
            templates_dir: Directory containing prompt templates (optional)
        """
        self.templates_dir = templates_dir or PROMPTS_DIR
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.loaded_categories: List[str] = []
        
    def load_templates(self, category: str = None):
        """Load templates from the filesystem.
        
        Args:
            category: Template category to load (optional, loads all if not specified)
        """
        if category:
            self._load_category(category)
        else:
            # Get all subdirectories in templates_dir
            for item in os.listdir(self.templates_dir):
                if os.path.isdir(os.path.join(self.templates_dir, item)) and not item.startswith('__'):
                    self._load_category(item)
    
    def _load_category(self, category: str):
        """Load templates for a specific category.
        
        Args:
            category: Template category to load
        """
        if category in self.loaded_categories:
            return
            
        category_dir = os.path.join(self.templates_dir, category)
        if not os.path.isdir(category_dir):
            return
            
        # Load all YAML files in category directory
        for filename in os.listdir(category_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                pattern_name = os.path.splitext(filename)[0]
                template_path = os.path.join(category_dir, filename)
                
                try:
                    with open(template_path, 'r') as f:
                        template_data = yaml.safe_load(f)
                        
                    # Store template by pattern name
                    template_key = f"{category}.{pattern_name}"
                    self.templates[template_key] = template_data
                except Exception as e:
                    print(f"Error loading template {template_path}: {e}")
        
        self.loaded_categories.append(category)
    
    def get_template(self, pattern_name: str, version: str = DEFAULT_VERSION) -> str:
        """Get template for a specific pattern and version.
        
        Args:
            pattern_name: Pattern name (with category prefix, e.g., "reasoning.chain_of_thought")
            version: Template version (default: "default")
            
        Returns:
            Template content
            
        Raises:
            ValueError: If template is not found
        """
        if pattern_name not in self.templates:
            # Try to load category if not done yet
            category = pattern_name.split('.')[0] if '.' in pattern_name else None
            if category:
                self._load_category(category)
                
            if pattern_name not in self.templates:
                raise ValueError(f"Template {pattern_name} not found")
        
        # Get template for version
        if version not in self.templates[pattern_name]:
            raise ValueError(f"Version {version} of template {pattern_name} not found")
            
        return self.templates[pattern_name][version]
    
    def render_template(self, pattern_name: str, variables: Dict[str, Any], version: str = DEFAULT_VERSION) -> str:
        """Render a template with variables.
        
        Args:
            pattern_name: Pattern name (with category prefix)
            variables: Variables to substitute in template
            version: Template version (default: "default")
            
        Returns:
            Rendered template
            
        Raises:
            ValueError: If template is not found
        """
        template = self.get_template(pattern_name, version)
        
        if isinstance(template, dict) and "content" in template:
            template = template["content"]
            
        # Apply variable substitution
        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", str(value))
            
        return template


# Global registry instance
_registry = None

def get_registry() -> PromptTemplateRegistry:
    """Get the global prompt template registry.
    
    Returns:
        Global prompt template registry
    """
    global _registry
    if _registry is None:
        _registry = PromptTemplateRegistry()
        _registry.load_templates()
    return _registry