"""Memory module for Symphony.

This module provides memory components for Symphony agents, including 
working memory, long-term memory with vector stores, and knowledge graph
integration. It also includes configurable importance assessment strategies
for intelligent memory management.
"""

# Module version
__version__ = "0.1.0"

# Core memory components
from symphony.memory.base import BaseMemory, ConversationMemory, InMemoryMemory
from symphony.memory.kg_memory import KnowledgeGraphMemory
from symphony.memory.local_kg_memory import LocalKnowledgeGraphMemory
from symphony.memory.memory_manager import (
    ConversationMemoryManager,
    MemoryManager,
    WorkingMemory
)
from symphony.memory.vector_memory import (
    ConversationVectorMemory,
    MemoryEntry,
    SimpleEmbedder,
    VectorMemory
)

# Importance assessment and strategies
from symphony.memory.importance import (
    ImportanceAssessor,
    ImportanceAssessmentStrategy,
    LLMImportanceAssessor,
    RuleBasedImportanceAssessor,
    HybridImportanceAssessor,
)
from symphony.memory.domain_strategies import (
    BaseImportanceStrategy,
    DomainSpecificStrategy,
    GeneralKnowledgeStrategy,
    AgentReflectionStrategy,
    CreativeWritingStrategy,
    TechnicalDocumentationStrategy,
)
from symphony.memory.strategy_factory import (
    ImportanceStrategyFactory,
    StrategyConfig,
)

# Explicit exports
__all__ = [
    # Base memory
    "BaseMemory",
    "ConversationMemory",
    "InMemoryMemory",
    
    # Knowledge graph memory
    "KnowledgeGraphMemory",
    "LocalKnowledgeGraphMemory",
    
    # Memory management
    "ConversationMemoryManager",
    "MemoryManager",
    "WorkingMemory",
    
    # Vector memory
    "ConversationVectorMemory",
    "MemoryEntry",
    "SimpleEmbedder",
    "VectorMemory",
    
    # Importance assessment
    "ImportanceAssessor",
    "ImportanceAssessmentStrategy",
    "LLMImportanceAssessor",
    "RuleBasedImportanceAssessor",
    "HybridImportanceAssessor",
    
    # Domain strategies
    "BaseImportanceStrategy",
    "DomainSpecificStrategy",
    "GeneralKnowledgeStrategy",
    "AgentReflectionStrategy",
    "CreativeWritingStrategy",
    "TechnicalDocumentationStrategy",
    
    # Strategy factory
    "ImportanceStrategyFactory",
    "StrategyConfig",
]

# Feature detection for optional dependencies
def has_vector_store_support() -> bool:
    """Check if vector store support is available.
    
    Returns:
        True if at least one vector store is available, False otherwise
    """
    from symphony import has_feature
    return any([
        has_feature("qdrant"),
        has_feature("chroma"),
        has_feature("weaviate"),
    ])

def has_knowledge_graph_support() -> bool:
    """Check if knowledge graph support is available.
    
    Returns:
        True if at least one knowledge graph provider is available, False otherwise
    """
    from symphony import has_feature
    return any([
        has_feature("neo4j"),
        has_feature("networkx"),
    ])