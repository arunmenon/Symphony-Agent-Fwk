"""Knowledge Graph memory implementation using Graphiti integration."""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import requests
from pydantic import BaseModel, Field, model_validator

from symphony.memory.base import BaseMemory
from symphony.utils.types import Message


class Entity(BaseModel):
    """An entity in the knowledge graph."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    vector: Optional[List[float]] = None


class Relationship(BaseModel):
    """A relationship between entities in the knowledge graph."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class Triplet(BaseModel):
    """A knowledge triplet (subject, predicate, object)."""
    
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    source: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphitiConfig(BaseModel):
    """Configuration for Graphiti connection."""
    
    endpoint: str = "http://localhost:8000"  # Default Graphiti endpoint
    api_key: Optional[str] = None
    project_id: str = "default"
    timeout: int = 30  # Timeout in seconds
    
    @model_validator(mode='after')
    def check_api_key(self) -> 'GraphitiConfig':
        """Check if API key is set in environment if not provided."""
        if not self.api_key:
            # Try to get from environment
            self.api_key = os.environ.get("GRAPHITI_API_KEY")
        return self


class GraphitiClient:
    """Client for interacting with the Graphiti API."""
    
    def __init__(self, config: GraphitiConfig):
        """Initialize the Graphiti client."""
        self.config = config
        self.logger = logging.getLogger("symphony.memory.graphiti")
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
            
        return headers
    
    async def ingest_text(self, text: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Ingest text into Graphiti.
        
        Args:
            text: The text to ingest
            document_id: Optional document ID
            
        Returns:
            Response from Graphiti API
        """
        if not document_id:
            document_id = str(uuid.uuid4())
            
        url = f"{self.config.endpoint}/api/v1/documents"
        payload = {
            "id": document_id,
            "text": text,
            "project_id": self.config.project_id
        }
        
        try:
            response = await asyncio.to_thread(
                requests.post,
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code not in (200, 201):
                self.logger.error(f"Error ingesting text: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Error ingesting text: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def add_triplet(self, triplet: Triplet) -> Dict[str, Any]:
        """Add a knowledge triplet to Graphiti.
        
        Args:
            triplet: The triplet to add
            
        Returns:
            Response from Graphiti API
        """
        url = f"{self.config.endpoint}/api/v1/triplets"
        payload = triplet.model_dump()
        
        try:
            response = await asyncio.to_thread(
                requests.post,
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code not in (200, 201):
                self.logger.error(f"Error adding triplet: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Error adding triplet: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        use_semantic: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search the knowledge graph.
        
        Args:
            query: The search query
            limit: Maximum number of results
            use_semantic: Whether to use semantic search
            filters: Optional filters for search
            
        Returns:
            Search results from Graphiti API
        """
        url = f"{self.config.endpoint}/api/v1/search"
        payload = {
            "query": query,
            "limit": limit,
            "project_id": self.config.project_id,
            "use_semantic": use_semantic
        }
        
        if filters:
            payload["filters"] = filters
            
        try:
            response = await asyncio.to_thread(
                requests.post,
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code != 200:
                self.logger.error(f"Error searching: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text, "results": []}
                
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Error searching: {str(e)}")
            return {"success": False, "error": str(e), "results": []}
    
    async def get_entity_connections(self, entity_name: str) -> Dict[str, Any]:
        """Get connections for a specific entity.
        
        Args:
            entity_name: The name of the entity
            
        Returns:
            Entity connections from Graphiti API
        """
        url = f"{self.config.endpoint}/api/v1/entities/{entity_name}/connections"
        params = {"project_id": self.config.project_id}
        
        try:
            response = await asyncio.to_thread(
                requests.get,
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.config.timeout
            )
            
            if response.status_code != 200:
                self.logger.error(f"Error getting entity connections: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text, "connections": []}
                
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Error getting entity connections: {str(e)}")
            return {"success": False, "error": str(e), "connections": []}


class TripletExtractor:
    """Extracts knowledge triplets from text using LLM."""
    
    def __init__(self, llm_client):
        """Initialize the triplet extractor."""
        self.llm_client = llm_client
        self.logger = logging.getLogger("symphony.memory.kg.extractor")
        
    async def extract_triplets(self, text: str) -> List[Triplet]:
        """Extract knowledge triplets from text.
        
        Args:
            text: The text to extract triplets from
            
        Returns:
            List of extracted triplets
        """
        # Prepare prompt for LLM
        prompt = f"""Extract factual knowledge triplets (subject, predicate, object) from the following text.
Format each triplet as JSON: {{"subject": "...", "predicate": "...", "object": "..."}}
Only extract factual statements, not opinions or hypotheticals.

Text:
{text}

Knowledge Triplets (one per line):"""
        
        try:
            response = await self.llm_client.generate(prompt)
            
            # Parse triplets from response
            triplets = []
            for line in response.split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                    
                try:
                    # Try to parse as JSON
                    if line.startswith("{") and line.endswith("}"):
                        data = json.loads(line)
                        if "subject" in data and "predicate" in data and "object" in data:
                            triplet = Triplet(
                                subject=data["subject"],
                                predicate=data["predicate"],
                                object=data["object"],
                                confidence=data.get("confidence", 1.0),
                                source="llm_extraction",
                                metadata={"original_text": text}
                            )
                            triplets.append(triplet)
                except json.JSONDecodeError:
                    # Try simpler parsing as a fallback
                    if " " in line and line.count(" ") >= 2:
                        parts = line.split(" ", 2)
                        if len(parts) == 3:
                            triplet = Triplet(
                                subject=parts[0],
                                predicate=parts[1],
                                object=parts[2],
                                confidence=0.7,  # Lower confidence for fallback parsing
                                source="llm_extraction",
                                metadata={"original_text": text}
                            )
                            triplets.append(triplet)
            
            return triplets
            
        except Exception as e:
            self.logger.error(f"Error extracting triplets: {str(e)}")
            return []


class KnowledgeGraphMemory(BaseMemory):
    """Memory implementation using a knowledge graph backed by Graphiti."""
    
    def __init__(
        self,
        graphiti_config: Optional[GraphitiConfig] = None,
        llm_client = None,
        auto_extract: bool = True
    ):
        """Initialize the knowledge graph memory.
        
        Args:
            graphiti_config: Configuration for Graphiti connection
            llm_client: LLM client for triplet extraction
            auto_extract: Whether to automatically extract triplets from stored text
        """
        self.config = graphiti_config or GraphitiConfig()
        self.client = GraphitiClient(self.config)
        self.llm_client = llm_client
        self.auto_extract = auto_extract
        
        if auto_extract and not llm_client:
            raise ValueError("LLM client is required for automatic triplet extraction")
            
        if auto_extract and llm_client:
            self.extractor = TripletExtractor(llm_client)
        
        self.logger = logging.getLogger("symphony.memory.kg")
        
    async def store(self, key: str, value: Any) -> None:
        """Store a value in the knowledge graph.
        
        Args:
            key: The key to store the value under
            value: The value to store
        """
        if isinstance(value, Triplet):
            # Store a triplet directly
            await self.client.add_triplet(value)
        elif isinstance(value, str):
            # Store text and optionally extract triplets
            await self.client.ingest_text(value, document_id=key)
            
            # Extract triplets if enabled
            if self.auto_extract and self.llm_client:
                triplets = await self.extractor.extract_triplets(value)
                for triplet in triplets:
                    await self.client.add_triplet(triplet)
        else:
            # Try to convert to string
            try:
                value_str = str(value)
                await self.client.ingest_text(value_str, document_id=key)
                
                # Extract triplets if enabled
                if self.auto_extract and self.llm_client:
                    triplets = await self.extractor.extract_triplets(value_str)
                    for triplet in triplets:
                        await self.client.add_triplet(triplet)
            except Exception as e:
                self.logger.error(f"Error storing value: {str(e)}")
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value from the knowledge graph.
        
        This is not typically used for KG memory as it's not a key-value store.
        For KG, use search() instead.
        
        Args:
            key: The key to retrieve
            
        Returns:
            Retrieved value or None if not found
        """
        # Not directly applicable for KG, but we can search for the key
        search_result = await self.client.search(key, limit=1, use_semantic=False)
        
        if search_result.get("success", False) and search_result.get("results"):
            return search_result["results"][0]
        
        return None
    
    async def search(
        self, 
        query: str, 
        limit: Optional[int] = None,
        semantic: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Search the knowledge graph.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            semantic: Whether to use semantic search
            filters: Optional filters for search
            
        Returns:
            List of search results
        """
        limit = limit or 10
        
        search_result = await self.client.search(
            query=query,
            limit=limit,
            use_semantic=semantic,
            filters=filters
        )
        
        if search_result.get("success", False):
            return search_result.get("results", [])
        
        return []
    
    async def add_triplet(self, triplet: Triplet) -> bool:
        """Add a knowledge triplet to the graph.
        
        Args:
            triplet: The triplet to add
            
        Returns:
            Whether the operation was successful
        """
        result = await self.client.add_triplet(triplet)
        return result.get("success", False)
    
    async def get_entity_connections(self, entity: str) -> Dict[str, Any]:
        """Get connections for a specific entity.
        
        Args:
            entity: The entity to get connections for
            
        Returns:
            Entity connections data
        """
        result = await self.client.get_entity_connections(entity)
        if result.get("success", False):
            return result.get("connections", {})
        
        return {}
    
    async def extract_and_store(self, text: str, source: Optional[str] = None) -> List[Triplet]:
        """Extract triplets from text and store them.
        
        Args:
            text: The text to extract triplets from
            source: Optional source identifier
            
        Returns:
            List of extracted and stored triplets
        """
        if not self.llm_client:
            self.logger.error("LLM client is required for triplet extraction")
            return []
            
        triplets = await self.extractor.extract_triplets(text)
        
        # Update source if provided
        if source:
            for triplet in triplets:
                triplet.source = source
        
        # Store triplets
        for triplet in triplets:
            await self.client.add_triplet(triplet)
            
        return triplets


class ConversationKnowledgeGraphMemory(KnowledgeGraphMemory):
    """Knowledge graph memory specialized for conversation history."""
    
    def __init__(
        self,
        graphiti_config: Optional[GraphitiConfig] = None,
        llm_client = None,
        auto_extract: bool = True
    ):
        """Initialize conversation knowledge graph memory."""
        super().__init__(graphiti_config, llm_client, auto_extract)
        self._messages: List[Message] = []
        
    async def add_message(self, message: Message) -> None:
        """Add a message to the conversation history and to the knowledge graph.
        
        Args:
            message: The message to add
        """
        # Add to local list
        self._messages.append(message)
        
        # Store in Graphiti
        content = message.content
        document_id = f"message_{len(self._messages)}"
        await self.client.ingest_text(content, document_id=document_id)
        
        # Create basic triplet for the message
        speaker_triplet = Triplet(
            subject=f"message_{len(self._messages)}",
            predicate="was_said_by",
            object=message.role,
            confidence=1.0,
            source="conversation",
            metadata={
                "timestamp": time.time(),
                "message_index": len(self._messages) - 1
            }
        )
        await self.client.add_triplet(speaker_triplet)
        
        # Extract knowledge triplets if enabled
        if self.auto_extract and self.llm_client:
            triplets = await self.extractor.extract_triplets(content)
            for triplet in triplets:
                triplet.source = f"message_{len(self._messages)}"
                triplet.metadata["role"] = message.role
                triplet.metadata["message_index"] = len(self._messages) - 1
                await self.client.add_triplet(triplet)
    
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
            limit: Maximum number of results to return
            
        Returns:
            List of search results with message information
        """
        limit = limit or 10
        
        # Search for the query
        search_result = await self.client.search(
            query=query,
            limit=limit,
            use_semantic=True,
            filters={"type": "conversation"}
        )
        
        results = []
        if search_result.get("success", False):
            for item in search_result.get("results", []):
                # Extract message_index if available
                message_index = item.get("metadata", {}).get("message_index")
                if message_index is not None and 0 <= message_index < len(self._messages):
                    results.append({
                        "message": self._messages[message_index],
                        "score": item.get("score", 0.0),
                        "metadata": item.get("metadata", {})
                    })
                else:
                    results.append(item)
        
        return results
    
    async def get_related_facts(self, entity: str, limit: Optional[int] = None) -> List[Triplet]:
        """Get facts related to an entity from the knowledge graph.
        
        Args:
            entity: The entity to get facts for
            limit: Maximum number of facts to return
            
        Returns:
            List of related triplets
        """
        limit = limit or 10
        
        # Get entity connections
        connections = await self.client.get_entity_connections(entity)
        
        result = []
        if connections.get("success", False):
            triplets = connections.get("triplets", [])
            for triplet_data in triplets[:limit]:
                try:
                    triplet = Triplet(
                        subject=triplet_data.get("subject", ""),
                        predicate=triplet_data.get("predicate", ""),
                        object=triplet_data.get("object", ""),
                        confidence=triplet_data.get("confidence", 1.0),
                        source=triplet_data.get("source", ""),
                        timestamp=triplet_data.get("timestamp", time.time()),
                        metadata=triplet_data.get("metadata", {})
                    )
                    result.append(triplet)
                except Exception as e:
                    self.logger.error(f"Error parsing triplet: {str(e)}")
        
        return result