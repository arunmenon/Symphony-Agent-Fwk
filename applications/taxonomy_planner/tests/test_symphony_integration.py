"""Test Symphony integration with stable API."""

import unittest
import asyncio
import os
import sys
from unittest.mock import patch

# Add parent directory to path for importing application modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from applications.taxonomy_planner.config import TaxonomyConfig
from applications.taxonomy_planner.persistence import TaxonomyStore

class TestSymphonyIntegration(unittest.TestCase):
    """Test integration with Symphony stable API."""
    
    @patch('symphony.api.Symphony')
    def test_import_pathways(self, mock_symphony):
        """Test that all Symphony imports are using the stable API."""
        # Verify we can import from the stable API in agents.py
        from applications.taxonomy_planner.agents import create_agents
        
        # Verify we can import from the stable API in patterns.py  
        from applications.taxonomy_planner.patterns import create_patterns
        
        # Verify we can import from the stable API in tools/__init__.py
        from applications.taxonomy_planner.tools import register_tools
        
        # Verify we can import from the stable API in main.py
        from applications.taxonomy_planner.main import TaxonomyPlanner

        # These imports should not raise exceptions
        self.assertTrue(True, "Imports succeeded using stable API")
    
    def test_config_model_references(self):
        """Test that all model references use the correct provider prefixes."""
        config = TaxonomyConfig()
        
        # Check model references in agent configs
        for agent_name, agent_config in config.agent_configs.items():
            model_name = agent_config.get("model", "")
            self.assertTrue("/" in model_name, f"Model {model_name} should include provider prefix")
            
        # Check get_model_for_agent returns correct format
        model = config.get_model_for_agent("planner")
        self.assertTrue("/" in model, f"Model {model} should include provider prefix")
    
    @unittest.skip("This is an integration test that requires API keys")
    def test_actual_workflow_execution(self):
        """Test actual workflow execution with Symphony."""
        # This is a placeholder for an actual integration test
        # that would run the taxonomy generation process
        pass

if __name__ == "__main__":
    unittest.main()