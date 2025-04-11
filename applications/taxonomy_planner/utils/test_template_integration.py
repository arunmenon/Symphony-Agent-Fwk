"""Integration test for template loading in Taxonomy Planner."""

import os
import logging
import unittest
from unittest.mock import patch

from utils.prompt_utils import get_app_template_loader, PromptLoader

class TestTemplateIntegration(unittest.TestCase):
    """Integration tests for template loading."""
    
    def setUp(self):
        """Set up test environment."""
        # Configure root logging
        logging.basicConfig(level=logging.INFO)
        
        # Get the application template loader
        self.loader = get_app_template_loader()
        
        # Get app root directory for file paths
        self.app_root = os.path.dirname(os.path.dirname(__file__))
        self.template_dir = os.path.join(self.app_root, "task-prompts")
        
    def test_all_required_templates_exist(self):
        """Test that all required templates exist."""
        required_templates = [
            "planning",
            "exploration",
            "compliance",
            "legal",
            "enhanced-metadata",
            "compliance-areas",
            "planning-agent",
            "explorer-agent"
        ]
        
        for template_name in required_templates:
            template_path = os.path.join(self.template_dir, f"{template_name}.txt")
            self.assertTrue(
                os.path.exists(template_path),
                f"Required template {template_name}.txt does not exist"
            )
            
    def test_all_templates_load_correctly(self):
        """Test that all templates load correctly."""
        templates = [
            "planning",
            "exploration",
            "compliance",
            "legal",
            "enhanced-metadata",
            "compliance-areas",
            "planning-agent",
            "explorer-agent"
        ]
        
        for template_name in templates:
            content = self.loader.load_template(template_name)
            self.assertIsNotNone(
                content,
                f"Failed to load template {template_name}"
            )
            self.assertGreater(
                len(content), 10,
                f"Template {template_name} content is too short"
            )
            
    def test_planning_agent_template_formatting(self):
        """Test formatting the planning agent template."""
        formatted = self.loader.format_template(
            "planning-agent",
            category="Weapons",
            enhanced_fields="description, risk_level",
            jurisdictions="USA, EU"
        )
        
        self.assertIn("Weapons", formatted)
        self.assertIn("description, risk_level", formatted)
        self.assertIn("USA, EU", formatted)
        
    def test_explorer_agent_template_formatting(self):
        """Test formatting the explorer agent template."""
        formatted = self.loader.format_template(
            "explorer-agent",
            category="Weapons",
            enhanced_fields="description, risk_level",
            jurisdictions="USA, EU"
        )
        
        self.assertIn("Weapons", formatted)
        self.assertIn("description, risk_level", formatted)
        self.assertIn("USA, EU", formatted)
        
    def test_compliance_areas_template_formatting(self):
        """Test formatting the compliance areas template."""
        formatted = self.loader.format_template(
            "compliance-areas",
            category="Weapons",
            simplified_taxonomy="- Firearms\n  - Handguns\n  - Rifles"
        )
        
        self.assertIn("Weapons", formatted)
        self.assertIn("- Firearms\n  - Handguns\n  - Rifles", formatted)
        
    def test_enhanced_metadata_template_formatting(self):
        """Test formatting the enhanced metadata template."""
        formatted = self.loader.format_template(
            "enhanced-metadata",
            category="Firearms"
        )
        
        self.assertIn("Firearms", formatted)
        self.assertIn("description", formatted.lower())
        self.assertIn("risk level", formatted.lower())


if __name__ == "__main__":
    unittest.main()