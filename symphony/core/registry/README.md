# Symphony Registry System

The Registry system provides a central place to manage and access Symphony services and components. It now includes a pluggable backend architecture for different storage mechanisms:

## Overview

The key components of the refactored Registry system are:

1. **ServiceRegistry**: Central container for Symphony services and repositories
2. **StorageBackend**: Abstract interface for pluggable storage backends
3. **BackendType**: Enumeration of supported backend types
4. **StorageBackendFactory**: Factory for creating and retrieving storage backends

## Backend Types

The Registry system supports three types of backends:

1. **Vector Store**: For storing and searching embedding vectors
   - Used for similarity search and semantic retrieval
   - Supports operations like add, get, search, and delete

2. **Knowledge Graph**: For storing entities and their relationships
   - Used for structured data with relationships
   - Supports operations for entities and relations management
   - Enables traversal queries

3. **Checkpoint Store**: For saving and restoring application state
   - Used to create snapshots of the application state
   - Supports checkpoint creation, retrieval, and listing

## Backend Providers

Each backend type has multiple implementations (providers):

1. **Memory Provider**: 
   - In-memory storage (no persistence)
   - Fast but data is lost on application restart
   - Suitable for testing and development

2. **File Provider**:
   - JSON file-based storage
   - Persists data across application restarts
   - Suitable for development and small deployments

## Usage Examples

### Registering a Backend

```python
# Get registry instance
registry = ServiceRegistry.get_instance()

# Register a vector store backend
vector_store = await registry.register_backend(
    BackendType.VECTOR_STORE,
    "memory",  # Provider name
    "default",  # Backend name
    {"option": "value"}  # Optional configuration
)
```

### Using a Backend

```python
# Get a registered backend
vector_store = registry.get_backend(BackendType.VECTOR_STORE)

# Use the backend
await vector_store.add("doc1", [0.1, 0.2, 0.3], {"title": "Document 1"})
results = await vector_store.search([0.1, 0.2, 0.3], limit=10)
```

### Creating a Custom Backend Provider

```python
from symphony.core.registry.backends.vector_store.base import VectorStoreBackend
from symphony.core.registry.backends.base import BackendType, StorageBackendFactory

class MyCustomVectorStore(VectorStoreBackend):
    class Provider:
        @staticmethod
        def create_backend(config=None):
            return MyCustomVectorStore(config)
    
    # Implement required methods...

# Register custom provider
StorageBackendFactory.register_provider(
    BackendType.VECTOR_STORE, 
    "my_custom", 
    MyCustomVectorStore.Provider
)
```

## Extending the System

To add support for new storage backends:

1. Create a new implementation of the appropriate backend interface
2. Create a Provider class with a create_backend method
3. Register the provider with StorageBackendFactory
4. Use the backend through ServiceRegistry or StorageBackendFactory

This modular design allows production users to swap in specialized backends such as Redis, PostgreSQL with pgvector, Neo4j, or cloud-based solutions, without changing the rest of the Symphony codebase.