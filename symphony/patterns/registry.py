"""Pattern registry for Symphony patterns.

This module provides a registry for Symphony patterns, allowing
them to be discovered and instantiated by name.
"""

from typing import Dict, Any, List, Type, Callable, Optional
from symphony.patterns.base import Pattern, PatternConfig


class PatternRegistry:
    """Registry for Symphony patterns.
    
    This class provides a central registry for pattern types and
    factory functions. It allows patterns to be discovered and
    instantiated by name.
    """
    
    def __init__(self):
        """Initialize pattern registry."""
        self.patterns: Dict[str, Dict[str, Any]] = {}
    
    def register_pattern(
        self,
        name: str,
        factory: Callable[[Dict[str, Any]], Pattern],
        category: str,
        description: str,
        schema: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Register a pattern.
        
        Args:
            name: Pattern name
            factory: Factory function to create pattern instances
            category: Pattern category (reasoning, verification, etc.)
            description: Pattern description
            schema: JSON Schema for pattern configuration (optional)
            metadata: Additional metadata (optional)
        """
        self.patterns[name] = {
            "factory": factory,
            "category": category,
            "description": description,
            "schema": schema or {},
            "metadata": metadata or {}
        }
    
    def create_pattern(self, name: str, config: Dict[str, Any] = None) -> Pattern:
        """Create a pattern instance.
        
        Args:
            name: Pattern name
            config: Pattern configuration (optional)
            
        Returns:
            Pattern instance
            
        Raises:
            ValueError: If pattern name is not registered
        """
        if name not in self.patterns:
            raise ValueError(f"Pattern {name} not registered")
        
        # Create pattern configuration
        pattern_config = PatternConfig(
            name=name,
            description=self.patterns[name]["description"],
            **(config or {})
        )
        
        # Create pattern instance
        factory = self.patterns[name]["factory"]
        return factory(pattern_config)
    
    def get_pattern_info(self, name: str) -> Dict[str, Any]:
        """Get information about a pattern.
        
        Args:
            name: Pattern name
            
        Returns:
            Pattern information
            
        Raises:
            ValueError: If pattern name is not registered
        """
        if name not in self.patterns:
            raise ValueError(f"Pattern {name} not registered")
        
        return {
            "name": name,
            "category": self.patterns[name]["category"],
            "description": self.patterns[name]["description"],
            "schema": self.patterns[name]["schema"],
            "metadata": self.patterns[name]["metadata"]
        }
    
    def list_patterns(self, category: str = None) -> List[Dict[str, Any]]:
        """List registered patterns.
        
        Args:
            category: Filter by category (optional)
            
        Returns:
            List of pattern information
        """
        result = []
        
        for name, data in self.patterns.items():
            if category is None or data["category"] == category:
                result.append({
                    "name": name,
                    "category": data["category"],
                    "description": data["description"],
                    "metadata": data["metadata"]
                })
        
        return result
    
    def get_categories(self) -> List[str]:
        """Get list of pattern categories.
        
        Returns:
            List of category names
        """
        categories = set()
        
        for data in self.patterns.values():
            categories.add(data["category"])
        
        return sorted(list(categories))