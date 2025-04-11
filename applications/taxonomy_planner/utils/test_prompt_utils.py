"""Tests for the PromptLoader utility."""

import os
import tempfile
import unittest
from unittest.mock import patch, mock_open

from prompt_utils import PromptLoader, get_app_template_loader

class TestPromptLoader(unittest.TestCase):
    """Test suite for PromptLoader class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test templates
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test template file
        self.template_content = "Hello, ${name}! Welcome to ${application}."
        self.template_path = os.path.join(self.temp_dir, "greeting.txt")
        with open(self.template_path, "w") as f:
            f.write(self.template_content)
            
        # Create a handlebars-style template
        self.hbs_template = "Hello, {{name}}! Welcome to {{application}}."
        self.hbs_path = os.path.join(self.temp_dir, "handlebars.txt")
        with open(self.hbs_path, "w") as f:
            f.write(self.hbs_template)
        
        # Create loader instance
        self.loader = PromptLoader(template_dirs=[self.temp_dir])
        
    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory and files
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)
        
        # Reset singleton instance to avoid affecting other tests
        PromptLoader._instance = None
        
    def test_load_template(self):
        """Test loading a template file."""
        content = self.loader.load_template("greeting")
        self.assertEqual(content, self.template_content)
        
    def test_format_template(self):
        """Test formatting a template with variables."""
        formatted = self.loader.format_template(
            "greeting", 
            name="John", 
            application="Testing"
        )
        self.assertEqual(formatted, "Hello, John! Welcome to Testing.")
        
    def test_format_handlebars_template(self):
        """Test formatting a template with handlebars-style variables."""
        formatted = self.loader.format_template(
            "handlebars", 
            name="John", 
            application="Testing"
        )
        self.assertEqual(formatted, "Hello, John! Welcome to Testing.")
        
    def test_format_template_string(self):
        """Test formatting a template string directly."""
        template = "The ${item} costs $${price}."
        formatted = self.loader.format_template_string(
            template,
            item="book",
            price="19.99"
        )
        self.assertEqual(formatted, "The book costs $19.99.")
        
    def test_format_with_missing_variable(self):
        """Test formatting with a missing variable."""
        with self.assertLogs(level='WARNING'):
            formatted = self.loader.format_template(
                "greeting", 
                name="John"
                # Missing 'application'
            )
        # Should use safe_substitute which keeps the placeholder
        self.assertEqual(formatted, "Hello, John! Welcome to ${application}.")
        
    def test_get_template_variables(self):
        """Test extracting variable names from a template."""
        variables = self.loader.get_template_variables("greeting")
        self.assertEqual(sorted(variables), ["application", "name"])
        
    def test_validate_variables(self):
        """Test validating variables against a template."""
        # All variables present
        missing = self.loader.validate_variables(
            "greeting",
            {"name": "John", "application": "Testing"}
        )
        self.assertEqual(missing, [])
        
        # Missing variable
        missing = self.loader.validate_variables(
            "greeting",
            {"name": "John"}
        )
        self.assertEqual(missing, ["application"])
        
    def test_add_template_dir(self):
        """Test adding a new template directory."""
        # Create another temporary directory
        new_dir = tempfile.mkdtemp()
        try:
            # Add the new directory
            self.loader.add_template_dir(new_dir)
            self.assertIn(new_dir, self.loader.template_dirs)
            
            # Create a template in the new directory
            new_template = "This is a new template for ${purpose}."
            new_path = os.path.join(new_dir, "new.txt")
            with open(new_path, "w") as f:
                f.write(new_template)
                
            # Should be able to load from the new directory
            content = self.loader.load_template("new")
            self.assertEqual(content, new_template)
        finally:
            # Clean up
            if os.path.exists(new_path):
                os.remove(new_path)
            os.rmdir(new_dir)
            
    def test_singleton_instance(self):
        """Test the singleton instance pattern."""
        # Get singleton instance
        instance1 = PromptLoader.get_instance()
        
        # Get another instance - should be the same object
        instance2 = PromptLoader.get_instance()
        
        # Should be the same object
        self.assertIs(instance1, instance2)
        
    def test_app_template_loader(self):
        """Test the get_app_template_loader function."""
        # Mock the paths to avoid real file system dependencies
        with patch('os.path.dirname') as mock_dirname:
            mock_dirname.return_value = "/mock"
            
            # Test that it returns a properly configured loader
            loader = get_app_template_loader()
            self.assertIsInstance(loader, PromptLoader)
            self.assertIn("/mock/task-prompts", loader.template_dirs)
            
            # Call again - should return the same instance
            loader2 = get_app_template_loader()
            self.assertIs(loader, loader2)


if __name__ == "__main__":
    unittest.main()