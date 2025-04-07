"""Prompt registry and management system."""

import os
from datetime import datetime
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field

from symphony.prompts.templates import DEFAULT_PROMPTS, MEMORY_PROMPTS


class PromptTemplate(BaseModel):
    """A template for a prompt."""
    
    content: str
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PromptRegistry:
    """Registry for prompts with hierarchical overrides."""
    
    def __init__(self, registry_path: Optional[str] = None):
        self.registry_path = registry_path
        self.registry: Dict[str, Dict[str, Dict[str, PromptTemplate]]] = {
            "global": {},
            "agent_types": {},
            "agent_instances": {}
        }
        self.cache: Dict[str, PromptTemplate] = {}
        
        # Register built-in prompts
        self._register_default_prompts()
        
        if registry_path and os.path.exists(registry_path):
            self.load()
            
    def _register_default_prompts(self) -> None:
        """Register the default prompts from templates."""
        # Register agent system prompts
        for agent_type, content in DEFAULT_PROMPTS.items():
            self.register_prompt(
                prompt_type="system",
                content=content,
                agent_type=agent_type,
                metadata={"built_in": True}
            )
            
        # Register memory-related prompts
        for prompt_type, content in MEMORY_PROMPTS.items():
            self.register_prompt(
                prompt_type=f"memory.{prompt_type}",
                content=content,
                metadata={"built_in": True, "category": "memory"}
            )
    
    def load(self) -> None:
        """Load prompts from registry file."""
        if not self.registry_path:
            return
            
        try:
            with open(self.registry_path, "r") as f:
                data = yaml.safe_load(f) or {}
                
            # Convert raw data to PromptTemplates
            for level, prompts in data.items():
                if level not in self.registry:
                    continue
                    
                if not prompts:
                    continue
                    
                for name, prompt_types in prompts.items():
                    if not isinstance(prompt_types, dict):
                        continue
                        
                    for prompt_type, content in prompt_types.items():
                        if isinstance(content, dict):
                            # Handle complex prompt format with version, metadata, etc.
                            self.registry[level].setdefault(name, {})[prompt_type] = PromptTemplate(**content)
                        else:
                            # Handle simple string content
                            self.registry[level].setdefault(name, {})[prompt_type] = PromptTemplate(content=content)
                            
            # Clear cache after loading
            self.cache = {}
        except Exception as e:
            print(f"Error loading prompt registry: {e}")
    
    def save(self) -> None:
        """Save prompts to registry file."""
        if not self.registry_path:
            return
            
        # Convert PromptTemplates to serializable format
        output = {}
        for level, names in self.registry.items():
            output[level] = {}
            for name, prompt_types in names.items():
                output[level][name] = {}
                for prompt_type, template in prompt_types.items():
                    output[level][name][prompt_type] = template.model_dump()
        
        try:
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            with open(self.registry_path, "w") as f:
                yaml.dump(output, f)
        except Exception as e:
            print(f"Error saving prompt registry: {e}")
    
    def get_prompt(
        self, 
        prompt_type: str,
        agent_type: Optional[str] = None,
        agent_instance: Optional[str] = None
    ) -> Optional[PromptTemplate]:
        """Get a prompt from the registry, respecting hierarchical overrides."""
        # Check cache first
        cache_key = f"{agent_instance or ''}:{agent_type or ''}:{prompt_type}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Check for instance-specific prompt
        if agent_instance and agent_instance in self.registry["agent_instances"]:
            instance_prompts = self.registry["agent_instances"][agent_instance]
            if prompt_type in instance_prompts:
                self.cache[cache_key] = instance_prompts[prompt_type]
                return instance_prompts[prompt_type]
        
        # Check for type-specific prompt
        if agent_type and agent_type in self.registry["agent_types"]:
            type_prompts = self.registry["agent_types"][agent_type]
            if prompt_type in type_prompts:
                self.cache[cache_key] = type_prompts[prompt_type]
                return type_prompts[prompt_type]
        
        # Fall back to global prompt
        global_prompts = self.registry["global"]
        if prompt_type in global_prompts:
            self.cache[cache_key] = global_prompts[prompt_type]
            return global_prompts[prompt_type]
        
        return None
    
    def register_prompt(
        self,
        prompt_type: str,
        content: str,
        agent_type: Optional[str] = None,
        agent_instance: Optional[str] = None,
        version: str = "1.0",
        metadata: Optional[Dict[str, Any]] = None
    ) -> PromptTemplate:
        """Register a new prompt or update an existing one."""
        prompt = PromptTemplate(
            content=content,
            version=version,
            metadata=metadata or {}
        )
        
        if agent_instance:
            self.registry["agent_instances"].setdefault(agent_instance, {})[prompt_type] = prompt
        elif agent_type:
            self.registry["agent_types"].setdefault(agent_type, {})[prompt_type] = prompt
        else:
            self.registry["global"][prompt_type] = prompt
        
        # Clear relevant cache entries
        cache_keys = [k for k in self.cache if k.endswith(f":{prompt_type}")]
        for key in cache_keys:
            self.cache.pop(key, None)
            
        return prompt
    
    def __str__(self) -> str:
        """String representation for debugging."""
        counts = {
            "global": len(self.registry["global"]),
            "agent_types": sum(len(prompts) for prompts in self.registry["agent_types"].values()),
            "agent_instances": sum(len(prompts) for prompts in self.registry["agent_instances"].values())
        }
        return f"PromptRegistry(global={counts['global']}, types={counts['agent_types']}, instances={counts['agent_instances']})"