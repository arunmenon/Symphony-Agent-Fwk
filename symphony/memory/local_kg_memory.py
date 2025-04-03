"""Local knowledge graph memory implementation inspired by Zep semantics."""

import asyncio
import datetime
import json
import os
import pickle
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field, model_validator

from symphony.memory.base import BaseMemory
from symphony.utils.types import Message


class Entity(BaseModel):
    """An entity in the knowledge graph."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    embedding: Optional[List[float]] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class Relationship(BaseModel):
    """A relationship between entities in the knowledge graph."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    type: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    def key(self) -> Tuple[str, str, str]:
        """Get a unique key for the relationship."""
        return (self.source_id, self.type, self.target_id)


class KnowledgeTriplet(BaseModel):
    """A knowledge triplet (subject, predicate, object)."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str  # Can be entity ID or name
    predicate: str
    object: str  # Can be entity ID, name, or literal value
    confidence: float = 1.0
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    source: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def as_text(self) -> str:
        """Get a text representation of the triplet."""
        return f"{self.subject} {self.predicate} {self.object}"


class EmbeddingModel:
    """Base class for embedding models."""
    
    def __init__(self, dimension: int = 384):
        """Initialize the embedding model with specified dimension."""
        self.dimension = dimension
    
    def embed(self, text: str) -> List[float]:
        """Generate an embedding for the given text."""
        raise NotImplementedError("Subclasses must implement this method")


class SimpleEmbeddingModel(EmbeddingModel):
    """Simple embedding model using a deterministic hashing approach.
    
    This is intended for development and testing purposes only.
    In a production environment, use a proper embedding model.
    """
    
    def __init__(self, dimension: int = 384):
        """Initialize the simple embedding model."""
        super().__init__(dimension)
        self.word_vectors: Dict[str, List[float]] = {}
    
    def embed(self, text: str) -> List[float]:
        """Generate an embedding for the given text."""
        if not text:
            return [0.0] * self.dimension
            
        # Simple preprocessing - lowercase and remove punctuation
        text = text.lower()
        for char in '.,!?;:()[]{}"\'':
            text = text.replace(char, ' ')
            
        words = text.split()
        if not words:
            return [0.0] * self.dimension
            
        # Get or create vectors for each word
        vectors = [self._get_word_vector(word) for word in words]
        
        # Average the word vectors
        avg_vector = np.mean(vectors, axis=0)
        
        # Normalize to unit length
        norm = np.linalg.norm(avg_vector)
        if norm > 0:
            avg_vector = avg_vector / norm
            
        return avg_vector.tolist()
    
    def _get_word_vector(self, word: str) -> List[float]:
        """Get a vector for a word, creating a new one if needed."""
        if word not in self.word_vectors:
            # Create a deterministic vector based on the word
            np.random.seed(hash(word) % 2**32)
            self.word_vectors[word] = np.random.randn(self.dimension).tolist()
            
        return self.word_vectors[word]


class TripletExtractor:
    """Extracts knowledge triplets from text using LLM."""
    
    def __init__(self, llm_client, confidence_threshold: float = 0.7):
        """Initialize the triplet extractor."""
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
        self.extraction_cache = {}  # Simple cache to avoid re-extracting identical text
    
    async def extract_triplets(self, text: str, extraction_mode: str = "default") -> List[KnowledgeTriplet]:
        """Extract knowledge triplets from text.
        
        Args:
            text: The text to extract triplets from
            extraction_mode: Mode of extraction (default, conservative, aggressive, entity-focused)
            
        Returns:
            List of extracted triplets
        """
        # Skip if text is too short
        if len(text) < 20:
            return []
            
        # Check cache first (using text + mode as key)
        cache_key = f"{extraction_mode}:{text}"
        if cache_key in self.extraction_cache:
            return self.extraction_cache[cache_key]
            
        # Select extraction prompt based on mode
        if extraction_mode == "conservative":
            prompt = self._get_conservative_extraction_prompt(text)
        elif extraction_mode == "aggressive":
            prompt = self._get_aggressive_extraction_prompt(text)
        elif extraction_mode == "entity-focused":
            prompt = self._get_entity_focused_extraction_prompt(text)
        else:  # default
            prompt = self._get_default_extraction_prompt(text)
        
        try:
            # Generate triplets using LLM
            response = await self.llm_client.generate(prompt)
            
            # Parse triplets from response
            triplets = []
            for line in response.split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                    
                try:
                    # Try to parse as JSON
                    if "{" in line and "}" in line:
                        # Extract JSON part even if it's not the whole line
                        json_part = line[line.find("{"):line.rfind("}")+1]
                        data = json.loads(json_part)
                        
                        if "subject" in data and "predicate" in data and "object" in data:
                            confidence = data.get("confidence", 1.0)
                            
                            # Skip low confidence triplets
                            if confidence >= self.confidence_threshold:
                                triplet = KnowledgeTriplet(
                                    subject=data["subject"],
                                    predicate=data["predicate"],
                                    object=data["object"],
                                    confidence=confidence,
                                    source="llm_extraction",
                                    metadata={
                                        "original_text": text,
                                        "extraction_mode": extraction_mode
                                    }
                                )
                                triplets.append(triplet)
                except Exception:
                    # Skip parsing errors
                    continue
            
            # Store in cache
            self.extraction_cache[cache_key] = triplets
            
            return triplets
            
        except Exception as e:
            print(f"Error extracting triplets: {str(e)}")
            return []
    
    def _get_default_extraction_prompt(self, text: str) -> str:
        """Get the default extraction prompt."""
        return f"""Extract factual knowledge triplets (subject, predicate, object) from the following text.
Format each triplet as a JSON object: {{"subject": "...", "predicate": "...", "object": "...", "confidence": 0.95}}
Assign a confidence score between 0 and 1 to each triplet.
Only extract factual statements, not opinions or hypotheticals.
Return one triplet per line.

Guidelines:
- Focus on clear, factual information
- Subjects and objects should usually be nouns or noun phrases
- Predicates should express a relationship, property, or action
- Canonicalize entities when possible (e.g., "the company" → proper name)
- Use consistent predicate forms (e.g., "was born in" rather than "is born in")

Text:
{text}

Knowledge Triplets:"""
    
    def _get_conservative_extraction_prompt(self, text: str) -> str:
        """Get a conservative extraction prompt that favors precision over recall."""
        return f"""Extract only the most clearly stated, factual knowledge triplets from the following text.
Format each triplet as a JSON object: {{"subject": "...", "predicate": "...", "object": "...", "confidence": 0.95}}
Only extract facts that are explicitly stated, with high confidence (0.9+).
Focus on the most important entities and relationships.

Text:
{text}

Knowledge Triplets:"""
    
    def _get_aggressive_extraction_prompt(self, text: str) -> str:
        """Get an aggressive extraction prompt that favors recall over precision."""
        return f"""Extract all possible knowledge triplets from the text, including implied information.
Format each triplet as a JSON object: {{"subject": "...", "predicate": "...", "object": "...", "confidence": 0.7}}
Extract both explicit statements and reasonable inferences.
Include potential relationships between entities even if they're not directly stated.
Assign lower confidence scores (0.7-0.8) to inferred information.

Text:
{text}

Knowledge Triplets:"""
    
    def _get_entity_focused_extraction_prompt(self, text: str) -> str:
        """Get an entity-focused extraction prompt that emphasizes entity properties."""
        return f"""Extract knowledge triplets focused on entities and their properties from the text.
Format each triplet as a JSON object: {{"subject": "...", "predicate": "...", "object": "...", "confidence": 0.9}}
Focus on:
1. Entity types (e.g., "X is a person/company/product")
2. Entity properties (e.g., "X has property Y")
3. Entity relationships (e.g., "X is related to Y")

Identify the main entities first, then extract their attributes and relationships.
Normalize entity names to their canonical form.

Text:
{text}

Knowledge Triplets:"""


class LocalGraph:
    """A local graph implementation for storing entities and relationships."""
    
    def __init__(self, embedding_model: Optional[EmbeddingModel] = None):
        """Initialize the local graph."""
        self.entities: Dict[str, Entity] = {}  # id -> Entity
        self.entity_names: Dict[str, str] = {}  # name -> id
        self.relationships: Dict[str, Relationship] = {}  # id -> Relationship
        self.rel_index: Dict[str, List[Relationship]] = defaultdict(list)  # entity_id -> [Relationships]
        self.triplets: List[KnowledgeTriplet] = []
        self.embedding_model = embedding_model or SimpleEmbeddingModel()
        self._last_modified = datetime.datetime.now()
    
    def add_entity(
        self, 
        name: str, 
        entity_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> Entity:
        """Add an entity to the graph.
        
        Args:
            name: The name of the entity
            entity_type: Optional type of the entity
            properties: Optional properties for the entity
            
        Returns:
            The added entity
        """
        # Check if entity already exists
        if name in self.entity_names:
            entity_id = self.entity_names[name]
            entity = self.entities[entity_id]
            
            # Update entity if needed
            if entity_type and entity_type != entity.type:
                entity.type = entity_type
                entity.updated_at = datetime.datetime.now()
                
            if properties:
                entity.properties.update(properties)
                entity.updated_at = datetime.datetime.now()
                
            return entity
        
        # Create new entity
        entity = Entity(
            name=name,
            type=entity_type,
            properties=properties or {},
            embedding=self.embedding_model.embed(name)
        )
        
        # Add to storage
        self.entities[entity.id] = entity
        self.entity_names[name] = entity.id
        
        return entity
    
    def get_entity(self, identifier: str) -> Optional[Entity]:
        """Get an entity by ID or name.
        
        Args:
            identifier: The ID or name of the entity
            
        Returns:
            The entity or None if not found
        """
        # Try as ID first
        if identifier in self.entities:
            return self.entities[identifier]
            
        # Try as name
        if identifier in self.entity_names:
            entity_id = self.entity_names[identifier]
            return self.entities[entity_id]
            
        return None
    
    def add_relationship(
        self,
        source: Union[str, Entity],
        relationship_type: str,
        target: Union[str, Entity],
        properties: Optional[Dict[str, Any]] = None
    ) -> Relationship:
        """Add a relationship between entities.
        
        Args:
            source: The source entity ID, name, or Entity object
            relationship_type: The type of relationship
            target: The target entity ID, name, or Entity object
            properties: Optional properties for the relationship
            
        Returns:
            The added relationship
        """
        # Resolve source and target to entities
        source_entity = source if isinstance(source, Entity) else self.get_entity(source)
        target_entity = target if isinstance(target, Entity) else self.get_entity(target)
        
        # Create entities if they don't exist
        if not source_entity:
            source_entity = self.add_entity(name=source if isinstance(source, str) else "unknown")
            
        if not target_entity:
            target_entity = self.add_entity(name=target if isinstance(target, str) else "unknown")
        
        # Create relationship
        relationship = Relationship(
            source_id=source_entity.id,
            target_id=target_entity.id,
            type=relationship_type,
            properties=properties or {}
        )
        
        # Check for duplicates
        for existing_rel in self.rel_index[source_entity.id]:
            if (existing_rel.source_id == relationship.source_id and
                existing_rel.type == relationship.type and
                existing_rel.target_id == relationship.target_id):
                
                # Update properties if provided
                if properties:
                    existing_rel.properties.update(properties)
                    existing_rel.updated_at = datetime.datetime.now()
                
                return existing_rel
        
        # Add to storage
        self.relationships[relationship.id] = relationship
        self.rel_index[source_entity.id].append(relationship)
        self.rel_index[target_entity.id].append(relationship)
        
        return relationship
    
    def add_triplet(self, triplet: KnowledgeTriplet) -> Tuple[Entity, Relationship, Entity]:
        """Add a knowledge triplet to the graph.
        
        Args:
            triplet: The triplet to add
            
        Returns:
            Tuple of (subject entity, relationship, object entity)
        """
        # Add subject entity
        subject_entity = self.add_entity(triplet.subject)
        
        # Add object entity
        object_entity = self.add_entity(triplet.object)
        
        # Add relationship
        relationship = self.add_relationship(
            source=subject_entity,
            relationship_type=triplet.predicate,
            target=object_entity,
            properties={"confidence": triplet.confidence, "source": triplet.source}
        )
        
        # Store triplet
        self.triplets.append(triplet)
        
        return (subject_entity, relationship, object_entity)
    
    def get_entity_relationships(self, entity_identifier: str) -> List[Tuple[Entity, str, Entity]]:
        """Get all relationships involving an entity.
        
        Args:
            entity_identifier: The ID or name of the entity
            
        Returns:
            List of (entity, relationship type, entity) tuples
        """
        entity = self.get_entity(entity_identifier)
        if not entity:
            return []
            
        result = []
        for rel in self.rel_index[entity.id]:
            source = self.entities[rel.source_id]
            target = self.entities[rel.target_id]
            
            if source.id == entity.id:
                # Outgoing relationship
                result.append((source, rel.type, target))
            else:
                # Incoming relationship
                result.append((target, f"inverse_{rel.type}", source))
                
        return result
    
    def search_entities(
        self, 
        query: str, 
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Tuple[Entity, float]]:
        """Search for entities by text similarity.
        
        Args:
            query: The search query
            limit: Maximum number of results
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (entity, score) tuples sorted by score
        """
        if not query or not self.entities:
            return []
            
        # Create query embedding
        query_embedding = self.embedding_model.embed(query)
        
        # Calculate similarity with all entities
        results = []
        for entity in self.entities.values():
            if entity.embedding:
                similarity = self._cosine_similarity(query_embedding, entity.embedding)
                if similarity >= threshold:
                    results.append((entity, similarity))
        
        # Sort by similarity and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def search_triplets(
        self, 
        query: str, 
        limit: int = 10
    ) -> List[Tuple[KnowledgeTriplet, float]]:
        """Search for triplets by text similarity.
        
        Args:
            query: The search query
            limit: Maximum number of results
            
        Returns:
            List of (triplet, score) tuples sorted by score
        """
        if not query or not self.triplets:
            return []
            
        # Create query embedding
        query_embedding = self.embedding_model.embed(query)
        
        # Calculate similarity with all triplets
        results = []
        for triplet in self.triplets:
            triplet_text = triplet.as_text()
            triplet_embedding = self.embedding_model.embed(triplet_text)
            
            similarity = self._cosine_similarity(query_embedding, triplet_embedding)
            results.append((triplet, similarity))
        
        # Sort by similarity and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def save(self, filepath: str) -> None:
        """Save the graph to a file.
        
        Args:
            filepath: The path to save to
        """
        data = {
            "entities": {k: v.model_dump() for k, v in self.entities.items()},
            "entity_names": self.entity_names,
            "relationships": {k: v.model_dump() for k, v in self.relationships.items()},
            "triplets": [t.model_dump() for t in self.triplets]
        }
        
        with open(filepath, "wb") as f:
            pickle.dump(data, f)
    
    def load(self, filepath: str) -> None:
        """Load the graph from a file.
        
        Args:
            filepath: The path to load from
        """
        if not os.path.exists(filepath):
            return
            
        with open(filepath, "rb") as f:
            data = pickle.load(f)
            
        # Clear current data
        self.entities.clear()
        self.entity_names.clear()
        self.relationships.clear()
        self.rel_index.clear()
        self.triplets = []
        
        # Load entities
        for entity_id, entity_data in data["entities"].items():
            self.entities[entity_id] = Entity(**entity_data)
            
        # Load entity names
        self.entity_names = data["entity_names"]
        
        # Load relationships
        for rel_id, rel_data in data["relationships"].items():
            relationship = Relationship(**rel_data)
            self.relationships[rel_id] = relationship
            self.rel_index[relationship.source_id].append(relationship)
            self.rel_index[relationship.target_id].append(relationship)
            
        # Load triplets
        for triplet_data in data["triplets"]:
            self.triplets.append(KnowledgeTriplet(**triplet_data))
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)


class LocalKnowledgeGraphMemory(BaseMemory):
    """Local knowledge graph memory implementation."""
    
    def __init__(
        self, 
        llm_client = None,
        embedding_model: Optional[EmbeddingModel] = None,
        storage_path: Optional[str] = None,
        auto_extract: bool = True
    ):
        """Initialize the knowledge graph memory.
        
        Args:
            llm_client: LLM client for triplet extraction
            embedding_model: Optional embedding model to use
            storage_path: Optional path to persist the graph
            auto_extract: Whether to extract triplets from text automatically
        """
        self.llm_client = llm_client
        self.graph = LocalGraph(embedding_model=embedding_model)
        self.storage_path = storage_path
        self.auto_extract = auto_extract
        
        # Initialize triplet extractor if auto_extract is enabled
        if auto_extract and llm_client:
            self.extractor = TripletExtractor(llm_client)
        else:
            self.extractor = None
        
        # Load existing data if available
        if storage_path and os.path.exists(storage_path):
            self.graph.load(storage_path)
    
    async def store(self, key: str, value: Any) -> None:
        """Store a value in the knowledge graph memory.
        
        Args:
            key: The key to store under
            value: The value to store
        """
        if isinstance(value, KnowledgeTriplet):
            # Store a triplet directly
            self.graph.add_triplet(value)
        elif isinstance(value, str) and len(value) > 0:
            # Store as document and extract triplets if enabled
            document_entity = self.graph.add_entity(
                name=key,
                entity_type="document",
                properties={"content": value, "timestamp": datetime.datetime.now().isoformat()}
            )
            
            # Extract triplets if enabled
            if self.auto_extract and self.extractor:
                triplets = await self.extractor.extract_triplets(value)
                for triplet in triplets:
                    self.graph.add_triplet(triplet)
                    
                    # Link document to triplet
                    self.graph.add_relationship(
                        source=document_entity,
                        relationship_type="contains",
                        target=triplet.subject,
                        properties={"confidence": triplet.confidence}
                    )
        else:
            # Try to convert to string
            try:
                str_value = str(value)
                await self.store(key, str_value)
            except:
                pass
        
        # Persist if storage path is set
        if self.storage_path:
            self.graph.save(self.storage_path)
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value from the knowledge graph memory.
        
        Args:
            key: The key to retrieve
            
        Returns:
            The retrieved value or None if not found
        """
        entity = self.graph.get_entity(key)
        if entity and "content" in entity.properties:
            return entity.properties["content"]
            
        return None
    
    async def search(
        self, 
        query: str, 
        limit: Optional[int] = None,
        search_type: str = "combined",
        threshold: float = 0.5,
        include_documents: bool = False
    ) -> List[Dict[str, Any]]:
        """Search the knowledge graph memory.
        
        Args:
            query: The search query
            limit: Maximum number of results
            search_type: Type of search (entities, triplets, combined)
            threshold: Minimum similarity score threshold
            include_documents: Whether to include linked documents in results
            
        Returns:
            List of search results
        """
        limit = limit or 10
        results = []
        
        if search_type in ("entities", "combined"):
            # Search entities
            entity_results = self.graph.search_entities(query, limit=limit, threshold=threshold)
            for entity, score in entity_results:
                result = {
                    "type": "entity",
                    "id": entity.id,
                    "name": entity.name,
                    "entity_type": entity.type,
                    "score": score,
                    "properties": entity.properties
                }
                
                # Add related entities if requested
                if include_documents and entity.type != "document":
                    # Find documents that mention this entity
                    related_docs = []
                    for rel in self.graph.rel_index.get(entity.id, []):
                        if rel.type == "mentions" and rel.source_id != entity.id:
                            # This is a document mentioning the entity
                            source_entity = self.graph.entities.get(rel.source_id)
                            if source_entity and source_entity.type == "document":
                                doc_content = source_entity.properties.get("content", "")
                                if len(doc_content) > 200:
                                    # Truncate long documents
                                    doc_content = doc_content[:200] + "..."
                                
                                related_docs.append({
                                    "id": source_entity.id,
                                    "content": doc_content,
                                    "timestamp": source_entity.properties.get("timestamp")
                                })
                    
                    if related_docs:
                        result["related_documents"] = related_docs
                
                results.append(result)
        
        if search_type in ("triplets", "combined"):
            # Search triplets
            triplet_results = self.graph.search_triplets(query, limit=limit)
            for triplet, score in triplet_results:
                result = {
                    "type": "triplet",
                    "id": triplet.id,
                    "subject": triplet.subject,
                    "predicate": triplet.predicate,
                    "object": triplet.object,
                    "confidence": triplet.confidence,
                    "score": score,
                    "source": triplet.source
                }
                results.append(result)
        
        # Sort by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
        
    async def semantic_query(
        self,
        query: str,
        limit: int = 10,
        query_expansion: bool = False,
        llm_client = None
    ) -> List[Dict[str, Any]]:
        """Perform a semantic query using the LLM to expand the query.
        
        Args:
            query: The user's query
            limit: Maximum number of results
            query_expansion: Whether to expand the query using LLM
            llm_client: Optional LLM client for query expansion
            
        Returns:
            List of relevant knowledge items
        """
        expanded_query = query
        
        # Expand query if requested and llm client is available
        if query_expansion and (llm_client or self.llm_client):
            client = llm_client or self.llm_client
            
            # Create expansion prompt
            expansion_prompt = f"""I want to search a knowledge graph for information related to this query:
"{query}"

Please generate 5-7 related search terms, keywords, and possible phrasings that would help find relevant information.
List them one per line.
"""
            
            try:
                # Get expansion from LLM
                expansion_response = await client.generate(expansion_prompt)
                
                # Extract terms
                expansion_terms = [
                    term.strip() for term in expansion_response.split('\n')
                    if term.strip() and not term.strip().startswith('#') and not term.strip().startswith('-')
                ]
                
                # Combine with original query
                if expansion_terms:
                    expanded_query = f"{query} {' '.join(expansion_terms)}"
            except Exception as e:
                print(f"Error expanding query: {str(e)}")
        
        # Perform search with expanded query
        return await self.search(
            query=expanded_query,
            limit=limit,
            search_type="combined",
            include_documents=True
        )
    
    async def add_triplet(
        self, 
        subject: str, 
        predicate: str, 
        object: str,
        confidence: float = 1.0,
        source: Optional[str] = None
    ) -> KnowledgeTriplet:
        """Add a knowledge triplet to the graph.
        
        Args:
            subject: The subject of the triplet
            predicate: The predicate of the triplet
            object: The object of the triplet
            confidence: The confidence score (0-1)
            source: Optional source of the triplet
            
        Returns:
            The added triplet
        """
        triplet = KnowledgeTriplet(
            subject=subject,
            predicate=predicate,
            object=object,
            confidence=confidence,
            source=source
        )
        
        self.graph.add_triplet(triplet)
        
        # Persist if storage path is set
        if self.storage_path:
            self.graph.save(self.storage_path)
            
        return triplet
    
    async def get_entity_knowledge(
        self, 
        entity_name: str
    ) -> Dict[str, Any]:
        """Get knowledge about an entity.
        
        Args:
            entity_name: The name of the entity
            
        Returns:
            Dictionary with entity information and relationships
        """
        entity = self.graph.get_entity(entity_name)
        if not entity:
            return {"entity": None, "relationships": []}
            
        relationships = self.graph.get_entity_relationships(entity.id)
        
        formatted_relationships = []
        for source, rel_type, target in relationships:
            formatted_relationships.append({
                "subject": source.name,
                "predicate": rel_type,
                "object": target.name
            })
            
        return {
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "properties": entity.properties
            },
            "relationships": formatted_relationships
        }
    
    async def extract_and_store(
        self, 
        text: str, 
        source: Optional[str] = None,
        extraction_mode: str = "default",
        store_text: bool = True
    ) -> List[KnowledgeTriplet]:
        """Extract triplets from text and store them.
        
        Args:
            text: The text to extract from
            source: Optional source identifier
            extraction_mode: Mode of extraction (default, conservative, aggressive, entity-focused)
            store_text: Whether to store the original text as a document
            
        Returns:
            List of extracted triplets
        """
        if not self.extractor:
            return []
        
        # Store the text as a document if requested
        if store_text:
            doc_id = f"doc_{uuid.uuid4()}"
            doc_entity = self.graph.add_entity(
                name=doc_id,
                entity_type="document",
                properties={
                    "content": text,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "source": source or "unknown"
                }
            )
        
        # Extract triplets with the specified mode
        triplets = await self.extractor.extract_triplets(text, extraction_mode=extraction_mode)
        
        # Set source if provided
        if source:
            for triplet in triplets:
                triplet.source = source
                
        # Store triplets and link to document
        for triplet in triplets:
            subject_entity, _, object_entity = self.graph.add_triplet(triplet)
            
            # Link document to entities
            if store_text and doc_entity:
                self.graph.add_relationship(
                    source=doc_entity,
                    relationship_type="mentions",
                    target=subject_entity
                )
                
                self.graph.add_relationship(
                    source=doc_entity,
                    relationship_type="mentions", 
                    target=object_entity
                )
            
        # Persist if storage path is set
        if self.storage_path:
            self.graph.save(self.storage_path)
            
        return triplets
        
    async def extract_with_multiple_modes(
        self,
        text: str,
        source: Optional[str] = None,
        store_text: bool = True
    ) -> Dict[str, List[KnowledgeTriplet]]:
        """Extract triplets using multiple extraction modes for better coverage.
        
        Args:
            text: The text to extract from
            source: Optional source identifier
            store_text: Whether to store the original text as a document
            
        Returns:
            Dictionary of extraction mode to list of triplets
        """
        modes = ["default", "entity-focused", "aggressive"]
        results = {}
        
        # Store the text only once
        if store_text:
            doc_id = f"doc_{uuid.uuid4()}"
            doc_entity = self.graph.add_entity(
                name=doc_id,
                entity_type="document",
                properties={
                    "content": text,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "source": source or "unknown"
                }
            )
        else:
            doc_entity = None
        
        # Run extraction with each mode
        for mode in modes:
            triplets = await self.extractor.extract_triplets(text, extraction_mode=mode)
            
            # Set source if provided
            if source:
                for triplet in triplets:
                    triplet.source = source
                    
            # Store triplets and link to document
            for triplet in triplets:
                subject_entity, _, object_entity = self.graph.add_triplet(triplet)
                
                # Link document to entities (only if we stored the text)
                if doc_entity:
                    self.graph.add_relationship(
                        source=doc_entity,
                        relationship_type="mentions",
                        target=subject_entity
                    )
                    
                    self.graph.add_relationship(
                        source=doc_entity,
                        relationship_type="mentions", 
                        target=object_entity
                    )
            
            results[mode] = triplets
        
        # Persist if storage path is set
        if self.storage_path:
            self.graph.save(self.storage_path)
            
        return results
    
    def load(self) -> None:
        """Load the graph from storage."""
        if self.storage_path and os.path.exists(self.storage_path):
            self.graph.load(self.storage_path)
    
    def save(self) -> None:
        """Save the graph to storage."""
        if self.storage_path:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            self.graph.save(self.storage_path)
            
    def export_graph(self, format: str = "json", filepath: Optional[str] = None) -> Any:
        """Export the knowledge graph in various formats.
        
        Args:
            format: Format to export in ('json', 'networkx', 'visjs', 'cytoscape')
            filepath: Optional filepath to save the export to
            
        Returns:
            The exported graph in the requested format
        """
        # Add export methods to LocalGraph if they don't exist
        if not hasattr(LocalGraph, "export_to_networkx"):
            # Define export methods
            
            def export_to_networkx(self):
                """Export the graph to a NetworkX Graph object for analysis."""
                try:
                    import networkx as nx
                except ImportError:
                    raise ImportError("NetworkX is required for this functionality. Install it with 'pip install networkx'.")
                    
                G = nx.Graph()
                
                # Add entities as nodes
                for entity_id, entity in self.entities.items():
                    G.add_node(
                        entity_id, 
                        label=entity.name,
                        type=entity.type or "unknown",
                        properties=entity.properties
                    )
                    
                # Add relationships as edges
                for rel_id, rel in self.relationships.items():
                    G.add_edge(
                        rel.source_id,
                        rel.target_id,
                        key=rel_id,
                        type=rel.type,
                        properties=rel.properties
                    )
                    
                return G
                
            def export_to_visjs(self) -> Dict[str, List[Dict[str, Any]]]:
                """Export the graph to a format compatible with vis.js network visualization."""
                nodes = []
                edges = []
                
                # Add entities as nodes
                for entity_id, entity in self.entities.items():
                    node = {
                        "id": entity_id,
                        "label": entity.name,
                        "title": f"Type: {entity.type or 'unknown'}",
                        "group": entity.type or "unknown"
                    }
                    nodes.append(node)
                    
                # Add relationships as edges
                for rel_id, rel in self.relationships.items():
                    edge = {
                        "id": rel_id,
                        "from": rel.source_id,
                        "to": rel.target_id,
                        "label": rel.type,
                        "arrows": "to"
                    }
                    edges.append(edge)
                    
                return {"nodes": nodes, "edges": edges}
                
            def export_to_json(self) -> Dict[str, Any]:
                """Export the graph to a JSON-compatible format."""
                result = {
                    "entities": [],
                    "relationships": [],
                    "triplets": []
                }
                
                # Add entities
                for entity_id, entity in self.entities.items():
                    entity_data = entity.model_dump()
                    # Remove embedding vector for readability
                    if "embedding" in entity_data:
                        entity_data["embedding"] = f"<Vector({len(entity_data['embedding'])} dimensions)>"
                    result["entities"].append(entity_data)
                    
                # Add relationships
                for rel_id, rel in self.relationships.items():
                    result["relationships"].append(rel.model_dump())
                    
                # Add triplets
                for triplet in self.triplets:
                    result["triplets"].append(triplet.model_dump())
                    
                return result
                
            def export_to_cytoscape(self) -> Dict[str, List[Dict[str, Any]]]:
                """Export the graph to a format compatible with Cytoscape.js."""
                elements = {
                    "nodes": [],
                    "edges": []
                }
                
                # Add entities as nodes
                for entity_id, entity in self.entities.items():
                    node = {
                        "data": {
                            "id": entity_id,
                            "label": entity.name,
                            "type": entity.type or "unknown"
                        }
                    }
                    elements["nodes"].append(node)
                    
                # Add relationships as edges
                for rel_id, rel in self.relationships.items():
                    edge = {
                        "data": {
                            "id": rel_id,
                            "source": rel.source_id,
                            "target": rel.target_id,
                            "label": rel.type
                        }
                    }
                    elements["edges"].append(edge)
                    
                return elements
                
            # Add methods to the class
            setattr(LocalGraph, "export_to_networkx", export_to_networkx)
            setattr(LocalGraph, "export_to_visjs", export_to_visjs)
            setattr(LocalGraph, "export_to_json", export_to_json)
            setattr(LocalGraph, "export_to_cytoscape", export_to_cytoscape)
        
        # Call the appropriate export method
        if format == "networkx":
            result = self.graph.export_to_networkx()
        elif format == "visjs":
            result = self.graph.export_to_visjs()
        elif format == "cytoscape":
            result = self.graph.export_to_cytoscape()
        else:  # Default to JSON
            result = self.graph.export_to_json()
            
        # Save to file if requested
        if filepath and format != "networkx":  # Can't directly serialize networkx
            import json
            with open(filepath, 'w') as f:
                json.dump(result, f, indent=2, default=str)
                
        return result


class ConversationKnowledgeGraphMemory(LocalKnowledgeGraphMemory):
    """Knowledge graph memory specialized for conversations."""
    
    def __init__(
        self, 
        llm_client = None,
        embedding_model: Optional[EmbeddingModel] = None,
        storage_path: Optional[str] = None,
        auto_extract: bool = True
    ):
        """Initialize conversation knowledge graph memory."""
        super().__init__(llm_client, embedding_model, storage_path, auto_extract)
        self._messages: List[Message] = []
        
    async def add_message(self, message: Message) -> None:
        """Add a message to the conversation history.
        
        Args:
            message: The message to add
        """
        # Add to local list
        self._messages.append(message)
        
        # Create message entity
        message_id = f"message_{len(self._messages)}"
        message_entity = self.graph.add_entity(
            name=message_id,
            entity_type="message",
            properties={
                "content": message.content,
                "role": message.role,
                "index": len(self._messages) - 1,
                "timestamp": datetime.datetime.now().isoformat(),
                **message.additional_kwargs
            }
        )
        
        # Link to previous message if exists
        if len(self._messages) > 1:
            prev_message_id = f"message_{len(self._messages) - 1}"
            prev_message = self.graph.get_entity(prev_message_id)
            
            if prev_message:
                self.graph.add_relationship(
                    source=prev_message,
                    relationship_type="followed_by",
                    target=message_entity
                )
        
        # Extract knowledge if enabled
        if self.auto_extract and self.extractor and len(message.content) > 20:
            triplets = await self.extractor.extract_triplets(message.content)
            
            for triplet in triplets:
                # Store triplet
                subject_entity, _, object_entity = self.graph.add_triplet(triplet)
                
                # Link message to triplet entities
                self.graph.add_relationship(
                    source=message_entity,
                    relationship_type="mentions",
                    target=subject_entity
                )
                
                self.graph.add_relationship(
                    source=message_entity,
                    relationship_type="mentions",
                    target=object_entity
                )
        
        # Persist if storage path is set
        if self.storage_path:
            self.graph.save(self.storage_path)
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get the conversation history.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of messages
        """
        if limit is not None:
            return self._messages[-limit:]
        return self._messages
    
    async def search_conversation(
        self, 
        query: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search conversation history.
        
        Args:
            query: The search query
            limit: Maximum number of results
            
        Returns:
            List of search results with message information
        """
        limit = limit or 10
        
        # Create query embedding
        embedding_model = self.graph.embedding_model
        query_embedding = embedding_model.embed(query)
        
        # Search messages by similarity
        results = []
        for i, message in enumerate(self._messages):
            if not message.content:
                continue
                
            message_embedding = embedding_model.embed(message.content)
            similarity = self._cosine_similarity(query_embedding, message_embedding)
            
            results.append({
                "message": message,
                "index": i,
                "score": similarity
            })
        
        # Sort by similarity and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)