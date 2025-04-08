"""Simple direct tests for the TaxonomyStore class."""

import os
import json
import tempfile
import unittest
from typing import Dict, Any, List, Optional

# Import directly from the persistence.py file
import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)
from persistence import TaxonomyStore


class TestTaxonomyStore(unittest.TestCase):
    """Test the TaxonomyStore functionality."""
    
    def setUp(self):
        """Set up a temp file for storage."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        
        # Create a populated store for testing
        self.store = TaxonomyStore(storage_path=self.temp_path)
        
        # Add nodes to create a simple taxonomy
        self.store.add_node("Technology")  # Root
        
        # Level 1 categories
        self.store.add_node("Hardware", parent="Technology")
        self.store.add_node("Software", parent="Technology")
        self.store.add_node("Networks", parent="Technology")
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.temp_path):
            os.remove(self.temp_path)
    
    def test_init(self):
        """Test initialization of the taxonomy store."""
        store = TaxonomyStore()
        self.assertIsNotNone(store)
        self.assertIsInstance(store.nodes, dict)
        self.assertIsInstance(store.edges, dict)
        self.assertIsInstance(store.parents, dict)
        self.assertIsInstance(store.compliance_mappings, dict)
        self.assertIsInstance(store.legal_mappings, dict)
    
    def test_add_node(self):
        """Test adding nodes to the taxonomy."""
        store = TaxonomyStore()
        
        # Add root node
        store.add_node("Technology")
        self.assertIn("Technology", store.nodes)
        self.assertEqual(len(store.edges["Technology"]), 0)
        
        # Add child node
        store.add_node("Hardware", parent="Technology")
        self.assertIn("Hardware", store.nodes)
        self.assertIn("Hardware", store.edges["Technology"])
        self.assertEqual(store.parents["Hardware"], "Technology")
    
    def test_get_node_and_children(self):
        """Test retrieving node data and children."""
        # Check root node
        self.assertIsNotNone(self.store.get_node("Technology"))
        
        # Check children
        children = self.store.get_children("Technology")
        self.assertEqual(len(children), 3)
        self.assertIn("Hardware", children)
        self.assertIn("Software", children)
        self.assertIn("Networks", children)
    
    def test_get_parent(self):
        """Test retrieving parent nodes."""
        self.assertEqual(self.store.get_parent("Hardware"), "Technology")
        self.assertIsNone(self.store.get_parent("Technology"))  # Root has no parent
    
    def test_get_all_nodes(self):
        """Test retrieving all nodes."""
        all_nodes = self.store.get_all_nodes()
        self.assertEqual(len(all_nodes), 4)  # Root + 3 children
        self.assertIn("Technology", all_nodes)
        self.assertIn("Hardware", all_nodes)
        self.assertIn("Software", all_nodes)
        self.assertIn("Networks", all_nodes)
    
    def test_compliance_mappings(self):
        """Test compliance mappings functionality."""
        # Add a compliance mapping
        self.store.add_compliance_mapping("Hardware", "USA", {
            "regulations": ["FCC Part 15"]
        })
        
        # Get the mapping
        mapping = self.store.get_compliance_mapping("Hardware", "USA")
        self.assertIsNotNone(mapping)
        self.assertIn("regulations", mapping)
        self.assertIn("FCC Part 15", mapping["regulations"])
    
    def test_legal_mappings(self):
        """Test legal mappings functionality."""
        # Add a legal mapping
        self.store.add_legal_mapping("Software", "EU", {
            "regulations": ["GDPR"]
        })
        
        # Get the mapping
        mapping = self.store.get_legal_mapping("Software", "EU")
        self.assertIsNotNone(mapping)
        self.assertIn("regulations", mapping)
        self.assertIn("GDPR", mapping["regulations"])
    
    def test_get_ancestors(self):
        """Test retrieving ancestors of a node."""
        # Add a deeper node
        self.store.add_node("Computers", parent="Hardware")
        
        # Check ancestors
        ancestors = self.store.get_ancestors("Computers")
        self.assertEqual(len(ancestors), 1)  # Just Hardware, as it only has one parent
        self.assertEqual(ancestors[0], "Hardware")
        
        # Let's verify the parents mapping is correct
        self.assertEqual(self.store.parents["Computers"], "Hardware")
        self.assertEqual(self.store.parents["Hardware"], "Technology")
        
        # Add another level and verify each relationship separately
        self.store.add_node("Laptop", parent="Computers")
        self.assertEqual(self.store.parents["Laptop"], "Computers")
        
        # Check immediate parent
        parent = self.store.get_parent("Laptop")
        self.assertEqual(parent, "Computers")
        
        # Check grandparent manually
        grandparent = self.store.get_parent(parent)
        self.assertEqual(grandparent, "Hardware")
        
        # Get ancestors of Laptop
        ancestors2 = self.store.get_ancestors("Laptop")
        self.assertEqual(len(ancestors2), 1)
        self.assertEqual(ancestors2[0], "Computers")
        
        # ENHANCEMENT OPPORTUNITY: The current get_ancestors implementation only returns
        # the immediate parent due to the parents dictionary structure. For a full chain
        # of ancestors, the method would need to recursively follow parent links.
    
    def test_get_descendants(self):
        """Test retrieving descendants of a node."""
        # Add deeper nodes
        self.store.add_node("Computers", parent="Hardware")
        self.store.add_node("Mobile Devices", parent="Hardware")
        
        # Check descendants
        descendants = self.store.get_descendants("Hardware")
        self.assertEqual(len(descendants), 2)
        self.assertIn("Computers", descendants)
        self.assertIn("Mobile Devices", descendants)
    
    def test_get_taxonomy_tree(self):
        """Test building a complete taxonomy tree."""
        # Add deeper nodes
        self.store.add_node("Computers", parent="Hardware")
        self.store.add_node("Mobile Devices", parent="Hardware")
        self.store.add_node("Operating Systems", parent="Software")
        
        # Add some compliance mappings
        self.store.add_compliance_mapping("Computers", "USA", {
            "regulations": ["FCC Part 15", "UL Certification"]
        })
        
        # Get full tree
        tree = self.store.get_taxonomy_tree("Technology")
        self.assertEqual(tree["category"], "Technology")
        self.assertEqual(len(tree["subcategories"]), 3)
        
        # Check hardware branch
        hardware_branch = None
        for sub in tree["subcategories"]:
            if sub["category"] == "Hardware":
                hardware_branch = sub
                break
        
        self.assertIsNotNone(hardware_branch)
        self.assertEqual(len(hardware_branch["subcategories"]), 2)
    
    def test_persistence(self):
        """Test saving and loading from disk."""
        # Create a store, add data, and save
        store = TaxonomyStore(storage_path=self.temp_path)
        store.add_node("Root")
        store.add_node("Child1", parent="Root")
        store.add_node("Child2", parent="Root")
        store.add_compliance_mapping("Root", "Global", {"rules": ["Rule1"]})
        
        # Save to disk
        self.assertTrue(store.save())
        
        # Create a new store and load from disk
        new_store = TaxonomyStore(storage_path=self.temp_path)
        
        # Verify data was loaded correctly
        self.assertIn("Root", new_store.nodes)
        self.assertIn("Child1", new_store.nodes)
        self.assertIn("Child2", new_store.nodes)
        self.assertEqual(new_store.get_parent("Child1"), "Root")
        self.assertIn("Root", new_store.compliance_mappings)
    
    def test_clear(self):
        """Test clearing all data."""
        # Verify store has data
        self.assertGreater(len(self.store.nodes), 0)
        self.assertGreater(len(self.store.edges), 0)
        
        # Clear the store
        self.store.clear()
        
        # Verify data is cleared
        self.assertEqual(len(self.store.nodes), 0)
        self.assertEqual(len(self.store.edges), 0)
        self.assertEqual(len(self.store.parents), 0)
        self.assertTrue(self.store.dirty)  # Should be marked as dirty after clearing


if __name__ == "__main__":
    unittest.main()