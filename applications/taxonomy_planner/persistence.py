"""Persistence layer for Taxonomy Planner.

This module provides efficient storage for taxonomy structures with incremental
persistence to disk. It uses an adjacency list representation for the taxonomy tree.
"""

import json
import os
import time
from typing import Dict, List, Optional, Any

class TaxonomyStore:
    """Efficient storage for taxonomy structure with incremental persistence.
    
    This class provides a specialized storage solution for taxonomy structures,
    optimized for the Taxonomy Planner application. It manages:
    
    1. Node data (categories with metadata)
    2. Edge data (parent-child relationships)
    3. Compliance mappings
    4. Legal mappings
    5. Persistent storage to disk
    
    The storage uses an adjacency list structure for efficient traversal
    and supports incremental persistence to minimize data loss.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the taxonomy store.
        
        Args:
            storage_path: Path to save the taxonomy data (optional)
        """
        self.storage_path = storage_path
        
        # Category data storage
        self.nodes: Dict[str, Dict[str, Any]] = {}  # category -> node data
        self.edges: Dict[str, List[str]] = {}  # category -> list of children
        self.parents: Dict[str, str] = {}  # child -> parent mapping for quick lookups
        
        # Mappings for compliance and legal requirements
        self.compliance_mappings: Dict[str, Dict[str, Any]] = {}  # category -> requirements by jurisdiction
        self.legal_mappings: Dict[str, Dict[str, Any]] = {}  # category -> legal requirements by jurisdiction
        
        # Persistence tracking
        self.last_saved: float = 0
        self.dirty: bool = False
        
        # Load from disk if path provided
        if storage_path and os.path.exists(storage_path):
            self.load()
    
    def add_node(self, category: str, parent: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a category node to the taxonomy.
        
        Args:
            category: Category name
            parent: Parent category (if any)
            metadata: Additional category metadata
        """
        # Skip if node already exists
        if category not in self.nodes:
            # Add node with metadata
            self.nodes[category] = metadata or {}
            self.edges[category] = []
        
        # Connect to parent if specified
        if parent:
            # Skip if already connected
            if category not in self.edges.get(parent, []):
                # Ensure parent exists
                if parent not in self.nodes:
                    self.add_node(parent)
                
                # Add edge from parent to child
                if parent not in self.edges:
                    self.edges[parent] = []
                self.edges[parent].append(category)
                
                # Record parent relationship
                self.parents[category] = parent
            
        # Mark as needing save
        self.dirty = True
    
    def get_node(self, category: str) -> Optional[Dict[str, Any]]:
        """Get a category node's metadata.
        
        Args:
            category: Category name
            
        Returns:
            Node metadata or None if not found
        """
        return self.nodes.get(category)
    
    def get_children(self, category: str) -> List[str]:
        """Get child categories for a given category.
        
        Args:
            category: Parent category name
            
        Returns:
            List of child category names
        """
        return self.edges.get(category, [])
    
    def get_parent(self, category: str) -> Optional[str]:
        """Get parent category for a given category.
        
        Args:
            category: Child category name
            
        Returns:
            Parent category name or None if no parent
        """
        return self.parents.get(category)
    
    def get_all_nodes(self) -> List[str]:
        """Get all category names in the taxonomy.
        
        Returns:
            List of all category names
        """
        return list(self.nodes.keys())
    
    def add_compliance_mapping(self, category: str, jurisdiction: str, requirements: Any) -> None:
        """Add compliance requirements for a category in a jurisdiction.
        
        Args:
            category: Category name
            jurisdiction: Jurisdiction name (e.g., 'USA', 'EU')
            requirements: Compliance requirements
        """
        if category not in self.compliance_mappings:
            self.compliance_mappings[category] = {}
        
        self.compliance_mappings[category][jurisdiction] = requirements
        self.dirty = True
    
    def get_compliance_mapping(self, category: str, jurisdiction: Optional[str] = None) -> Any:
        """Get compliance requirements for a category.
        
        Args:
            category: Category name
            jurisdiction: Specific jurisdiction to get requirements for
            
        Returns:
            Compliance requirements (all or for specific jurisdiction)
        """
        if category not in self.compliance_mappings:
            return {} if jurisdiction else {}
        
        if jurisdiction:
            return self.compliance_mappings[category].get(jurisdiction, {})
        
        return self.compliance_mappings[category]
    
    def add_legal_mapping(self, category: str, jurisdiction: str, requirements: Any) -> None:
        """Add legal requirements for a category in a jurisdiction.
        
        Args:
            category: Category name
            jurisdiction: Jurisdiction name (e.g., 'USA', 'EU')
            requirements: Legal requirements
        """
        if category not in self.legal_mappings:
            self.legal_mappings[category] = {}
        
        self.legal_mappings[category][jurisdiction] = requirements
        self.dirty = True
    
    def get_legal_mapping(self, category: str, jurisdiction: Optional[str] = None) -> Any:
        """Get legal requirements for a category.
        
        Args:
            category: Category name
            jurisdiction: Specific jurisdiction to get requirements for
            
        Returns:
            Legal requirements (all or for specific jurisdiction)
        """
        if category not in self.legal_mappings:
            return {} if jurisdiction else {}
        
        if jurisdiction:
            return self.legal_mappings[category].get(jurisdiction, {})
        
        return self.legal_mappings[category]
    
    def get_ancestors(self, category: str) -> List[str]:
        """Get all ancestors of a category (path to root).
        
        Args:
            category: Category name
            
        Returns:
            List of ancestor categories (ordered from parent to root)
        """
        ancestors = []
        current = category
        
        while current in self.parents:
            parent = self.parents[current]
            ancestors.append(parent)
            current = parent
            
            # Check for cycles (should never happen)
            if parent in ancestors:
                break
        
        return ancestors
    
    def get_descendants(self, category: str) -> List[str]:
        """Get all descendants of a category.
        
        Args:
            category: Category name
            
        Returns:
            List of all descendant categories
        """
        if category not in self.edges:
            return []
        
        # Use BFS to find all descendants
        descendants = []
        queue = self.edges[category].copy()
        
        while queue:
            current = queue.pop(0)
            descendants.append(current)
            queue.extend(self.edges.get(current, []))
        
        return descendants
    
    def get_taxonomy_tree(self, root: str) -> Dict[str, Any]:
        """Build a complete taxonomy tree from the given root.
        
        Args:
            root: Root category
            
        Returns:
            Dictionary representation of the taxonomy tree
        """
        if root not in self.nodes:
            return {}
        
        # Start with root node
        tree = {
            "category": root,
            "subcategories": [],
            "compliance": self.compliance_mappings.get(root, {}),
            "legal": self.legal_mappings.get(root, {})
        }
        
        # Add the following enhanced fields to support comprehensive taxonomies
        enhanced_structure = {
            "description": "",
            "enforcement_examples": [],
            "social_media_trends": [],
            "risk_level": "",
            "detection_methods": []
        }
        
        # Add metadata and any existing node data
        tree.update(self.nodes[root])
        
        # Add enhanced structure fields if they don't already exist
        for key, default_value in enhanced_structure.items():
            if key not in tree:
                tree[key] = default_value
        
        # Build children recursively
        for child in self.edges.get(root, []):
            child_tree = self.get_taxonomy_tree(child)
            if child_tree:
                tree["subcategories"].append(child_tree)
        
        return tree
    
    def save(self, force: bool = False) -> bool:
        """Save taxonomy data to disk.
        
        Args:
            force: Force save even if not dirty
            
        Returns:
            Whether the save was successful
        """
        # Skip if no storage path or not dirty
        if not self.storage_path or (not self.dirty and not force):
            return False
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.storage_path)), exist_ok=True)
            
            # Prepare data for serialization
            data = {
                "nodes": self.nodes,
                "edges": self.edges,
                "parents": self.parents,
                "compliance_mappings": self.compliance_mappings,
                "legal_mappings": self.legal_mappings,
                "last_updated": time.time()
            }
            
            # Write to file
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.last_saved = time.time()
            self.dirty = False
            return True
            
        except Exception as e:
            print(f"Error saving taxonomy data: {e}")
            return False
    
    def load(self) -> bool:
        """Load taxonomy data from disk.
        
        Returns:
            Whether the load was successful
        """
        if not self.storage_path or not os.path.exists(self.storage_path):
            return False
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # Restore data
            self.nodes = data.get("nodes", {})
            self.edges = data.get("edges", {})
            self.parents = data.get("parents", {})
            self.compliance_mappings = data.get("compliance_mappings", {})
            self.legal_mappings = data.get("legal_mappings", {})
            
            self.last_saved = time.time()
            self.dirty = False
            return True
            
        except Exception as e:
            print(f"Error loading taxonomy data: {e}")
            return False
    
    def clear(self) -> None:
        """Clear all taxonomy data."""
        self.nodes = {}
        self.edges = {}
        self.parents = {}
        self.compliance_mappings = {}
        self.legal_mappings = {}
        self.dirty = True