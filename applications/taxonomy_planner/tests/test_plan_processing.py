"""Tests for the plan processing functionality in Taxonomy Planner."""

import os
import pytest
import tempfile
from typing import Dict, Any, List

from applications.taxonomy_planner.main import TaxonomyPlanner
from applications.taxonomy_planner.config import TaxonomyConfig
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
def planner_instance():
    """Create a taxonomy planner instance for testing."""
    config = TaxonomyConfig()
    planner = TaxonomyPlanner(config)
    return planner


class TestPlanProcessing:
    """Test the plan processing functionality."""
    
    @pytest.mark.asyncio
    async def test_extract_categories_from_bullet_points(self, taxonomy_store, planner_instance):
        """Test extracting categories from bullet point lists."""
        # Sample planner output with bullet points
        plan_output = """
        # Taxonomy for Technology
        
        Here's a comprehensive taxonomy for Technology:
        
        ## Main Categories
        
        * Hardware - Physical components and devices
        * Software - Programs and applications
        * Networks - Communication infrastructure
        * Data - Information storage and processing
        * Security - Protection of systems and data
        """
        
        # Create context for processing
        context = {
            "plan": plan_output,
            "root_category": "Technology",
            "store": taxonomy_store
        }
        
        # Process the plan
        initial_categories = await planner_instance._process_plan(context)
        
        # Verify extracted categories
        assert len(initial_categories) >= 4  # At least the 4 major categories
        assert "Hardware" in initial_categories
        assert "Software" in initial_categories
        assert "Networks" in initial_categories
        assert "Data" in initial_categories
        
        # Verify categories were added to store
        assert "Hardware" in taxonomy_store.nodes
        assert taxonomy_store.get_parent("Hardware") == "Technology"
    
    @pytest.mark.asyncio
    async def test_extract_categories_from_numbered_lists(self, taxonomy_store, planner_instance):
        """Test extracting categories from numbered lists."""
        # Sample planner output with numbered lists
        plan_output = """
        # Taxonomy for Vehicles
        
        Below is a structured taxonomy for Vehicles:
        
        1. Automobiles - Cars, trucks, and other road vehicles
        2. Aircraft - Flying vehicles
        3. Watercraft - Boats, ships, and other water vehicles
        4. Rail vehicles - Trains and related vehicles
        5. Off-road vehicles - ATVs, snowmobiles, etc.
        """
        
        # Create context for processing
        context = {
            "plan": plan_output,
            "root_category": "Vehicles",
            "store": taxonomy_store
        }
        
        # Process the plan
        initial_categories = await planner_instance._process_plan(context)
        
        # Verify extracted categories
        assert len(initial_categories) >= 4  # At least 4 major categories
        assert "Automobiles" in initial_categories
        assert "Aircraft" in initial_categories
        assert "Watercraft" in initial_categories
        assert "Rail vehicles" in initial_categories
        
        # Verify categories were added to store
        assert "Automobiles" in taxonomy_store.nodes
        assert taxonomy_store.get_parent("Automobiles") == "Vehicles"
    
    @pytest.mark.asyncio
    async def test_extract_categories_from_headers(self, taxonomy_store, planner_instance):
        """Test extracting categories from capitalized headers."""
        # Sample planner output with headers
        plan_output = """
        # Taxonomy for Animals
        
        A comprehensive taxonomy for the Animal Kingdom:
        
        Mammals
        - Warm-blooded animals with fur
        - Examples: Dogs, cats, humans, whales
        
        Birds
        - Feathered vertebrates with wings
        - Examples: Eagles, sparrows, penguins
        
        Reptiles
        - Cold-blooded vertebrates with scales
        - Examples: Snakes, lizards, turtles
        
        Fish
        - Aquatic vertebrates with gills
        - Examples: Salmon, sharks, goldfish
        """
        
        # Create context for processing
        context = {
            "plan": plan_output,
            "root_category": "Animals",
            "store": taxonomy_store
        }
        
        # Process the plan
        initial_categories = await planner_instance._process_plan(context)
        
        # Verify extracted categories
        assert len(initial_categories) >= 3  # At least 3 major categories
        assert "Mammals" in initial_categories
        assert "Birds" in initial_categories
        assert "Reptiles" in initial_categories
        
        # Verify categories were added to store
        assert "Mammals" in taxonomy_store.nodes
        assert taxonomy_store.get_parent("Mammals") == "Animals"
    
    @pytest.mark.asyncio
    async def test_filter_non_categories(self, taxonomy_store, planner_instance):
        """Test filtering out phrases that are not categories."""
        # Sample planner output with some non-category phrases
        plan_output = """
        # Taxonomy for Food
        
        Here's a comprehensive food taxonomy:
        
        * Fruits - Edible plant structures with seeds
        * Vegetables - Edible plant parts
        * This list is not exhaustive
        * The following categories are also important
        * Grains - Seeds from grasses like wheat and rice
        * Proteins - Meat, fish, and plant-based proteins
        * These categories can overlap in some cases
        """
        
        # Create context for processing
        context = {
            "plan": plan_output,
            "root_category": "Food",
            "store": taxonomy_store
        }
        
        # Process the plan
        initial_categories = await planner_instance._process_plan(context)
        
        # Verify extracted categories (should filter out non-categories)
        assert "Fruits" in initial_categories
        assert "Vegetables" in initial_categories
        assert "Grains" in initial_categories
        assert "Proteins" in initial_categories
        
        # Verify non-categories were filtered out
        assert "This list is not exhaustive" not in initial_categories
        assert "The following categories are also important" not in initial_categories
        assert "These categories can overlap in some cases" not in initial_categories
    
    @pytest.mark.asyncio
    async def test_deduplication(self, taxonomy_store, planner_instance):
        """Test deduplication of categories."""
        # Sample planner output with duplicate categories
        plan_output = """
        # Taxonomy for Sports
        
        Main categories:
        
        * Team Sports - Sports played in teams
        * Individual Sports - Sports played individually
        
        Further breakdown:
        
        * Team Sports - Including basketball, soccer, etc.
        * Water Sports - Sports played in water
        * Combat Sports - Boxing, martial arts, etc.
        """
        
        # Create context for processing
        context = {
            "plan": plan_output,
            "root_category": "Sports",
            "store": taxonomy_store
        }
        
        # Process the plan
        initial_categories = await planner_instance._process_plan(context)
        
        # Verify extracted categories (should deduplicate "Team Sports")
        team_sports_count = initial_categories.count("Team Sports")
        assert team_sports_count == 1  # Should only appear once
        
        assert "Individual Sports" in initial_categories
        assert "Water Sports" in initial_categories
        assert "Combat Sports" in initial_categories
    
    @pytest.mark.asyncio
    async def test_store_persistence(self, taxonomy_store, planner_instance, temp_storage_path):
        """Test that the processed plan is persisted to storage."""
        # Sample plan
        plan_output = """
        # Taxonomy for Books
        
        * Fiction - Novels, short stories, etc.
        * Non-fiction - Factual books
        * Reference - Dictionaries, encyclopedias, etc.
        """
        
        # Create context for processing
        context = {
            "plan": plan_output,
            "root_category": "Books",
            "store": taxonomy_store
        }
        
        # Process the plan
        await planner_instance._process_plan(context)
        
        # Create a new store instance pointing to the same file
        new_store = TaxonomyStore(storage_path=temp_storage_path)
        
        # Verify categories were persisted
        assert "Books" in new_store.nodes
        assert "Fiction" in new_store.nodes
        assert "Non-fiction" in new_store.nodes
        assert "Reference" in new_store.nodes
        
        # Verify parent-child relationships were persisted
        assert new_store.get_parent("Fiction") == "Books"
        assert new_store.get_parent("Non-fiction") == "Books"