import pytest
from app.db import seen_delivery, upsert_event

def test_idempotent_delivery():
    """Test that webhook deliveries are properly deduplicated."""
    delivery_id = "evt_test_123"
    event_data = {
        "event": "taskCreated",
        "task": {"id": "clickup_123", "name": "Test Task"}
    }
    
    # First time should not be seen
    assert not seen_delivery(delivery_id)
    
    # Store the event
    webhook_event = upsert_event(delivery_id, event_data)
    
    # Now should be seen
    assert seen_delivery(delivery_id)
    
    # Storing again should still work (upsert)
    webhook_event2 = upsert_event(delivery_id, event_data)
    
    # Should still be marked as seen
    assert seen_delivery(delivery_id)

def test_empty_delivery_id():
    """Test handling of empty delivery IDs."""
    # Empty delivery ID should not be considered seen
    assert not seen_delivery("")
    assert not seen_delivery(None)

def test_different_delivery_ids():
    """Test that different delivery IDs are tracked separately."""
    delivery_id1 = "evt_test_456"
    delivery_id2 = "evt_test_789"
    
    event_data = {"event": "taskUpdated"}
    
    # Neither should be seen initially
    assert not seen_delivery(delivery_id1)
    assert not seen_delivery(delivery_id2)
    
    # Store first event
    upsert_event(delivery_id1, event_data)
    
    # Only first should be seen
    assert seen_delivery(delivery_id1)
    assert not seen_delivery(delivery_id2)
    
    # Store second event
    upsert_event(delivery_id2, event_data)
    
    # Both should be seen
    assert seen_delivery(delivery_id1)
    assert seen_delivery(delivery_id2)

def test_webhook_event_storage():
    """Test that webhook events are properly stored with metadata."""
    delivery_id = "evt_storage_test"
    event_data = {
        "event": "taskStatusUpdated",
        "event_id": "internal_123",
        "task": {
            "id": "clickup_456",
            "status": "complete"
        }
    }
    
    webhook_event = upsert_event(delivery_id, event_data)
    
    assert webhook_event.event_type == "taskStatusUpdated"
    assert webhook_event.event_id == "internal_123"  
    assert webhook_event.delivery_id == delivery_id
    assert webhook_event.external_id == "clickup_456"
    assert webhook_event.data == event_data
    assert webhook_event.timestamp is not None