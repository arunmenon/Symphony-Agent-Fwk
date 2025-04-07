# Entry Points Configuration

## Entry Points Overview

Entry points are a mechanism in Python packaging for exposing components from a package to be used by other packages. Symphony uses entry points to expose various extension points and for automatic discovery of plugins, patterns, and other components.

## Symphony Entry Points

The following entry points should be defined in `pyproject.toml`:

### 1. Plugin Entry Points

```toml
[project.entry-points."symphony.plugins"]
# Core plugins (built-in)
memory_plugins = "symphony.plugins.memory:register_plugins"
llm_plugins = "symphony.plugins.llm:register_plugins"
orchestration_plugins = "symphony.plugins.orchestration:register_plugins"
tool_plugins = "symphony.plugins.tools:register_plugins"

# Example of a third-party plugin
# my_plugin = "my_package.plugin:MyPlugin"
```

### 2. Pattern Entry Points

```toml
[project.entry-points."symphony.patterns"]
# Core patterns (built-in)
reasoning = "symphony.patterns.reasoning:register_patterns"
verification = "symphony.patterns.verification:register_patterns"
multi_agent = "symphony.patterns.multi_agent:register_patterns"
tool_usage = "symphony.patterns.tool_usage:register_patterns"
learning = "symphony.patterns.learning:register_patterns"

# Example of a third-party pattern
# my_patterns = "my_package.patterns:register_patterns"
```

### 3. Command Line Interface

```toml
[project.entry-points.console_scripts]
symphony = "symphony.cli:main"
```

### 4. Connectors

```toml
[project.entry-points."symphony.connectors"]
# Core connectors
openai = "symphony.connectors.openai:register_connector"
anthropic = "symphony.connectors.anthropic:register_connector"
vertex = "symphony.connectors.vertex:register_connector"

# Example of a third-party connector
# my_connector = "my_package.connectors:register_connector"
```

### 5. Vector Stores

```toml
[project.entry-points."symphony.vector_stores"]
# Core vector stores
qdrant = "symphony.vector_stores.qdrant:register_vector_store"
chroma = "symphony.vector_stores.chroma:register_vector_store"
weaviate = "symphony.vector_stores.weaviate:register_vector_store"

# Example of a third-party vector store
# my_vector_store = "my_package.vector_stores:register_vector_store"
```

### 6. Knowledge Graph Providers

```toml
[project.entry-points."symphony.kg_providers"]
# Core knowledge graph providers
neo4j = "symphony.kg_providers.neo4j:register_kg_provider"
networkx = "symphony.kg_providers.networkx:register_kg_provider"

# Example of a third-party knowledge graph provider
# my_kg_provider = "my_package.kg_providers:register_kg_provider"
```

### 7. Orchestrators

```toml
[project.entry-points."symphony.orchestrators"]
# Core orchestrators
dag = "symphony.orchestrators.dag:register_orchestrator"
sequential = "symphony.orchestrators.sequential:register_orchestrator"
parallel = "symphony.orchestrators.parallel:register_orchestrator"

# Example of a third-party orchestrator
# my_orchestrator = "my_package.orchestrators:register_orchestrator"
```

## Entry Point Discovery Process

Symphony discovers and loads entry points using the following process:

1. At startup, Symphony queries all entry points in the specified groups
2. Each entry point is loaded and initialized
3. Components register themselves with the appropriate registry
4. The components become available through the Symphony API

## Creating Custom Entry Points

Third-party packages can define their own entry points to extend Symphony. To create a custom entry point:

1. Define a class that implements the appropriate interface:
   - For plugins: Subclass `symphony.core.plugin.Plugin`
   - For patterns: Implement pattern registration function
   - For connectors: Implement connector registration function
   - etc.

2. Add the entry point to your package's `pyproject.toml`:
   ```toml
   [project.entry-points."symphony.plugins"]
   my_plugin = "my_package.plugin:MyPlugin"
   ```

3. When your package is installed, Symphony will automatically discover and load your extension.

## Testing Entry Points

You can test your entry points using the Symphony CLI:

```bash
# List all discovered plugins
symphony plugin list

# Get information about a specific plugin
symphony plugin info my_plugin
```