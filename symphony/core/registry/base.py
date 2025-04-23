"""Service registry for Symphony components.

This module provides a registry for Symphony services and components,
allowing them to be managed centrally and accessed from anywhere in
the application.
"""

from typing import Dict, Any, Optional, List

from symphony.persistence.repository import Repository
from symphony.core.agent_factory import AgentFactory
from symphony.core.task_manager import TaskManager
from symphony.execution.workflow_tracker import WorkflowTracker
from symphony.execution.enhanced_agent import EnhancedExecutor
from symphony.execution.router import TaskRouter, RoutingStrategy

from symphony.core.registry.backends.base import (
    StorageBackend, 
    BackendType,
    StorageBackendFactory
)

class ServiceRegistry:
    """Registry for Symphony services and components.
    
    The service registry provides a central place to manage and access
    Symphony services and components. It follows the singleton pattern
    to ensure that there is only one instance of the registry in the
    application.
    
    The service registry now supports pluggable backends for various
    storage mechanisms:
    - Vector stores for embeddings and similarity search
    - Knowledge graphs for structured data relationships
    - Checkpoint stores for application state persistence
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'ServiceRegistry':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize service registry."""
        self.repositories: Dict[str, Repository] = {}
        self.services: Dict[str, Any] = {}
        # Each backend type maps to a dictionary of named backends
        self._backends: Dict[BackendType, Dict[str, StorageBackend]] = {
            BackendType.VECTOR_STORE: {},
            BackendType.KNOWLEDGE_GRAPH: {},
            BackendType.CHECKPOINT_STORE: {},
        }
    
    def register_repository(self, name: str, repository: Repository) -> None:
        """Register a repository.
        
        Args:
            name: Name of the repository
            repository: Repository instance
        """
        self.repositories[name] = repository
    
    def get_repository(self, name: str) -> Repository:
        """Get repository by name.
        
        Args:
            name: Name of the repository
            
        Returns:
            Repository instance
            
        Raises:
            ValueError: If repository is not registered
        """
        if name not in self.repositories:
            raise ValueError(f"Repository {name} not registered")
        return self.repositories[name]
    
    def register_service(self, name: str, service: Any) -> None:
        """Register a service.
        
        Args:
            name: Name of the service
            service: Service instance
        """
        self.services[name] = service
    
    def get_service(self, name: str) -> Any:
        """Get service by name.
        
        Args:
            name: Name of the service
            
        Returns:
            Service instance
            
        Raises:
            ValueError: If service is not registered
        """
        if name not in self.services:
            raise ValueError(f"Service {name} not registered")
        return self.services[name]
    
    # Backend management methods
    
    async def register_backend(
        self, 
        backend_type: BackendType,
        provider_name: str,
        backend_name: str = "default",
        config: Optional[Dict[str, Any]] = None
    ) -> StorageBackend:
        """Register a backend for a specific service.
        
        Creates a new backend instance using the specified provider and
        registers it with the registry.
        
        Args:
            backend_type: Type of backend (vector store, knowledge graph, etc.)
            provider_name: Name of the provider to use (e.g., "memory", "redis")
            backend_name: Name for this backend instance (default: "default")
            config: Optional configuration for the backend
            
        Returns:
            The created backend instance
            
        Raises:
            ValueError: If the provider is not registered
        """
        backend = await StorageBackendFactory.create_backend(
            backend_type, provider_name, backend_name, config
        )
        
        self._backends[backend_type][backend_name] = backend
        
        # Also register as a service for backward compatibility
        service_name = f"{backend_type.name.lower()}_{backend_name}"
        self.register_service(service_name, backend)
        
        return backend
    
    def get_backend(
        self, 
        backend_type: BackendType, 
        backend_name: str = "default"
    ) -> Optional[StorageBackend]:
        """Get a registered backend.
        
        Args:
            backend_type: Type of backend
            backend_name: Name of the backend instance
            
        Returns:
            The backend instance, or None if not found
        """
        backend = self._backends[backend_type].get(backend_name)
        if backend is None:
            backend = StorageBackendFactory.get_backend(backend_type, backend_name)
            if backend:
                self._backends[backend_type][backend_name] = backend
                
        return backend
    
    def list_backends(self, backend_type: BackendType) -> List[str]:
        """List all registered backends of a specific type.
        
        Args:
            backend_type: Type of backend
            
        Returns:
            List of backend names
        """
        return list(self._backends[backend_type].keys())
    
    # Factory methods for common services
    
    def get_agent_factory(self) -> AgentFactory:
        """Get or create agent factory.
        
        Returns:
            Agent factory instance
        """
        if "agent_factory" not in self.services:
            # Check if agent config repository exists
            agent_config_repo = self.repositories.get("agent_config")
            
            # Create and register agent factory
            agent_factory = AgentFactory(agent_config_repo)
            self.register_service("agent_factory", agent_factory)
        
        return self.services["agent_factory"]
    
    def get_task_manager(self) -> TaskManager:
        """Get or create task manager.
        
        Returns:
            Task manager instance
            
        Raises:
            ValueError: If task repository is not registered
        """
        if "task_manager" not in self.services:
            # Check if task repository exists
            task_repo = self.repositories.get("task")
            if not task_repo:
                raise ValueError("Task repository not registered")
            
            # Create and register task manager
            task_manager = TaskManager(task_repo)
            self.register_service("task_manager", task_manager)
        
        return self.services["task_manager"]
    
    def get_workflow_tracker(self) -> WorkflowTracker:
        """Get or create workflow tracker.
        
        Returns:
            Workflow tracker instance
            
        Raises:
            ValueError: If workflow or task repository is not registered
        """
        if "workflow_tracker" not in self.services:
            # Check if repositories exist
            workflow_repo = self.repositories.get("workflow")
            task_repo = self.repositories.get("task")
            
            if not workflow_repo:
                raise ValueError("Workflow repository not registered")
            if not task_repo:
                raise ValueError("Task repository not registered")
            
            # Create and register workflow tracker
            workflow_tracker = WorkflowTracker(workflow_repo, task_repo)
            self.register_service("workflow_tracker", workflow_tracker)
        
        return self.services["workflow_tracker"]
    
    def get_enhanced_executor(self) -> EnhancedExecutor:
        """Get or create enhanced executor.
        
        Returns:
            Enhanced executor instance
            
        Raises:
            ValueError: If task repository is not registered
        """
        if "enhanced_executor" not in self.services:
            # Check if task repository exists
            task_repo = self.repositories.get("task")
            if not task_repo:
                raise ValueError("Task repository not registered")
            
            # Get workflow tracker if available
            workflow_tracker = None
            try:
                workflow_tracker = self.get_workflow_tracker()
            except ValueError:
                # Workflow tracker is optional
                pass
            
            # Create and register enhanced executor
            executor = EnhancedExecutor(task_repo, workflow_tracker)
            self.register_service("enhanced_executor", executor)
        
        return self.services["enhanced_executor"]
    
    def get_task_router(self, strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_MATCH) -> TaskRouter:
        """Get or create task router.
        
        Args:
            strategy: Routing strategy to use
            
        Returns:
            Task router instance
            
        Raises:
            ValueError: If agent config repository is not registered
        """
        if "task_router" not in self.services:
            # Check if agent config repository exists
            agent_config_repo = self.repositories.get("agent_config")
            if not agent_config_repo:
                raise ValueError("Agent config repository not registered")
            
            # Create and register task router
            router = TaskRouter(agent_config_repo, strategy)
            self.register_service("task_router", router)
        
        return self.services["task_router"]
    
    async def shutdown(self) -> None:
        """Shut down the registry and all registered backends.
        
        This should be called when the application is shutting down to
        ensure clean disconnection from all backends.
        """
        # Disconnect all backends
        for backend_type in self._backends:
            for backend in self._backends[backend_type].values():
                await backend.disconnect()
        
        # Clear service registry
        self.services.clear()
        self.repositories.clear()
        
        # Clear backend registries
        for backend_type in self._backends:
            self._backends[backend_type].clear()