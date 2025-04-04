"""Unit tests for the Symphony event system."""

import pytest
import asyncio
from unittest.mock import MagicMock

from symphony.core.events import EventBus, Event, EventType, EventCallback


class TestEvents:
    """Test suite for the event system."""
    
    def test_event_create(self):
        """Test creating an event."""
        event = Event.create(
            type=EventType.AGENT_CREATED,
            source="test",
            agent_id="agent1",
            config={"name": "TestAgent"}
        )
        
        assert event.type == EventType.AGENT_CREATED
        assert event.source == "test"
        assert event.data["agent_id"] == "agent1"
        assert event.data["config"] == {"name": "TestAgent"}
        assert isinstance(event.id, str)
        assert event.timestamp > 0
    
    def test_event_bus_subscribe_unsubscribe(self):
        """Test subscribing and unsubscribing from events."""
        bus = EventBus()
        callback = MagicMock()
        
        # Subscribe to all events
        callback_id = bus.subscribe(callback)
        
        assert isinstance(callback_id, str)
        assert len(bus._callbacks) == 1
        assert bus._callbacks[0].callback == callback
        assert bus._callbacks[0].event_type is None
        
        # Unsubscribe
        result = bus.unsubscribe(callback_id)
        assert result is True
        assert len(bus._callbacks) == 0
        
        # Try to unsubscribe again (should fail)
        result = bus.unsubscribe(callback_id)
        assert result is False
    
    def test_event_bus_filtered_subscription(self):
        """Test subscribing to specific event types."""
        bus = EventBus()
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        # Subscribe to specific event types
        bus.subscribe(callback1, EventType.AGENT_CREATED)
        bus.subscribe(callback2, EventType.AGENT_FINISHED)
        
        # Create and publish events
        event1 = Event.create(type=EventType.AGENT_CREATED, source="test")
        event2 = Event.create(type=EventType.AGENT_FINISHED, source="test")
        event3 = Event.create(type=EventType.AGENT_ERROR, source="test")
        
        bus.publish(event1)
        bus.publish(event2)
        bus.publish(event3)
        
        # Check callbacks were called correctly
        callback1.assert_called_once_with(event1)
        callback2.assert_called_once_with(event2)
        
        # Neither should be called for the error event
        assert callback1.call_count == 1
        assert callback2.call_count == 1
    
    def test_event_bus_publish(self):
        """Test publishing events."""
        bus = EventBus()
        callback = MagicMock()
        
        # Subscribe to all events
        bus.subscribe(callback)
        
        # Create and publish an event
        event = Event.create(type=EventType.TOOL_CALLED, source="test", tool="test_tool")
        bus.publish(event)
        
        # Check callback was called
        callback.assert_called_once_with(event)
    
    def test_event_callback_exception_handling(self):
        """Test that exceptions in callbacks are handled gracefully."""
        bus = EventBus()
        
        # Create a callback that raises an exception
        def bad_callback(event):
            raise ValueError("Test exception")
        
        # Subscribe the bad callback
        bus.subscribe(bad_callback)
        
        # This should not raise an exception
        event = Event.create(type=EventType.CUSTOM, source="test")
        bus.publish(event)  # Should not raise
    
    @pytest.mark.asyncio
    async def test_event_bus_async_callbacks(self):
        """Test async callbacks."""
        bus = EventBus()
        
        # Create async callbacks
        async_callback = MagicMock()
        
        # Make it behave like a coroutine function
        async def async_func(event):
            async_callback(event)
            return "async result"
        
        # Subscribe the async callback
        bus.subscribe(async_func)
        
        # Create and publish an event asynchronously
        event = Event.create(type=EventType.LLM_RESPONSE_RECEIVED, source="test")
        await bus.publish_async(event)
        
        # Check callback was called
        async_callback.assert_called_once_with(event)
    
    @pytest.mark.asyncio
    async def test_event_bus_mixed_callbacks(self):
        """Test mixing sync and async callbacks."""
        bus = EventBus()
        
        sync_callback = MagicMock()
        async_callback = MagicMock()
        
        # Create an async function
        async def async_func(event):
            async_callback(event)
            return "async result"
        
        # Subscribe both types
        bus.subscribe(sync_callback)
        bus.subscribe(async_func)
        
        # Create and publish an event asynchronously
        event = Event.create(type=EventType.ORCHESTRATION_STARTED, source="test")
        await bus.publish_async(event)
        
        # Both callbacks should be called
        sync_callback.assert_called_once_with(event)
        async_callback.assert_called_once_with(event)
        
        # Test sync publishing with async callbacks
        sync_callback.reset_mock()
        async_callback.reset_mock()
        
        event2 = Event.create(type=EventType.ORCHESTRATION_FINISHED, source="test")
        bus.publish(event2)
        
        # Sync callback should be called immediately
        sync_callback.assert_called_once_with(event2)
        
        # For the async callback in sync context, we need to allow the event loop to process it
        await asyncio.sleep(0.1)
        async_callback.assert_called_once_with(event2)