"""Tests for the TaxonomyStore class."""

import os
import json
import tempfile
import sys
import pytest
from typing import Dict, Any, List, Optional

# Add the parent directory to the path for imports
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the TaxonomyStore class
from applications.taxonomy_planner.persistence import TaxonomyStore


@pytest.fixture
def temp_storage_path():
    """Create a temporary file for storage testing."""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def populated_store(temp_storage_path):
    """Create a pre-populated taxonomy store for testing."""
    store = TaxonomyStore(storage_path=temp_storage_path)
    
    # Add nodes to create a simple taxonomy
    store.add_node("Technology")  # Root
    
    # Level 1 categories
    store.add_node("Hardware", parent="Technology")
    store.add_node("Software", parent="Technology")
    store.add_node("Networks", parent="Technology")
    
    # Level 2 categories
    store.add_node("Computers", parent="Hardware")
    store.add_node("Mobile Devices", parent="Hardware")
    store.add_node("Operating Systems", parent="Software")
    store.add_node("Applications", parent="Software")
    
    # Level 3 categories
    store.add_node("Laptops", parent="Computers")
    store.add_node("Desktops", parent="Computers")
    store.add_node("Smartphones", parent="Mobile Devices")
    store.add_node("Tablets", parent="Mobile Devices")
    
    # Add some compliance mappings
    store.add_compliance_mapping("Computers", "USA", {
        "regulations": ["FCC Part 15", "UL Certification"],
        "standards": ["ENERGY STAR"]
    })
    
    # Add some legal mappings
    store.add_legal_mapping("Software", "EU", {
        "regulations": ["GDPR", "EU Copyright Directive"],
        "licenses": ["Proprietary", "Open Source"]
    })
    
    return store


class TestTaxonomyStore:
    """Test the TaxonomyStore functionality."""
    
    def test_init(self):
        """Test initialization of the taxonomy store."""
        store = TaxonomyStore()
        assert store is not None
        assert isinstance(store.nodes, dict)
        assert isinstance(store.edges, dict)
        assert isinstance(store.parents, dict)
        assert isinstance(store.compliance_mappings, dict)
        assert isinstance(store.legal_mappings, dict)
    
    def test_add_node(self):
        """Test adding nodes to the taxonomy."""
        store = TaxonomyStore()
        
        # Add root node
        store.add_node("Technology")
        assert "Technology" in store.nodes
        assert len(store.edges["Technology"]) == 0
        
        # Add child node
        store.add_node("Hardware", parent="Technology")
        assert "Hardware" in store.nodes
        assert "Hardware" in store.edges["Technology"]
        assert store.parents["Hardware"] == "Technology"
        
        # Add node with metadata
        metadata = {"description": "Software includes applications, operating systems, etc."}
        store.add_node("Software", parent="Technology", metadata=metadata)
        assert "Software" in store.nodes
        assert store.nodes["Software"] == metadata
    
    def test_get_node_and_children(self, populated_store):
        """Test retrieving node data and children."""
        store = populated_store
        
        # Check root node
        assert store.get_node("Technology") is not None
        
        # Check children
        children = store.get_children("Technology")
        assert len(children) == 3
        assert "Hardware" in children
        assert "Software" in children
        assert "Networks" in children
        
        # Check nested children
        hw_children = store.get_children("Hardware")
        assert len(hw_children) == 2
        assert "Computers" in hw_children
        assert "Mobile Devices" in hw_children
    
    def test_get_parent(self, populated_store):
        """Test retrieving parent nodes."""
        store = populated_store
        
        assert store.get_parent("Hardware") == "Technology"
        assert store.get_parent("Computers") == "Hardware"
        assert store.get_parent("Laptops") == "Computers"
        assert store.get_parent("Technology") is None  # Root has no parent
    
    def test_get_all_nodes(self, populated_store):
        """Test retrieving all nodes."""
        store = populated_store
        
        all_nodes = store.get_all_nodes()
        assert len(all_nodes) == 13  # Total nodes in our test hierarchy
        
        # Check some specific nodes
        assert "Technology" in all_nodes
        assert "Hardware" in all_nodes
        assert "Software" in all_nodes
        assert "Laptops" in all_nodes
    
    def test_compliance_mappings(self, populated_store):
        """Test compliance mappings functionality."""
        store = populated_store
        
        # Get existing mapping
        mapping = store.get_compliance_mapping("Computers", "USA")
        assert mapping is not None
        assert "regulations" in mapping
        assert "FCC Part 15" in mapping["regulations"]
        
        # Add new mapping
        store.add_compliance_mapping("Smartphones", "EU", {
            "regulations": ["CE Mark", "RoHS Compliance"]
        })
        
        new_mapping = store.get_compliance_mapping("Smartphones", "EU")
        assert new_mapping is not None
        assert "CE Mark" in new_mapping["regulations"]
        
        # Get all mappings for a category
        all_mappings = store.get_compliance_mapping("Computers")
        assert "USA" in all_mappings
    
    def test_legal_mappings(self, populated_store):
        """Test legal mappings functionality."""
        store = populated_store
        
        # Get existing mapping
        mapping = store.get_legal_mapping("Software", "EU")
        assert mapping is not None
        assert "regulations" in mapping
        assert "GDPR" in mapping["regulations"]
        
        # Add new mapping
        store.add_legal_mapping("Applications", "USA", {
            "regulations": ["DMCA", "Software Licensing Laws"]
        })
        
        new_mapping = store.get_legal_mapping("Applications", "USA")
        assert new_mapping is not None
        assert "DMCA" in new_mapping["regulations"]
    
    def test_get_ancestors(self, populated_store):
        """Test retrieving ancestors of a node."""
        store = populated_store
        
        # Check ancestors of a leaf node
        ancestors = store.get_ancestors("Laptops")
        assert len(ancestors) == 3
        assert ancestors[0] == "Computers"
        assert ancestors[1] == "Hardware"
        assert ancestors[2] == "Technology"
        
        # Check ancestors of a middle node
        ancestors = store.get_ancestors("Computers")
        assert len(ancestors) == 2
        assert ancestors[0] == "Hardware"
        assert ancestors[1] == "Technology"
        
        # Root node has no ancestors
        ancestors = store.get_ancestors("Technology")
        assert len(ancestors) == 0
    
    def test_get_descendants(self, populated_store):
        """Test retrieving descendants of a node."""
        store = populated_store
        
        # Check descendants of root
        descendants = store.get_descendants("Technology")
        assert len(descendants) == 12  # All nodes except the root
        assert "Hardware" in descendants
        assert "Laptops" in descendants
        
        # Check descendants of a middle node
        descendants = store.get_descendants("Hardware")
        assert len(descendants) == 4
        assert "Computers" in descendants
        assert "Laptops" in descendants
        assert "Mobile Devices" in descendants
        assert "Smartphones" in descendants
        
        # Check descendants of a leaf node
        descendants = store.get_descendants("Laptops")
        assert len(descendants) == 0  # No descendants for leaf nodes
    
    def test_get_taxonomy_tree(self, populated_store):
        """Test building a complete taxonomy tree."""
        store = populated_store
        
        # Get full tree
        tree = store.get_taxonomy_tree("Technology")
        assert tree["category"] == "Technology"
        assert len(tree["subcategories"]) == 3
        
        # Check specific branch
        hardware_branch = None
        for sub in tree["subcategories"]:
            if sub["category"] == "Hardware":
                hardware_branch = sub
                break
        
        assert hardware_branch is not None
        assert len(hardware_branch["subcategories"]) == 2
        
        # Check compliance data is included
        computers_branch = None
        for sub in hardware_branch["subcategories"]:
            if sub["category"] == "Computers":
                computers_branch = sub
                break
        
        assert computers_branch is not None
        assert "compliance" in computers_branch
        assert "USA" in computers_branch["compliance"]
    
    def test_persistence(self, temp_storage_path):
        """Test saving and loading from disk."""
        # Create and populate a store
        store = TaxonomyStore(storage_path=temp_storage_path)
        store.add_node("Root")
        store.add_node("Child1", parent="Root")
        store.add_node("Child2", parent="Root")
        store.add_node("Grandchild", parent="Child1")
        
        # Add some mappings
        store.add_compliance_mapping("Child1", "USA", {"rules": ["Rule1"]})
        store.add_legal_mapping("Root", "Global", {"laws": ["Law1"]})
        
        # Save to disk
        assert store.save() is True
        assert os.path.exists(temp_storage_path)
        
        # Create a new store and load from disk
        new_store = TaxonomyStore(storage_path=temp_storage_path)
        
        # Verify data was loaded correctly
        assert "Root" in new_store.nodes
        assert "Child1" in new_store.nodes
        assert "Grandchild" in new_store.nodes
        assert new_store.get_parent("Child1") == "Root"
        assert "Child1" in new_store.compliance_mappings
        assert "USA" in new_store.compliance_mappings["Child1"]
        assert "Root" in new_store.legal_mappings
    
    def test_clear(self, populated_store):
        """Test clearing all data."""
        store = populated_store
        
        # Verify store has data
        assert len(store.nodes) > 0
        assert len(store.edges) > 0
        
        # Clear the store
        store.clear()
        
        # Verify data is cleared
        assert len(store.nodes) == 0
        assert len(store.edges) == 0
        assert len(store.parents) == 0
        assert len(store.compliance_mappings) == 0
        assert len(store.legal_mappings) == 0
        assert store.dirty is True  # Should be marked as dirty after clearing