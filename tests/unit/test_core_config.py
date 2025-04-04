"""Unit tests for the Symphony configuration system."""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from symphony.core.config import SymphonyConfig, ConfigLoader
from symphony.core.exceptions import ConfigurationError


class TestSymphonyConfig:
    """Test suite for SymphonyConfig class."""
    
    def test_default_config(self):
        """Test the default configuration values."""
        config = SymphonyConfig()
        
        assert config.application_name == "Symphony Application"
        assert config.debug is False
        assert config.log_level == "INFO"
        assert config.llm_provider == "mock"
        assert config.llm_model == "default"
        assert config.mcp_enabled is True
        assert config.base_dir == str(Path.cwd())
        assert config.data_dir == str(Path.cwd() / "data")
        assert config.prompt_dir == str(Path.cwd() / "prompts")
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = SymphonyConfig(
            application_name="Test App",
            debug=True,
            log_level="DEBUG",
            llm_provider="openai",
            llm_model="gpt-4",
            llm_api_key="test-key",
            base_dir="/custom/path",
            data_dir="/custom/data",
            prompt_dir="/custom/prompts"
        )
        
        assert config.application_name == "Test App"
        assert config.debug is True
        assert config.log_level == "DEBUG"
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert config.llm_api_key == "test-key"
        assert config.base_dir == "/custom/path"
        assert config.data_dir == "/custom/data"
        assert config.prompt_dir == "/custom/prompts"
    
    def test_directories_setup(self):
        """Test that directories are set up correctly."""
        config = SymphonyConfig(base_dir="/test/base")
        
        assert config.base_dir == "/test/base"
        assert config.data_dir == "/test/base/data"
        assert config.prompt_dir == "/test/base/prompts"
    
    def test_get_env_variable(self):
        """Test getting environment variables."""
        config = SymphonyConfig()
        
        # Set a test environment variable
        os.environ["TEST_VAR"] = "test_value"
        
        assert config.get_env_variable("TEST_VAR") == "test_value"
        assert config.get_env_variable("NONEXISTENT_VAR") is None
        assert config.get_env_variable("NONEXISTENT_VAR", "default") == "default"
        
        # Clean up
        del os.environ["TEST_VAR"]
    
    def test_get_llm_api_key(self):
        """Test getting the LLM API key."""
        # Test with explicit key
        config = SymphonyConfig(llm_provider="openai", llm_api_key="explicit-key")
        assert config.get_llm_api_key() == "explicit-key"
        
        # Test with environment variable
        config = SymphonyConfig(llm_provider="openai", llm_api_key=None)
        os.environ["OPENAI_API_KEY"] = "env-key"
        
        assert config.get_llm_api_key() == "env-key"
        
        # Clean up
        del os.environ["OPENAI_API_KEY"]
    
    def test_extra_params(self):
        """Test extra parameters."""
        config = SymphonyConfig(extra={"custom_param": "value"})
        
        assert config.get_extra("custom_param") == "value"
        assert config.get_extra("nonexistent") is None
        assert config.get_extra("nonexistent", "default") == "default"
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        config = SymphonyConfig(application_name="Test App")
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["application_name"] == "Test App"
    
    def test_to_yaml(self):
        """Test saving to YAML."""
        config = SymphonyConfig(application_name="Test App")
        
        # Use a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_path = temp.name
        
        try:
            # Write to the temp file
            with patch("builtins.open", mock_open()) as mock_file:
                config.to_yaml(temp_path)
                
                # Check that file was opened for writing
                mock_file.assert_called_once_with(temp_path, "w")
                
                # Check that yaml.dump was called with the config dict
                # (indirectly by checking if write was called)
                mock_file().write.assert_called()
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestConfigLoader:
    """Test suite for ConfigLoader class."""
    
    def test_from_dict(self):
        """Test loading from a dictionary."""
        config_dict = {
            "application_name": "Dict App",
            "debug": True,
            "llm_provider": "anthropic"
        }
        
        config = ConfigLoader.from_dict(config_dict)
        
        assert config.application_name == "Dict App"
        assert config.debug is True
        assert config.llm_provider == "anthropic"
    
    def test_from_yaml(self):
        """Test loading from a YAML file."""
        yaml_content = """
        application_name: YAML App
        debug: true
        llm_provider: anthropic
        """
        
        # Create a temporary YAML file
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(yaml_content.encode())
            temp_path = temp.name
        
        try:
            # Load from the temp file
            config = ConfigLoader.from_yaml(temp_path)
            
            assert config.application_name == "YAML App"
            assert config.debug is True
            assert config.llm_provider == "anthropic"
        finally:
            # Clean up
            os.remove(temp_path)
    
    def test_from_yaml_error(self):
        """Test error handling when loading from YAML."""
        with pytest.raises(ConfigurationError):
            ConfigLoader.from_yaml("nonexistent_file.yaml")
    
    def test_from_env(self):
        """Test loading from environment variables."""
        # Set test environment variables
        os.environ["SYMPHONY_APPLICATION_NAME"] = "Env App"
        os.environ["SYMPHONY_DEBUG"] = "true"
        os.environ["SYMPHONY_LLM_MAX_TOKENS"] = "2000"
        os.environ["SYMPHONY_LLM_TEMPERATURE"] = "0.8"
        
        config = ConfigLoader.from_env()
        
        assert config.application_name == "Env App"
        assert config.debug is True
        assert config.llm_max_tokens == 2000
        assert config.llm_temperature == 0.8
        
        # Clean up
        del os.environ["SYMPHONY_APPLICATION_NAME"]
        del os.environ["SYMPHONY_DEBUG"]
        del os.environ["SYMPHONY_LLM_MAX_TOKENS"]
        del os.environ["SYMPHONY_LLM_TEMPERATURE"]
    
    def test_load_with_defaults(self):
        """Test loading with default values."""
        defaults = {
            "application_name": "Default App",
            "debug": False
        }
        
        config = ConfigLoader.load(defaults=defaults)
        
        assert config.application_name == "Default App"
        assert config.debug is False
    
    def test_load_precedence(self):
        """Test the precedence of different config sources."""
        # Set up different sources with different values for the same keys
        defaults = {
            "application_name": "Default App",
            "debug": False,
            "log_level": "INFO"
        }
        
        yaml_content = """
        application_name: YAML App
        debug: true
        """
        
        # Create a temporary YAML file
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(yaml_content.encode())
            temp_path = temp.name
        
        try:
            # Set environment variables
            os.environ["SYMPHONY_APPLICATION_NAME"] = "Env App"
            
            # Load config with all sources
            config = ConfigLoader.load(
                yaml_path=temp_path,
                defaults=defaults
            )
            
            # Environment variables should have highest precedence
            assert config.application_name == "Env App"
            # YAML should override defaults
            assert config.debug is True
            # Defaults should be used for fields not in other sources
            assert config.log_level == "INFO"
        finally:
            # Clean up
            os.remove(temp_path)
            del os.environ["SYMPHONY_APPLICATION_NAME"]