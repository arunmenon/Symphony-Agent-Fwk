# Symphony State Management

Symphony provides a state management system that enables checkpointing and resumption of long-running workflows, agents, and tasks. This document explains how to use this system to add resilience to your Symphony applications.

## Overview

The state management system:

- Allows creating checkpoints of the entire Symphony state
- Supports resuming Symphony from a previous checkpoint
- Automatically checkpoints during workflow execution
- Provides a clean, simple API for developers

## Basic Usage

### Enabling State Persistence

To enable state management, initialize Symphony with the `persistence_enabled` flag:

```python
from symphony import Symphony

# Enable state persistence
symphony = Symphony(persistence_enabled=True)

# Set up Symphony with a custom state directory
await symphony.setup(state_dir="/path/to/state")
```

### Creating Checkpoints

Create checkpoints manually at important stages of your application:

```python
# Create a named checkpoint
checkpoint_id = await symphony.create_checkpoint("after_planning_phase")
print(f"Created checkpoint: {checkpoint_id}")
```

### Resuming from Checkpoints

Resume execution from a previous checkpoint:

```python
# Resume from a specific checkpoint
await symphony.resume_from_checkpoint(checkpoint_id)

# Or resume from the latest checkpoint
latest_checkpoint_id = await symphony.resume_latest_checkpoint()
if latest_checkpoint_id:
    print(f"Resumed from checkpoint: {latest_checkpoint_id}")
else:
    print("No checkpoints available")
```

### Managing Checkpoints

List and delete checkpoints:

```python
# List all checkpoints
checkpoints = await symphony.list_checkpoints()
for cp in checkpoints:
    print(f"{cp['id']} ({cp['name']}): created at {cp['created_at']}")

# Delete a checkpoint
await symphony.delete_checkpoint(checkpoint_id)
```

## Automatic Checkpointing

Symphony can automatically create checkpoints during workflow execution:

```python
# Execute a workflow with automatic checkpointing
workflow_result = await symphony.workflows.execute_workflow_by_id(workflow_id)
```

Checkpoints are automatically created:
- At the start of the workflow
- After every few steps (configurable)
- When errors occur
- At workflow completion

## Architecture

The state management system consists of:

1. **State Serialization**: Encodes Symphony entities into a portable format
2. **Storage Provider**: Persists state data with transactional guarantees 
3. **Checkpoint Manager**: Creates and restores consistent checkpoints
4. **Symphony API Integration**: Provides a clean interface for developers

## Advanced Configuration

### Storage Location

Configure where state data is stored:

```python
# Custom state directory
await symphony.setup(state_dir="/custom/state/directory")
```

### Disabling Automatic Checkpoints

Control automatic checkpointing in workflows:

```python
# Execute workflow without automatic checkpointing
workflow_engine = symphony.registry.get("workflow_engine")
await workflow_engine.execute_workflow(workflow_def, auto_checkpoint=False)
```

## Examples

See the following examples for practical use cases:

- `examples/state_management_example.py`: Basic state management
- `examples/workflow_state_management_example.py`: Automatic workflow checkpointing

## State Restoration Architecture

The Symphony state restoration system uses a factory approach to reconstruct entities from serialized state:

### Two-Phase Restoration

Restoration happens in two phases to handle circular references between entities:

1. **Creation Phase**: Creates all entities with basic properties
   ```
   ┌─────────────┐     ┌──────────────┐    ┌─────────────┐
   │ Checkpoint  │────▶│ Entity State │───▶│  Restorers  │
   │  Manifest   │     │   Bundles    │    │ (by type)   │
   └─────────────┘     └──────────────┘    └─────────────┘
                                                  │
                                                  ▼
                                           ┌─────────────┐
                                           │   Created   │
                                           │  Entities   │
                                           └─────────────┘
   ```

2. **Connection Phase**: Resolves references between entities
   ```
   ┌─────────────┐     ┌──────────────┐    ┌─────────────┐
   │  Pending    │────▶│  Reference   │───▶│ Connected   │
   │ References  │     │ Resolution   │    │  Entities   │
   └─────────────┘     └──────────────┘    └─────────────┘
   ```

### Entity-Specific Restorers

Each entity type has a specialized restorer that knows how to recreate the entity:

```python
class AgentRestorer(EntityRestorer):
    """Restorer for Agent entities."""
    
    @property
    def entity_type(self) -> str:
        return "Agent"
    
    async def restore(self, entity_id: str, data: Dict[str, Any], context: RestorationContext) -> Any:
        # Use Symphony's existing agent creation facilities
        agent_config = data.get("config", {})
        agent = await context.symphony.agents.create_agent(agent_config)
        
        # Restore entity-specific state
        if "interaction_history" in data and hasattr(agent, "_interaction_history"):
            agent._interaction_history = data["interaction_history"]
            
        return agent
```

This approach ensures we don't need to modify core entity classes, keeping the code clean.

## Extending State Management

### Custom Entity Restoration

To support custom entities, you can register a custom restorer:

```python
from symphony.core.state import EntityRestorer, RestorationContext

class CustomEntityRestorer(EntityRestorer):
    @property
    def entity_type(self) -> str:
        return "CustomEntity"
    
    async def restore(self, entity_id: str, data: Dict[str, Any], context: RestorationContext) -> Any:
        # Create your custom entity
        custom_entity = CustomEntity(**data)
        return custom_entity

# Register with restore manager
from symphony.core.state.restore import restore_manager
restore_manager.register_restorer(CustomEntityRestorer())
```

### Limitations

- External resources (like API clients) need reconnection logic
- Some complex entity relationships may require manual restoration
- Custom agent state may need specialized restoration logic