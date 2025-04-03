"""Local knowledge graph enhanced agent capabilities."""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from symphony.memory.local_kg_memory import (
    ConversationKnowledgeGraphMemory,
    KnowledgeTriplet,
    LocalKnowledgeGraphMemory,
)
from symphony.utils.types import Message


class LocalKGEnhancedAgentMixin:
    """Mixin that adds local knowledge graph capabilities to agents."""
    
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
            if isinstance(self.memory, LocalKnowledgeGraphMemory):
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
            
        triplet = await self.kg_memory.add_triplet(
            subject=subject,
            predicate=predicate,
            object=object,
            confidence=confidence,
            source=source or getattr(self, "id", "agent")
        )
        
        return triplet is not None
    
    async def search_knowledge(
        self, 
        query: str, 
        limit: int = 10,
        search_type: str = "combined",
        include_documents: bool = False
    ) -> List[Dict[str, Any]]:
        """Search the agent's knowledge graph.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            search_type: Type of search (entities, triplets, combined)
            include_documents: Whether to include linked documents in results
            
        Returns:
            List of search results
        """
        if not self.kg_memory:
            self.kg_logger.warning("Cannot search knowledge - no knowledge graph memory available")
            return []
            
        return await self.kg_memory.search(
            query=query,
            limit=limit,
            search_type=search_type,
            include_documents=include_documents
        )
        
    async def semantic_search_knowledge(
        self,
        query: str,
        limit: int = 10,
        query_expansion: bool = True
    ) -> List[Dict[str, Any]]:
        """Perform a semantic search of the knowledge graph with query expansion.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            query_expansion: Whether to expand the query using LLM
            
        Returns:
            List of search results
        """
        if not self.kg_memory:
            self.kg_logger.warning("Cannot perform semantic search - no knowledge graph memory available")
            return []
            
        # Use LLM client from agent if available
        llm_client = getattr(self, "llm_client", None)
            
        return await self.kg_memory.semantic_query(
            query=query,
            limit=limit,
            query_expansion=query_expansion,
            llm_client=llm_client
        )
    
    async def extract_knowledge_from_text(
        self, 
        text: str, 
        extraction_mode: str = "default",
        store_text: bool = True
    ) -> List[KnowledgeTriplet]:
        """Extract knowledge triplets from text and add them to the knowledge graph.
        
        Args:
            text: The text to extract knowledge from
            extraction_mode: Mode of extraction (default, conservative, aggressive, entity-focused)
            store_text: Whether to store the original text as a document
            
        Returns:
            List of extracted triplets
        """
        if not self.kg_memory:
            self.kg_logger.warning("Cannot extract knowledge - no knowledge graph memory available")
            return []
            
        return await self.kg_memory.extract_and_store(
            text=text,
            source=getattr(self, "id", "agent"),
            extraction_mode=extraction_mode,
            store_text=store_text
        )
        
    async def extract_knowledge_with_all_modes(self, text: str) -> Dict[str, List[KnowledgeTriplet]]:
        """Extract knowledge using multiple extraction modes for better coverage.
        
        Args:
            text: The text to extract knowledge from
            
        Returns:
            Dictionary of extraction mode to list of triplets
        """
        if not self.kg_memory:
            self.kg_logger.warning("Cannot extract knowledge - no knowledge graph memory available")
            return {}
            
        return await self.kg_memory.extract_with_multiple_modes(
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
            
        return await self.kg_memory.get_entity_knowledge(entity)
    
    async def query_relevant_knowledge(self, context: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query the knowledge graph for information relevant to a given context.
        
        Args:
            context: The context to find relevant knowledge for
            limit: Maximum number of knowledge items to return
            
        Returns:
            List of relevant knowledge items
        """
        if not self.kg_memory:
            self.kg_logger.warning("Cannot query relevant knowledge - no knowledge graph memory available")
            return []
            
        # Extract key terms for more targeted search
        terms = self._extract_key_terms(context)
        
        # Use the original context if no terms found
        search_query = " ".join(terms) if terms else context
        
        return await self.kg_memory.search(
            query=search_query,
            limit=limit,
            search_type="combined"
        )
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text for better search.
        
        Args:
            text: The text to extract terms from
            
        Returns:
            List of key terms
        """
        # Simple extraction of nouns and noun phrases
        # In a real implementation, use NLP libraries for better extraction
        words = re.findall(r'\b[A-Z][a-z]+\b', text)  # Capitalized words
        phrases = re.findall(r'\b[A-Z][a-z]+ [A-Za-z]+\b', text)  # Capitalized phrases
        
        # Add any words longer than 5 characters as they might be important
        long_words = [w for w in re.findall(r'\b[a-z]{5,}\b', text.lower()) 
                      if w not in ('about', 'these', 'those', 'their', 'there', 'which', 'would')]
        
        return list(set(words + phrases + long_words))
    
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
        knowledge_items = await self.query_relevant_knowledge(message.content)
        
        if not knowledge_items:
            return message
            
        # Format knowledge for addition to message
        formatted_knowledge = []
        for item in knowledge_items:
            if item.get("type") == "triplet":
                formatted_knowledge.append(
                    f"{item.get('subject')} {item.get('predicate')} {item.get('object')}"
                )
            elif item.get("type") == "entity" and item.get("properties", {}).get("content"):
                formatted_knowledge.append(item.get("properties", {}).get("content"))
            else:
                # Format based on what's available
                parts = []
                for key in ["name", "subject", "predicate", "object", "content"]:
                    if key in item:
                        parts.append(str(item[key]))
                
                if parts:
                    formatted_knowledge.append(" ".join(parts))
        
        # Add knowledge to message metadata
        enriched_message = Message(
            role=message.role,
            content=message.content,
            additional_kwargs={
                **message.additional_kwargs,
                "knowledge_context": formatted_knowledge
            }
        )
        
        return enriched_message
    
    async def process_with_kg(self, input_message: str) -> str:
        """Process a command related to the knowledge graph.
        
        Args:
            input_message: The input message to process
            
        Returns:
            The response message
        """
        if not self.kg_memory:
            return "Knowledge graph memory is not available."
            
        # Check if this is a KG command
        if not input_message.startswith("kg:"):
            return None
            
        command = input_message[3:].strip()
        parts = command.split(" ", 1)
        cmd = parts[0].lower()
        
        if cmd == "add" and len(parts) > 1:
            # Format: add subject|predicate|object
            try:
                triplet_parts = parts[1].split("|")
                if len(triplet_parts) == 3:
                    subject, predicate, object_value = triplet_parts
                    success = await self.add_knowledge_triplet(
                        subject=subject.strip(),
                        predicate=predicate.strip(),
                        object=object_value.strip()
                    )
                    return f"Knowledge triplet added: {subject} {predicate} {object_value}" if success else "Failed to add triplet."
                else:
                    return "Invalid triplet format. Use: add subject|predicate|object"
            except Exception as e:
                return f"Error adding triplet: {str(e)}"
                
        elif cmd == "search" and len(parts) > 1:
            # Format: search query
            query_parts = parts[1].split(" --", 1)
            query = query_parts[0]
            
            # Check for flags
            include_docs = False
            limit = 5
            
            if len(query_parts) > 1:
                flags = query_parts[1]
                if "docs" in flags or "documents" in flags:
                    include_docs = True
                if "limit=" in flags:
                    try:
                        limit_str = flags[flags.find("limit=")+6:].split()[0]
                        limit = int(limit_str)
                    except:
                        pass
            
            results = await self.search_knowledge(
                query=query, 
                limit=limit, 
                include_documents=include_docs
            )
            
            if not results:
                return f"No results found for query: {query}"
                
            formatted_results = [f"Knowledge graph search results for '{query}':"]
            for i, result in enumerate(results, 1):
                if result.get("type") == "triplet":
                    formatted_results.append(
                        f"{i}. {result.get('subject')} {result.get('predicate')} {result.get('object')}"
                    )
                elif result.get("type") == "entity":
                    entity_info = [f"{i}. Entity: {result.get('name')}"]
                    if result.get("entity_type"):
                        entity_info.append(f"   Type: {result.get('entity_type')}")
                    for prop_name, prop_value in result.get("properties", {}).items():
                        if prop_name != "embedding":
                            entity_info.append(f"   {prop_name}: {prop_value}")
                    
                    # Add related documents if included
                    if include_docs and "related_documents" in result:
                        entity_info.append("   Related documents:")
                        for j, doc in enumerate(result["related_documents"][:2], 1):
                            entity_info.append(f"     {j}. {doc.get('content', '')}")
                    
                    formatted_results.append("\n".join(entity_info))
                else:
                    formatted_results.append(f"{i}. {result}")
                    
            return "\n".join(formatted_results)
            
        elif cmd == "semantic" and len(parts) > 1:
            # Format: semantic query
            query = parts[1]
            results = await self.semantic_search_knowledge(query, limit=5)
            
            if not results:
                return f"No results found for semantic query: {query}"
                
            formatted_results = [f"Semantic knowledge graph search results for '{query}':"]
            for i, result in enumerate(results, 1):
                if result.get("type") == "triplet":
                    formatted_results.append(
                        f"{i}. {result.get('subject')} {result.get('predicate')} {result.get('object')}"
                    )
                elif result.get("type") == "entity":
                    entity_info = [f"{i}. Entity: {result.get('name')}"]
                    if result.get("entity_type"):
                        entity_info.append(f"   Type: {result.get('entity_type')}")
                    for prop_name, prop_value in result.get("properties", {}).items():
                        if prop_name != "embedding":
                            entity_info.append(f"   {prop_name}: {prop_value}")
                    
                    # Add related documents if available
                    if "related_documents" in result:
                        entity_info.append("   Related documents:")
                        for j, doc in enumerate(result["related_documents"][:2], 1):
                            entity_info.append(f"     {j}. {doc.get('content', '')}")
                    
                    formatted_results.append("\n".join(entity_info))
                else:
                    formatted_results.append(f"{i}. {result}")
                    
            return "\n".join(formatted_results)
            
        elif cmd == "entity" and len(parts) > 1:
            # Format: entity name
            entity = parts[1]
            entity_info = await self.get_entity_knowledge(entity)
            
            if not entity_info or not entity_info.get("entity"):
                return f"No information found for entity: {entity}"
                
            entity_data = entity_info.get("entity", {})
            relationships = entity_info.get("relationships", [])
            
            formatted_results = [f"Information about entity '{entity}':"]
            
            # Add entity properties
            if entity_data.get("properties"):
                formatted_results.append("Properties:")
                for prop_name, prop_value in entity_data.get("properties", {}).items():
                    if prop_name != "embedding":
                        formatted_results.append(f"- {prop_name}: {prop_value}")
            
            # Add relationships
            if relationships:
                formatted_results.append("\nRelationships:")
                for rel in relationships:
                    formatted_results.append(
                        f"- {rel.get('subject')} {rel.get('predicate')} {rel.get('object')}"
                    )
                        
            return "\n".join(formatted_results)
            
        elif cmd == "extract" and len(parts) > 1:
            # Format: extract [--mode=default|aggressive|conservative|entity-focused] text
            extraction_parts = parts[1].split(" ", 1)
            mode = "default"
            text = parts[1]
            
            # Check for mode flag
            if extraction_parts[0].startswith("--mode="):
                mode_str = extraction_parts[0][7:]
                if mode_str in ["default", "aggressive", "conservative", "entity-focused"]:
                    mode = mode_str
                    text = extraction_parts[1] if len(extraction_parts) > 1 else ""
            
            if not text:
                return "Please provide text to extract knowledge from."
                
            triplets = await self.extract_knowledge_from_text(text, extraction_mode=mode)
            
            if not triplets:
                return "No knowledge triplets extracted."
                
            formatted_results = [f"Extracted {len(triplets)} knowledge triplets using {mode} mode:"]
            for i, triplet in enumerate(triplets, 1):
                formatted_results.append(
                    f"{i}. {triplet.subject} {triplet.predicate} {triplet.object} "
                    f"(confidence: {triplet.confidence:.2f})"
                )
                
            return "\n".join(formatted_results)
            
        elif cmd == "deepextract" and len(parts) > 1:
            # Format: deepextract text
            text = parts[1]
            
            if not text:
                return "Please provide text to extract knowledge from."
                
            results = await self.extract_knowledge_with_all_modes(text)
            
            if not results:
                return "No knowledge triplets extracted."
                
            formatted_results = ["Deep knowledge extraction results:"]
            
            total_triplets = 0
            for mode, triplets in results.items():
                total_triplets += len(triplets)
                if triplets:
                    formatted_results.append(f"\nMode: {mode} ({len(triplets)} triplets)")
                    # Show first 3 triplets from each mode
                    for i, triplet in enumerate(triplets[:3], 1):
                        formatted_results.append(
                            f"{i}. {triplet.subject} {triplet.predicate} {triplet.object} "
                            f"(confidence: {triplet.confidence:.2f})"
                        )
                    if len(triplets) > 3:
                        formatted_results.append(f"... and {len(triplets) - 3} more")
            
            formatted_results.insert(1, f"Total triplets extracted: {total_triplets}")
                
            return "\n".join(formatted_results)
        
        else:
            return (
                "Available knowledge graph commands:\n"
                "- kg:add subject|predicate|object - Add a knowledge triplet\n"
                "- kg:search query [--docs --limit=N] - Search the knowledge graph\n"
                "- kg:semantic query - Semantic search with query expansion\n"
                "- kg:entity name - Get information about an entity\n"
                "- kg:extract [--mode=default|aggressive|conservative|entity-focused] text - Extract knowledge\n"
                "- kg:deepextract text - Extract knowledge using multiple modes"
            )