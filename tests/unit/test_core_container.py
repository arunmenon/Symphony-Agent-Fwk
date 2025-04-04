"""Unit tests for the Symphony container (dependency injection system)."""

import pytest
from unittest.mock import MagicMock

from symphony.core.container import Container
from symphony.core.exceptions import ServiceNotFoundError


class TestContainer:
    """Test suite for the Container class."""
    
    def test_init(self):
        """Test container initialization."""
        container = Container()
        assert container._services == {}
        assert container._factories == {}
        assert container._singletons == {}
    
    def test_register_get_service(self):
        """Test registering and retrieving a service."""
        container = Container()
        service = MagicMock()
        
        # Register the service
        container.register("test_service", service)
        
        # Retrieve the service
        retrieved = container.get("test_service")
        
        # Should be the same instance
        assert retrieved is service
        assert "test_service" in container._services
        assert container._singletons["test_service"] is True
    
    def test_register_non_singleton(self):
        """Test registering a non-singleton service."""
        container = Container()
        service = MagicMock()
        
        # Register as non-singleton
        container.register("test_service", service, singleton=False)
        
        # Retrieve the service
        retrieved = container.get("test_service")
        
        # Should be the same instance (because it's directly registered)
        assert retrieved is service
        assert container._singletons["test_service"] is False
    
    def test_register_factory(self):
        """Test registering and using a factory function."""
        container = Container()
        service = MagicMock()
        factory = MagicMock(return_value=service)
        
        # Register factory
        container.register_factory("test_factory", factory)
        
        # Get service from factory
        retrieved = container.get("test_factory")
        
        # Factory should be called with container
        factory.assert_called_once_with(container)
        assert retrieved is service
        
        # Since it's a singleton by default, the factory should only be called once
        retrieved_again = container.get("test_factory")
        assert factory.call_count == 1
        assert retrieved_again is service
    
    def test_register_factory_non_singleton(self):
        """Test registering a non-singleton factory function."""
        container = Container()
        service1 = MagicMock()
        service2 = MagicMock()
        factory = MagicMock(side_effect=[service1, service2])
        
        # Register factory as non-singleton
        container.register_factory("test_factory", factory, singleton=False)
        
        # Get service from factory
        retrieved1 = container.get("test_factory")
        retrieved2 = container.get("test_factory")
        
        # Factory should be called twice
        assert factory.call_count == 2
        assert retrieved1 is service1
        assert retrieved2 is service2
    
    def test_register_class(self):
        """Test registering and instantiating a class."""
        container = Container()
        
        class TestService:
            def __init__(self, param1="default", param2=None):
                self.param1 = param1
                self.param2 = param2
        
        # Register class with params
        container.register_class("test_class", TestService, param1="custom", param2=42)
        
        # Get instance
        instance = container.get("test_class")
        
        assert isinstance(instance, TestService)
        assert instance.param1 == "custom"
        assert instance.param2 == 42
        
        # Should be the same instance for singleton
        instance2 = container.get("test_class")
        assert instance2 is instance
    
    def test_has_service(self):
        """Test checking if a service is registered."""
        container = Container()
        
        # Service not registered
        assert container.has("nonexistent") is False
        
        # Register service
        container.register("test_service", MagicMock())
        assert container.has("test_service") is True
        
        # Register factory
        container.register_factory("test_factory", lambda c: MagicMock())
        assert container.has("test_factory") is True
    
    def test_service_not_found(self):
        """Test getting a non-existent service."""
        container = Container()
        
        with pytest.raises(ServiceNotFoundError) as excinfo:
            container.get("nonexistent")
        
        assert "Service not found: nonexistent" in str(excinfo.value)