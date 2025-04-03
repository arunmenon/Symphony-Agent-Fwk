"""Knowledge Graph enhanced agent capabilities."""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from symphony.memory.kg_memory import (
    ConversationKnowledgeGraphMemory,
    KnowledgeGraphMemory,
    Triplet,
)
from symphony.utils.types import Message


class KnowledgeGraphEnhancedAgentMixin:
    """Mixin that adds knowledge graph capabilities to agents."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up logger
        self.kg_logger = logging.getLogger(f"symphony.agent.kg.{getattr(self, 'id', 'unknown')}")
        
        # Initialize KG memory if compatible
        self._init_kg_memory()
    
    def _init_kg_memory(self) -> None:
        """Initialize knowledge graph memory if available."""
        if hasattr(self, "memory"):
            # Check if memory is a KG memory
            if isinstance(self.memory, KnowledgeGraphMemory):
                self.kg_logger.info("Using existing knowledge graph memory")
                self.kg_memory = self.memory
            else:
                self.kg_logger.info("Agent has memory but it's not a knowledge graph memory")
                self.kg_memory = None
        else:
            self.kg_logger.warning("Agent has no memory attribute")
            self.kg_memory = None
    
    async def add_knowledge_triplet(
        self, 
        subject: str, 
        predicate: str, 
        object: str,
        confidence: float = 1.0,
        source: Optional[str] = None
    ) -> bool:
        """Add a knowledge triplet to the agent's knowledge graph.
        
        Args:
            subject: The subject entity
            predicate: The relationship
            object: The object entity
            confidence: The confidence score (0-1)
            source: Optional source of the triplet
            
        Returns:
            Whether the operation was successful
        """
        if not self.kg_memory:
            self.kg_logger.warning("Cannot add triplet - no knowledge graph memory available")
            return False
            
        triplet = Triplet(
            subject=subject,
            predicate=predicate,
            object=object,
            confidence=confidence,
            source=source or getattr(self, "id", "agent")
        )
        
        return await self.kg_memory.add_triplet(triplet)
    
    async def search_knowledge(
        self, 
        query: str, 
        limit: int = 10,
        semantic: bool = True
    ) -> List[Any]:
        """Search the agent's knowledge graph.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            semantic: Whether to use semantic search
            
        Returns:
            List of search results
        """
        if not self.kg_memory:
            self.kg_logger.warning("Cannot search knowledge - no knowledge graph memory available")
            return []
            
        return await self.kg_memory.search(
            query=query,
            limit=limit,
            semantic=semantic
        )
    
    async def extract_knowledge_from_text(self, text: str) -> List[Triplet]:
        """Extract knowledge triplets from text and add them to the knowledge graph.
        
        Args:
            text: The text to extract knowledge from
            
        Returns:
            List of extracted triplets
        """
        if not self.kg_memory:
            self.kg_logger.warning("Cannot extract knowledge - no knowledge graph memory available")
            return []
            
        return await self.kg_memory.extract_and_store(
            text=text,
            source=getattr(self, "id", "agent")
        )
    
    async def get_entity_knowledge(self, entity: str) -> Dict[str, Any]:
        """Get knowledge about a specific entity.
        
        Args:
            entity: The entity to get knowledge about
            
        Returns:
            Dictionary of entity information and connections
        """
        if not self.kg_memory:
            self.kg_logger.warning("Cannot get entity knowledge - no knowledge graph memory available")
            return {}
            
        return await self.kg_memory.get_entity_connections(entity)
    
    async def query_relevant_knowledge(self, context: str, limit: int = 5) -> List[str]:
        """Query the knowledge graph for information relevant to a given context.
        
        Args:
            context: The context to find relevant knowledge for
            limit: Maximum number of knowledge items to return
            
        Returns:
            List of relevant knowledge statements
        """
        if not self.kg_memory:
            self.kg_logger.warning("Cannot query relevant knowledge - no knowledge graph memory available")
            return []
            
        results = await self.kg_memory.search(
            query=context,
            limit=limit,
            semantic=True
        )
        
        # Format results as natural language statements
        statements = []
        for result in results:
            if isinstance(result, dict) and "subject" in result and "predicate" in result and "object" in result:
                statement = f"{result['subject']} {result['predicate']} {result['object']}"
                statements.append(statement)
            elif isinstance(result, dict) and "text" in result:
                statements.append(result["text"])
            else:
                statements.append(str(result))
                
        return statements
    
    async def enrich_message_with_knowledge(self, message: Message) -> Message:
        """Enrich a message with relevant knowledge from the knowledge graph.
        
        Args:
            message: The message to enrich
            
        Returns:
            Enriched message
        """
        if not self.kg_memory:
            return message
            
        # Skip if not a user message
        if message.role != "user":
            return message
            
        # Get relevant knowledge
        knowledge = await self.query_relevant_knowledge(message.content)
        
        if not knowledge:
            return message
            
        # Add knowledge to message metadata
        enriched_message = Message(
            role=message.role,
            content=message.content,
            additional_kwargs={
                **message.additional_kwargs,
                "knowledge_context": knowledge
            }
        )
        
        return enriched_message