"""Service locator and dependency injection container for Symphony."""

from typing import Any, Callable, Dict, Optional, Type

from symphony.core.exceptions import ServiceNotFoundError


class Container:
    """Service locator and dependency injection container."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[['Container'], Any]] = {}
        self._singletons: Dict[str, bool] = {}
    
    def register(self, name: str, service: Any, singleton: bool = True) -> None:
        """Register a service instance.
        
        Args:
            name: The name of the service
            service: The service instance
            singleton: Whether this should be treated as a singleton
        """
        self._services[name] = service
        self._singletons[name] = singleton
    
    def register_factory(
        self, 
        name: str, 
        factory: Callable[['Container'], Any], 
        singleton: bool = True
    ) -> None:
        """Register a factory function for creating a service.
        
        Args:
            name: The name of the service
            factory: Factory function that takes the container and returns a service
            singleton: Whether this should be treated as a singleton
        """
        self._factories[name] = factory
        self._singletons[name] = singleton
    
    def register_class(
        self, 
        name: str, 
        cls: Type[Any], 
        singleton: bool = True, 
        **kwargs: Any
    ) -> None:
        """Register a class for creating a service.
        
        Args:
            name: The name of the service
            cls: The class to instantiate
            singleton: Whether this should be treated as a singleton
            **kwargs: Additional arguments to pass to the constructor
        """
        def factory(container: 'Container') -> Any:
            return cls(**kwargs)
            
        self.register_factory(name, factory, singleton)
    
    def get(self, name: str) -> Any:
        """Get a service by name.
        
        Args:
            name: The name of the service
            
        Returns:
            The service instance
            
        Raises:
            ServiceNotFoundError: If the service is not registered
        """
        # If service is already created and is a singleton, return it
        if name in self._services and self._singletons.get(name, False):
            return self._services[name]
            
        # If a factory is registered, use it to create the service
        if name in self._factories:
            service = self._factories[name](self)
            
            # If it's a singleton, store it for future use
            if self._singletons.get(name, False):
                self._services[name] = service
                
            return service
            
        # If service is created but not a singleton, create a new instance
        if name in self._services:
            return self._services[name]
            
        raise ServiceNotFoundError(f"Service not found: {name}")
    
    def has(self, name: str) -> bool:
        """Check if a service is registered.
        
        Args:
            name: The name of the service
            
        Returns:
            True if the service is registered, False otherwise
        """
        return name in self._services or name in self._factories


# Global container instance
default_container = Container()