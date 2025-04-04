"""Service registry for Symphony components.

This module provides a registry for Symphony services and components,
allowing them to be managed centrally and accessed from anywhere in
the application.
"""

from typing import Dict, Any, Optional, Type
from symphony.persistence.repository import Repository
from symphony.core.agent_config import AgentConfig
from symphony.core.task import Task
from symphony.core.agent_factory import AgentFactory
from symphony.core.task_manager import TaskManager
from symphony.execution.workflow_tracker import Workflow, WorkflowTracker
from symphony.execution.enhanced_agent import EnhancedExecutor
from symphony.execution.router import TaskRouter, RoutingStrategy

class ServiceRegistry:
    """Registry for Symphony services and components.
    
    The service registry provides a central place to manage and access
    Symphony services and components. It follows the singleton pattern
    to ensure that there is only one instance of the registry in the
    application.
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