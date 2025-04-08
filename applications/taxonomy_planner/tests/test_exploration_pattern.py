"""Tests for the enhanced exploration pattern in Taxonomy Planner."""

import os
import pytest
import tempfile
import asyncio
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

from applications.taxonomy_planner.patterns import SearchEnhancedExplorationPattern
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
def taxonomy_store(temp_storage_path):
    """Create a taxonomy store for testing."""
    return TaxonomyStore(storage_path=temp_storage_path)


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = MagicMock()
    
    # Configure agent.execute to return appropriate test responses
    async def mock_execute(prompt, use_tools=None):
        """Mock agent execution with predefined responses."""
        if "internal knowledge" in prompt and "Technology" in prompt:
            return """
            Subcategories from knowledge base:
            - Hardware
            - Software
            - Networks
            """
        elif "internal knowledge" in prompt and "Hardware" in prompt:
            return """
            Subcategories from knowledge base:
            - Computers
            - Mobile Devices
            - Peripherals
            """
        elif "search for subcategories" in prompt and "Technology" in prompt:
            return """
            Subcategories from search:
            - Hardware
            - Software
            - Data Science
            - Artificial Intelligence
            - Cloud Computing
            """
        elif "search for subcategories" in prompt and "Hardware" in prompt:
            return """
            Subcategories from search:
            - Computers
            - Mobile Devices
            - Peripherals
            - Storage Devices
            - Input Devices
            - Output Devices
            """
        elif "validate and filter" in prompt and "Technology" in prompt:
            return """
            Validated subcategories:
            - Hardware
            - Software
            - Networks
            - Data Science
            - Artificial Intelligence
            - Cloud Computing
            """
        elif "validate and filter" in prompt and "Hardware" in prompt:
            return """
            Validated subcategories:
            - Computers
            - Mobile Devices
            - Peripherals
            - Storage Devices
            """
        elif "select" in prompt and "important" in prompt:
            # Simulate prioritization for breadth limiting
            categories = prompt.split(":")[1].strip().split(",")
            selected = categories[:3]  # Just take the first 3 for simplicity
            return "- " + "\n- ".join(selected)
        
        return "No relevant subcategories found."
    
    agent.execute = mock_execute
    return agent


@pytest.fixture
def exploration_pattern():
    """Create a search-enhanced exploration pattern for testing."""
    return SearchEnhancedExplorationPattern()


class TestExplorationPattern:
    """Test the enhanced exploration pattern."""
    
    @pytest.mark.asyncio
    async def test_basic_exploration(self, taxonomy_store, mock_agent, exploration_pattern):
        """Test basic exploration of a category."""
        # Set up context
        context = {
            "category": "Technology",
            "parent": None,
            "store": taxonomy_store,
            "agent": mock_agent,
            "tools": ["search_knowledge_base", "search_subcategories"],
            "depth": 1,
            "max_depth": 3,
            "breadth_limit": 10,
            "strategy": "depth_first"
        }
        
        # Execute the pattern
        result = await exploration_pattern.execute(context)
        
        # Verify result
        assert result["category"] == "Technology"
        assert len(result["subcategories"]) >= 4  # Should have at least 4 subcategories
        
        # Check store state
        assert "Technology" in taxonomy_store.nodes
        assert "Hardware" in taxonomy_store.nodes
        assert "Software" in taxonomy_store.nodes
        assert "Data Science" in taxonomy_store.nodes
        
        # Check parent-child relationships
        assert taxonomy_store.get_parent("Hardware") == "Technology"
        assert taxonomy_store.get_parent("Software") == "Technology"
    
    @pytest.mark.asyncio
    async def test_breadth_limiting(self, taxonomy_store, mock_agent, exploration_pattern):
        """Test breadth limiting to prevent explosion."""
        # Set up context with small breadth limit
        context = {
            "category": "Technology",
            "parent": None,
            "store": taxonomy_store,
            "agent": mock_agent,
            "tools": ["search_knowledge_base", "search_subcategories"],
            "depth": 1,
            "max_depth": 3,
            "breadth_limit": 3,  # Small breadth limit to trigger limiting
            "strategy": "depth_first"
        }
        
        # Execute the pattern
        result = await exploration_pattern.execute(context)
        
        # Verify result
        assert result["category"] == "Technology"
        assert len(result["subcategories"]) <= 3  # Should be limited to 3 subcategories
        
        # Verify agent was asked to prioritize
        prioritization_calls = [
            call for call, _ in mock_agent.execute.call_args_list 
            if "select" in str(call) and "important" in str(call)
        ]
        assert len(prioritization_calls) > 0
    
    @pytest.mark.asyncio
    async def test_depth_first_strategy(self, taxonomy_store, mock_agent, exploration_pattern):
        """Test depth-first exploration strategy."""
        # Patch the _explore methods to track their calls
        with patch.object(exploration_pattern, '_explore_depth_first') as mock_depth_first, \
             patch.object(exploration_pattern, '_explore_breadth_first') as mock_breadth_first, \
             patch.object(exploration_pattern, '_explore_parallel') as mock_parallel:
            
            # Set up context
            context = {
                "category": "Technology",
                "parent": None,
                "store": taxonomy_store,
                "agent": mock_agent,
                "tools": ["search_knowledge_base", "search_subcategories"],
                "depth": 1,
                "max_depth": 3,
                "breadth_limit": 10,
                "strategy": "depth_first"  # Depth-first strategy
            }
            
            # Mock the strategy methods to prevent actual execution
            mock_depth_first.return_value = None
            mock_breadth_first.return_value = None
            mock_parallel.return_value = None
            
            # Execute the pattern
            await exploration_pattern.execute(context)
            
            # Verify the depth-first method was called
            assert mock_depth_first.called
            assert not mock_breadth_first.called
            assert not mock_parallel.called
    
    @pytest.mark.asyncio
    async def test_breadth_first_strategy(self, taxonomy_store, mock_agent, exploration_pattern):
        """Test breadth-first exploration strategy."""
        # Patch the _explore methods to track their calls
        with patch.object(exploration_pattern, '_explore_depth_first') as mock_depth_first, \
             patch.object(exploration_pattern, '_explore_breadth_first') as mock_breadth_first, \
             patch.object(exploration_pattern, '_explore_parallel') as mock_parallel:
            
            # Set up context
            context = {
                "category": "Technology",
                "parent": None,
                "store": taxonomy_store,
                "agent": mock_agent,
                "tools": ["search_knowledge_base", "search_subcategories"],
                "depth": 1,
                "max_depth": 3,
                "breadth_limit": 10,
                "strategy": "breadth_first"  # Breadth-first strategy
            }
            
            # Mock the strategy methods to prevent actual execution
            mock_depth_first.return_value = None
            mock_breadth_first.return_value = None
            mock_parallel.return_value = None
            
            # Execute the pattern
            await exploration_pattern.execute(context)
            
            # Verify the breadth-first method was called
            assert not mock_depth_first.called
            assert mock_breadth_first.called
            assert not mock_parallel.called
    
    @pytest.mark.asyncio
    async def test_parallel_strategy(self, taxonomy_store, mock_agent, exploration_pattern):
        """Test parallel exploration strategy."""
        # Patch the _explore methods to track their calls
        with patch.object(exploration_pattern, '_explore_depth_first') as mock_depth_first, \
             patch.object(exploration_pattern, '_explore_breadth_first') as mock_breadth_first, \
             patch.object(exploration_pattern, '_explore_parallel') as mock_parallel:
            
            # Set up context
            context = {
                "category": "Technology",
                "parent": None,
                "store": taxonomy_store,
                "agent": mock_agent,
                "tools": ["search_knowledge_base", "search_subcategories"],
                "depth": 1,
                "max_depth": 3,
                "breadth_limit": 10,
                "strategy": "parallel"  # Parallel strategy
            }
            
            # Mock the strategy methods to prevent actual execution
            mock_depth_first.return_value = None
            mock_breadth_first.return_value = None
            mock_parallel.return_value = None
            
            # Execute the pattern
            await exploration_pattern.execute(context)
            
            # Verify the parallel method was called
            assert not mock_depth_first.called
            assert not mock_breadth_first.called
            assert mock_parallel.called
    
    @pytest.mark.asyncio
    async def test_extract_subcategories(self, exploration_pattern):
        """Test extracting subcategories from different formats."""
        # Test extracting from bullet points
        bullet_result = """
        - Category1
        - Category2: with description
        * Category3
        • Category4: another description
        """
        bullets = exploration_pattern._extract_subcategories(bullet_result)
        assert "Category1" in bullets
        assert "Category2" in bullets
        assert "Category3" in bullets
        assert "Category4" in bullets
        
        # Test extracting from numbered lists
        numbered_result = """
        1. Category1
        2. Category2: with description
        3. Category3
        """
        numbered = exploration_pattern._extract_subcategories(numbered_result)
        assert "Category1" in numbered
        assert "Category2" in numbered
        assert "Category3" in numbered
        
        # Test extracting from dictionary
        dict_result = {"subcategories": ["DictCat1", "DictCat2"]}
        dict_cats = exploration_pattern._extract_subcategories(dict_result)
        assert "DictCat1" in dict_cats
        assert "DictCat2" in dict_cats
        
        # Test extracting from list
        list_result = ["ListCat1", "ListCat2"]
        list_cats = exploration_pattern._extract_subcategories(list_result)
        assert "ListCat1" in list_cats
        assert "ListCat2" in list_cats
    
    @pytest.mark.asyncio
    async def test_persistence_during_exploration(self, taxonomy_store, mock_agent, exploration_pattern, temp_storage_path):
        """Test that the store is persisted during exploration."""
        # Set up context
        context = {
            "category": "Technology",
            "parent": None,
            "store": taxonomy_store,
            "agent": mock_agent,
            "tools": ["search_knowledge_base", "search_subcategories"],
            "depth": 1,
            "max_depth": 2,
            "breadth_limit": 10,
            "strategy": "depth_first"
        }
        
        # Execute the pattern
        await exploration_pattern.execute(context)
        
        # Create a new store instance pointing to the same file
        new_store = TaxonomyStore(storage_path=temp_storage_path)
        
        # Verify data was persisted
        assert "Technology" in new_store.nodes
        assert "Hardware" in new_store.nodes
        assert "Software" in new_store.nodes
        
        # Verify parent-child relationships were persisted
        assert new_store.get_parent("Hardware") == "Technology"
    
    @pytest.mark.asyncio
    async def test_initial_categories_integration(self, taxonomy_store, mock_agent, exploration_pattern):
        """Test integration with initial categories from planner."""
        # Initial categories from planner
        initial_categories = ["Hardware", "Software", "Cloud Services", "Cybersecurity"]
        
        # Set up context with initial categories
        context = {
            "category": "Technology",
            "parent": None,
            "store": taxonomy_store,
            "agent": mock_agent,
            "tools": ["search_knowledge_base", "search_subcategories"],
            "depth": 1,
            "max_depth": 2,
            "breadth_limit": 10,
            "strategy": "depth_first",
            "initial_categories": initial_categories
        }
        
        # Execute the pattern
        result = await exploration_pattern.execute(context)
        
        # Verify initial categories were included
        all_categories = set(taxonomy_store.get_children("Technology"))
        for category in initial_categories:
            assert category in all_categories
        
        # "Cloud Services" and "Cybersecurity" should be included even if they weren't
        # in the mock agent's responses because they were provided as initial categories
        assert "Cloud Services" in all_categories
        assert "Cybersecurity" in all_categories