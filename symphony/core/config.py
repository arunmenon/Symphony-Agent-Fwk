"""Configuration management for Symphony."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import yaml
from pydantic import BaseModel, Field, model_validator

from symphony.core.exceptions import ConfigurationError


class SymphonyConfig(BaseModel):
    """Main configuration for Symphony."""
    
    # Basic configuration
    application_name: str = "Symphony Application"
    debug: bool = False
    log_level: str = "INFO"
    
    # Directory paths
    base_dir: Optional[str] = None
    data_dir: Optional[str] = None
    prompt_dir: Optional[str] = None
    
    # MCP configuration
    mcp_enabled: bool = True
    mcp_app_name: Optional[str] = None
    mcp_resource_prefix: str = "symphony"
    
    # LLM configuration
    llm_provider: str = "mock"
    llm_model: str = "default"
    llm_api_key: Optional[str] = None
    llm_api_base: Optional[str] = None
    llm_max_tokens: int = 1000
    llm_temperature: float = 0.7
    llm_timeout: Optional[int] = None
    
    # Agent configuration
    default_agent_type: str = "reactive"
    
    # Memory configuration
    default_memory_type: str = "conversation"
    
    # Extra parameters that don't fit elsewhere
    extra: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def setup_directories(self) -> 'SymphonyConfig':
        """Set up directory paths if not explicitly provided."""
        if self.base_dir is None:
            self.base_dir = str(Path.cwd())
            
        if self.data_dir is None:
            self.data_dir = str(Path(self.base_dir) / "data")
            
        if self.prompt_dir is None:
            self.prompt_dir = str(Path(self.base_dir) / "prompts")
            
        if self.mcp_app_name is None:
            self.mcp_app_name = self.application_name
            
        return self
    
    def get_env_variable(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable."""
        return os.environ.get(name, default)
    
    def get_llm_api_key(self) -> Optional[str]:
        """Get the LLM API key, checking environment variables."""
        if self.llm_api_key:
            return self.llm_api_key
            
        env_var_name = f"{self.llm_provider.upper()}_API_KEY"
        return self.get_env_variable(env_var_name)
    
    def get_extra(self, key: str, default: Any = None) -> Any:
        """Get a value from the extra parameters."""
        return self.extra.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary."""
        return self.model_dump()
    
    def to_yaml(self, path: str) -> None:
        """Save configuration to a YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f)


class ConfigLoader:
    """Load configuration from various sources."""
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> SymphonyConfig:
        """Create a configuration from a dictionary."""
        return SymphonyConfig(**config_dict)
    
    @classmethod
    def from_yaml(cls, path: str) -> SymphonyConfig:
        """Load configuration from a YAML file."""
        try:
            with open(path, "r") as f:
                config_dict = yaml.safe_load(f) or {}
                return cls.from_dict(config_dict)
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration from {path}: {str(e)}")
    
    @classmethod
    def from_env(cls, prefix: str = "SYMPHONY_") -> SymphonyConfig:
        """Load configuration from environment variables.
        
        Environment variables should be prefixed with the given prefix.
        For example, SYMPHONY_LOG_LEVEL maps to log_level.
        """
        config_dict: Dict[str, Any] = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix):].lower()
                
                # Handle boolean values
                if value.lower() in ("true", "yes", "1", "on"):
                    config_dict[config_key] = True
                elif value.lower() in ("false", "no", "0", "off"):
                    config_dict[config_key] = False
                # Handle integer values
                elif value.isdigit():
                    config_dict[config_key] = int(value)
                # Handle float values
                elif value.replace(".", "", 1).isdigit() and value.count(".") == 1:
                    config_dict[config_key] = float(value)
                else:
                    config_dict[config_key] = value
                    
        return cls.from_dict(config_dict)
    
    @classmethod
    def load(
        cls, 
        yaml_path: Optional[str] = None,
        env_prefix: str = "SYMPHONY_",
        defaults: Optional[Dict[str, Any]] = None
    ) -> SymphonyConfig:
        """Load configuration from multiple sources.
        
        Priority (highest to lowest):
        1. Environment variables
        2. YAML file
        3. Default values
        """
        # Start with defaults
        config_dict = defaults or {}
        
        # Load from YAML file if provided
        if yaml_path:
            try:
                yaml_config = cls.from_yaml(yaml_path)
                config_dict.update(yaml_config.to_dict())
            except Exception as e:
                # Log but continue with defaults
                print(f"Warning: Could not load config from {yaml_path}: {str(e)}")
        
        # Load from environment variables
        env_config = cls.from_env(prefix=env_prefix)
        config_dict.update({k: v for k, v in env_config.to_dict().items() if v is not None})
        
        return cls.from_dict(config_dict)