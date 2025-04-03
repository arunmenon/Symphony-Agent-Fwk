"""Unit tests for local knowledge graph memory."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from symphony.memory.local_kg_memory import (
    Entity, Relationship, KnowledgeTriplet, LocalGraph,
    LocalKnowledgeGraphMemory, SimpleEmbeddingModel, TripletExtractor
)


class TestLocalKGComponents:
    """Test suite for local knowledge graph components."""
    
    def test_entity_initialization(self):
        """Test entity initialization."""
        entity = Entity(name="TestEntity", type="TestType")
        
        assert entity.name == "TestEntity"
        assert entity.type == "TestType"
        assert entity.properties == {}
        assert entity.id is not None
    
    def test_relationship_initialization(self):
        """Test relationship initialization."""
        relationship = Relationship(
            source_id="source_id",
            target_id="target_id",
            type="TestRelation"
        )
        
        assert relationship.source_id == "source_id"
        assert relationship.target_id == "target_id"
        assert relationship.type == "TestRelation"
        assert relationship.properties == {}
        assert relationship.id is not None
    
    def test_triplet_initialization(self):
        """Test knowledge triplet initialization."""
        triplet = KnowledgeTriplet(
            subject="TestSubject",
            predicate="TestPredicate",
            object="TestObject",
            confidence=0.9,
            source="TestSource"
        )
        
        assert triplet.subject == "TestSubject"
        assert triplet.predicate == "TestPredicate"
        assert triplet.object == "TestObject"
        assert triplet.confidence == 0.9
        assert triplet.source == "TestSource"
        assert triplet.id is not None
        
        # Test text representation
        assert triplet.as_text() == "TestSubject TestPredicate TestObject"
    
    def test_simple_embedding_model(self):
        """Test simple embedding model."""
        model = SimpleEmbeddingModel(dimension=10)
        
        # Test embedding generation
        embedding = model.embed("test text")
        
        assert len(embedding) == 10
        assert all(isinstance(x, float) for x in embedding)
        
        # Test consistent embeddings for same text
        embedding2 = model.embed("test text")
        assert embedding == embedding2
        
        # Test different embeddings for different text
        embedding3 = model.embed("different text")
        assert embedding != embedding3


class TestLocalGraph:
    """Test suite for local graph functionality."""
    
    def test_graph_initialization(self):
        """Test graph initialization."""
        graph = LocalGraph()
        
        assert graph.entities == {}
        assert graph.entity_names == {}
        assert graph.relationships == {}
        assert len(graph.rel_index) == 0
        assert graph.triplets == []
        assert graph.embedding_model is not None
    
    def test_add_entity(self):
        """Test adding entities to the graph."""
        graph = LocalGraph()
        
        # Add a new entity
        entity = graph.add_entity(
            name="TestEntity",
            entity_type="TestType",
            properties={"prop1": "value1"}
        )
        
        assert entity.name == "TestEntity"
        assert entity.type == "TestType"
        assert entity.properties == {"prop1": "value1"}
        assert entity.id in graph.entities
        assert graph.entity_names["TestEntity"] == entity.id
        
        # Add same entity again - should return existing entity
        entity2 = graph.add_entity(name="TestEntity")
        assert entity2.id == entity.id
        
        # Update properties of existing entity
        entity3 = graph.add_entity(
            name="TestEntity",
            properties={"prop2": "value2"}
        )
        
        assert entity3.id == entity.id
        assert entity3.properties == {"prop1": "value1", "prop2": "value2"}
    
    def test_add_relationship(self):
        """Test adding relationships to the graph."""
        graph = LocalGraph()
        
        # Add entities
        entity1 = graph.add_entity(name="Entity1")
        entity2 = graph.add_entity(name="Entity2")
        
        # Add relationship
        rel = graph.add_relationship(
            source=entity1,
            relationship_type="related_to",
            target=entity2,
            properties={"prop1": "value1"}
        )
        
        assert rel.source_id == entity1.id
        assert rel.target_id == entity2.id
        assert rel.type == "related_to"
        assert rel.properties == {"prop1": "value1"}
        assert rel.id in graph.relationships
        assert rel in graph.rel_index[entity1.id]
        assert rel in graph.rel_index[entity2.id]
        
        # Test adding relationship by entity name
        rel2 = graph.add_relationship(
            source="Entity1",
            relationship_type="another_relation",
            target="Entity2"
        )
        
        assert rel2.source_id == entity1.id
        assert rel2.target_id == entity2.id
        
        # Test adding relationship with non-existent entities
        rel3 = graph.add_relationship(
            source="NewEntity1",
            relationship_type="knows",
            target="NewEntity2"
        )
        
        # New entities should be created
        assert "NewEntity1" in graph.entity_names
        assert "NewEntity2" in graph.entity_names
    
    def test_add_triplet(self):
        """Test adding knowledge triplets to the graph."""
        graph = LocalGraph()
        
        triplet = KnowledgeTriplet(
            subject="Entity1",
            predicate="is_related_to",
            object="Entity2",
            confidence=0.9
        )
        
        subject, relation, object_entity = graph.add_triplet(triplet)
        
        # Check that entities were created
        assert subject.name == "Entity1"
        assert object_entity.name == "Entity2"
        
        # Check that the relationship was created
        assert relation.source_id == subject.id
        assert relation.target_id == object_entity.id
        assert relation.type == "is_related_to"
        
        # Check that the triplet was stored
        assert triplet in graph.triplets
    
    def test_get_entity_relationships(self):
        """Test getting entity relationships."""
        graph = LocalGraph()
        
        # Add entities and relationships
        entity1 = graph.add_entity(name="Entity1")
        entity2 = graph.add_entity(name="Entity2")
        entity3 = graph.add_entity(name="Entity3")
        
        rel1 = graph.add_relationship(
            source=entity1,
            relationship_type="knows",
            target=entity2
        )
        
        rel2 = graph.add_relationship(
            source=entity3,
            relationship_type="follows",
            target=entity1
        )
        
        # Get relationships for entity1
        relationships = graph.get_entity_relationships(entity1.id)
        
        # Should have two relationships
        assert len(relationships) == 2
        
        # Check outgoing relationship
        found_outgoing = False
        for source, rel_type, target in relationships:
            if source.id == entity1.id and rel_type == "knows" and target.id == entity2.id:
                found_outgoing = True
                break
        
        assert found_outgoing
        
        # Check incoming relationship (should have inverse_ prefix)
        found_incoming = False
        for source, rel_type, target in relationships:
            if source.id == entity1.id and rel_type == "inverse_follows" and target.id == entity3.id:
                found_incoming = True
                break
        
        assert found_incoming


class TestLocalKnowledgeGraphMemory:
    """Test suite for LocalKnowledgeGraphMemory."""
    
    @pytest.mark.asyncio
    async def test_memory_initialization(self, mock_llm_client):
        """Test memory initialization."""
        memory = LocalKnowledgeGraphMemory(
            llm_client=mock_llm_client,
            auto_extract=True
        )
        
        assert memory.llm_client == mock_llm_client
        assert memory.graph is not None
        assert memory.auto_extract is True
        assert memory.extractor is not None
    
    @pytest.mark.asyncio
    async def test_add_triplet(self, kg_memory):
        """Test adding a triplet to memory."""
        triplet = await kg_memory.add_triplet(
            subject="Symphony",
            predicate="is",
            object="a framework",
            confidence=0.95,
            source="test"
        )
        
        assert triplet.subject == "Symphony"
        assert triplet.predicate == "is"
        assert triplet.object == "a framework"
        assert triplet.confidence == 0.95
        assert triplet.source == "test"
        
        # Check that entities were created in the graph
        assert kg_memory.graph.get_entity("Symphony") is not None
        assert kg_memory.graph.get_entity("a framework") is not None
    
    @pytest.mark.asyncio
    async def test_extract_and_store(self, kg_memory):
        """Test extracting and storing triplets from text."""
        text = "Symphony is an agent framework that supports multiple AI agents."
        
        triplets = await kg_memory.extract_and_store(
            text=text,
            source="test"
        )
        
        # The mock LLM client should return some triplets
        assert len(triplets) > 0
        
        # Check that triplets were stored in the graph
        assert len(kg_memory.graph.triplets) >= len(triplets)
    
    @pytest.mark.asyncio
    async def test_search(self, kg_memory):
        """Test searching the knowledge graph."""
        # Add some triplets first
        await kg_memory.add_triplet(
            subject="Symphony",
            predicate="is",
            object="an agent framework",
            confidence=0.95
        )
        
        await kg_memory.add_triplet(
            subject="Symphony",
            predicate="supports",
            object="multiple agents",
            confidence=0.9
        )
        
        # Search for 'agent'
        results = await kg_memory.search(
            query="agent",
            limit=5,
            search_type="combined"
        )
        
        # Should find both entities and triplets
        assert len(results) > 0
        
        # Check that we have both entity and triplet results
        entity_results = [r for r in results if r.get("type") == "entity"]
        triplet_results = [r for r in results if r.get("type") == "triplet"]
        
        assert len(entity_results) + len(triplet_results) == len(results)
    
    @pytest.mark.asyncio
    async def test_get_entity_knowledge(self, kg_memory):
        """Test getting knowledge about an entity."""
        # Add some triplets first
        await kg_memory.add_triplet(
            subject="Symphony",
            predicate="is",
            object="an agent framework",
            confidence=0.95
        )
        
        await kg_memory.add_triplet(
            subject="Symphony",
            predicate="supports",
            object="multiple agents",
            confidence=0.9
        )
        
        # Get knowledge about Symphony
        knowledge = await kg_memory.get_entity_knowledge("Symphony")
        
        # Should have entity and relationships
        assert knowledge.get("entity") is not None
        assert knowledge.get("entity").get("name") == "Symphony"
        
        # Should have relationships
        relationships = knowledge.get("relationships", [])
        assert len(relationships) >= 2
        
        # Check for specific relationships
        found_is_relation = False
        found_supports_relation = False
        
        for rel in relationships:
            if (rel.get("subject") == "Symphony" and 
                rel.get("predicate") == "is" and
                rel.get("object") == "an agent framework"):
                found_is_relation = True
            
            if (rel.get("subject") == "Symphony" and
                rel.get("predicate") == "supports" and
                rel.get("object") == "multiple agents"):
                found_supports_relation = True
        
        assert found_is_relation
        assert found_supports_relation