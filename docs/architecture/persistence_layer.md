# Symphony Persistence Layer

The Persistence Layer provides storage capabilities for Symphony components, enabling the persistence of agent configurations, tasks, and other domain models. This document outlines the key components and their interactions.

## Architecture

The Persistence Layer is built around the Repository Pattern and consists of these main components:

1. **Repository Interface**: A generic interface for CRUD operations
2. **Repository Implementations**: Concrete implementations for different storage backends
3. **Domain Models**: Pydantic models that can be persisted
4. **Service Registry**: Central access point for repositories and services

## Repository Pattern

The Repository Pattern abstracts the data storage and provides a consistent interface for working with domain models.

### Features:
- Generic typing with `Repository[T]` for type safety
- Standard CRUD operations (save, find, update, delete)
- Filtering capabilities for querying
- Asynchronous API for non-blocking operation

### Interface:
```python
class Repository(Generic[T]):
    async def save(self, entity: T) -> str:
        """Save entity and return its ID."""
        
    async def find_by_id(self, id: str) -> Optional[T]:
        """Find entity by ID."""
        
    async def find_all(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[T]:
        """Find all entities matching filter criteria."""
        
    async def update(self, entity: T) -> bool:
        """Update an entity."""
        
    async def delete(self, id: str) -> bool:
        """Delete an entity by ID."""
```

## Repository Implementations

The layer provides multiple repository implementations for different storage backends.

### InMemoryRepository

Provides in-memory storage for testing and simple applications.

```python
# Example usage
repo = InMemoryRepository(Task)
task_id = await repo.save(task)
task = await repo.find_by_id(task_id)
```

### FileSystemRepository

Provides file-based storage for persistence across application restarts.

```python
# Example usage
repo = FileSystemRepository(Task, "/path/to/storage")
task_id = await repo.save(task)
tasks = await repo.find_all({"status": TaskStatus.PENDING})
```

## Domain Models

Domain models are Pydantic models that can be persisted through repositories.

### Task

Represents a unit of work that can be executed by an agent.

```python
class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    # Additional fields...
```

### AgentConfig

Represents an agent configuration that can be stored independently.

```python
class AgentConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str = ""
    description: str = ""
    instruction_template: str
    model_config: Dict[str, Any] = Field(default_factory=dict)
    # Additional fields...
```

## Service Integration

The Persistence Layer integrates with other Symphony components through:

### AgentFactory

Creates agent instances from stored configurations.

```python
class AgentFactory:
    def __init__(self, repository: Optional[Repository[AgentConfig]] = None):
        self.repository = repository
    
    async def create_agent(self, config_id: str, **kwargs) -> Agent:
        # Implementation that loads config and creates agent
```

### TaskManager

Manages task execution with persistence.

```python
class TaskManager:
    def __init__(self, repository: Repository[Task]):
        self.repository = repository
    
    async def create_task(self, name: str, **kwargs) -> Task:
        # Implementation that creates and saves task
        
    async def execute_task(self, task_id: str, agent: Agent) -> Task:
        # Implementation that executes and updates task
```

### ServiceRegistry

Provides central access to repositories and services.

```python
class ServiceRegistry:
    @classmethod
    def get_instance(cls) -> 'ServiceRegistry':
        # Singleton implementation
        
    def register_repository(self, name: str, repository: Repository) -> None:
        # Register repository
        
    def get_repository(self, name: str) -> Repository:
        # Get repository by name
```

## Usage Examples

### Basic In-Memory Usage

```python
# Set up registry
registry = ServiceRegistry.get_instance()

# Register repositories
agent_config_repo = InMemoryRepository(AgentConfig)
task_repo = InMemoryRepository(Task)
registry.register_repository("agent_config", agent_config_repo)
registry.register_repository("task", task_repo)

# Create and persist agent config
agent_config = AgentConfig(
    name="ExampleAgent",
    role="Assistant",
    instruction_template="You are a helpful assistant named {name}."
)
config_id = await agent_config_repo.save(agent_config)

# Create and execute task
task_manager = registry.get_task_manager()
task = await task_manager.create_task(
    name="Example Task",
    input_data={"query": "What is Symphony?"}
)

# Get agent factory and create agent
agent_factory = registry.get_agent_factory()
agent = await agent_factory.create_agent(config_id)

# Execute task
result_task = await task_manager.execute_task(task.id, agent)
```

### File System Persistence

```python
# Set up data directory
data_dir = os.path.join(os.getcwd(), "symphony_data")
os.makedirs(data_dir, exist_ok=True)

# Register repositories with file system storage
agent_config_repo = FileSystemRepository(AgentConfig, data_dir)
task_repo = FileSystemRepository(Task, data_dir)
registry.register_repository("agent_config", agent_config_repo)
registry.register_repository("task", task_repo)

# Use as above, with persistence across restarts
```

## Future Extensions

The Persistence Layer is designed to be extended with:

1. **Additional Storage Backends**: Support for databases like SQLite, PostgreSQL, MongoDB
2. **Caching Layer**: Performance optimizations for frequently accessed data
3. **Migration Support**: Tools for data schema evolution
4. **Encryption**: Secure storage of sensitive information
5. **Versioning**: History tracking for domain models