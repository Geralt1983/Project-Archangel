"""
Tests for outbox pattern implementation
"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock
from app.utils.outbox import (
    OutboxOperation, 
    OutboxManager, 
    OutboxStatus,
    OutboxProcessor,
    create_task_operation,
    update_task_operation
)

def create_test_db():
    """Create in-memory SQLite for testing"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def test_outbox_operation_creation():
    """Test OutboxOperation creation and serialization"""
    
    operation = OutboxOperation(
        operation_type="create_task",
        provider="clickup", 
        endpoint="/tasks",
        payload={"title": "Test Task", "description": "Test"},
        max_retries=3
    )
    
    assert operation.operation_type == "create_task"
    assert operation.provider == "clickup"
    assert operation.status == OutboxStatus.PENDING
    assert operation.retry_count == 0
    assert operation.max_retries == 3
    assert operation.idempotency_key is not None
    
    # Test serialization roundtrip
    data = operation.to_dict()
    restored = OutboxOperation.from_dict(data)
    
    assert restored.id == operation.id
    assert restored.idempotency_key == operation.idempotency_key
    assert restored.status == operation.status

def test_idempotency_key_generation():
    """Test idempotency keys are consistent and unique"""
    
    # Same payload should generate same key
    payload = {"title": "Test", "id": "123"}
    
    op1 = OutboxOperation("create_task", "clickup", "/tasks", payload)
    op2 = OutboxOperation("create_task", "clickup", "/tasks", payload)
    
    assert op1.idempotency_key == op2.idempotency_key
    
    # Different payload should generate different key
    op3 = OutboxOperation("create_task", "clickup", "/tasks", {"title": "Different"})
    assert op1.idempotency_key != op3.idempotency_key

def test_outbox_manager_initialization():
    """Test OutboxManager initializes schema correctly"""
    
    conn = create_test_db()
    manager = OutboxManager(lambda: conn)
    
    # Check table was created
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='outbox_operations'")
    assert cursor.fetchone() is not None

def test_add_operation():
    """Test adding operations to outbox"""
    
    conn = create_test_db()
    manager = OutboxManager(lambda: conn)
    
    operation = manager.add_operation(
        operation_type="create_task",
        provider="clickup",
        endpoint="/tasks", 
        payload={"title": "Test Task"},
        max_retries=5
    )
    
    assert operation.id is not None
    assert operation.status == OutboxStatus.PENDING
    
    # Verify stored in database
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM outbox_operations")
    count = cursor.fetchone()[0]
    assert count == 1

def test_idempotency_enforcement():
    """Test idempotency prevents duplicate operations"""
    
    conn = create_test_db() 
    manager = OutboxManager(lambda: conn)
    
    payload = {"title": "Test Task", "id": "123"}
    
    # Add same operation twice
    op1 = manager.add_operation("create_task", "clickup", "/tasks", payload)
    op2 = manager.add_operation("create_task", "clickup", "/tasks", payload)
    
    # Should return existing operation
    assert op1.idempotency_key == op2.idempotency_key
    
    # Only one record in database
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM outbox_operations")
    count = cursor.fetchone()[0]
    assert count == 1

def test_get_pending_operations():
    """Test retrieving pending operations"""
    
    conn = create_test_db()
    manager = OutboxManager(lambda: conn)
    
    # Add pending operation
    manager.add_operation("create_task", "clickup", "/tasks", {"title": "Task 1"})
    
    # Add failed operation ready for retry
    failed_op = manager.add_operation("update_task", "clickup", "/tasks/123", {"status": "done"})
    manager.mark_failed(failed_op.id, "Temporary failure")
    
    pending = manager.get_pending_operations()
    assert len(pending) == 2

def test_mark_operations():
    """Test marking operations with different statuses"""
    
    conn = create_test_db()
    manager = OutboxManager(lambda: conn)
    
    operation = manager.add_operation("create_task", "clickup", "/tasks", {"title": "Test"})
    
    # Test mark processing
    success = manager.mark_processing(operation.id)
    assert success
    
    # Test mark completed
    success = manager.mark_completed(operation.id)
    assert success
    
    # Verify status in database
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM outbox_operations WHERE id = ?", (operation.id,))
    status = cursor.fetchone()[0]
    assert status == "completed"

def test_mark_failed_with_retry():
    """Test marking failed operations schedules retry"""
    
    conn = create_test_db()
    manager = OutboxManager(lambda: conn)
    
    operation = manager.add_operation("create_task", "clickup", "/tasks", {"title": "Test"}, max_retries=3)
    
    # Mark failed first time
    success = manager.mark_failed(operation.id, "Network error", retry_delay_seconds=30)
    assert success
    
    # Check retry is scheduled
    cursor = conn.cursor()
    cursor.execute("SELECT retry_count, next_retry_at FROM outbox_operations WHERE id = ?", (operation.id,))
    row = cursor.fetchone()
    assert row[0] == 1  # retry_count incremented
    assert row[1] is not None  # next_retry_at set

def test_mark_failed_max_retries():
    """Test operation marked as permanently failed after max retries"""
    
    conn = create_test_db()
    manager = OutboxManager(lambda: conn)
    
    operation = manager.add_operation("create_task", "clickup", "/tasks", {"title": "Test"}, max_retries=2)
    
    # Fail twice to reach max retries
    manager.mark_failed(operation.id, "Error 1")
    manager.mark_failed(operation.id, "Error 2")
    
    # Check no more retries scheduled
    cursor = conn.cursor()
    cursor.execute("SELECT retry_count, next_retry_at, status FROM outbox_operations WHERE id = ?", (operation.id,))
    row = cursor.fetchone()
    assert row[0] == 2  # Max retry count reached
    assert row[1] is None  # No next retry scheduled
    assert row[2] == "failed"  # Still marked as failed

def test_cleanup_completed():
    """Test cleanup of old completed operations"""
    
    conn = create_test_db()
    manager = OutboxManager(lambda: conn)
    
    # Add completed operation
    operation = manager.add_operation("create_task", "clickup", "/tasks", {"title": "Old Task"})
    manager.mark_completed(operation.id)
    
    # Manually set old timestamp
    old_time = datetime.now(timezone.utc) - timedelta(days=10)
    cursor = conn.cursor()
    cursor.execute("UPDATE outbox_operations SET updated_at = ? WHERE id = ?", (old_time, operation.id))
    
    # Cleanup operations older than 5 days
    cleaned = manager.cleanup_completed(older_than_days=5)
    assert cleaned == 1
    
    # Verify operation was deleted
    cursor.execute("SELECT COUNT(*) FROM outbox_operations WHERE id = ?", (operation.id,))
    assert cursor.fetchone()[0] == 0

def test_get_stats():
    """Test outbox statistics"""
    
    conn = create_test_db()
    manager = OutboxManager(lambda: conn)
    
    # Add operations with different statuses
    op1 = manager.add_operation("create_task", "clickup", "/tasks", {"title": "Task 1"})
    op2 = manager.add_operation("create_task", "clickup", "/tasks", {"title": "Task 2"})
    
    manager.mark_completed(op1.id)
    manager.mark_failed(op2.id, "Error")
    
    stats = manager.get_stats()
    assert stats.get("completed", 0) == 1
    assert stats.get("failed", 0) == 1

async def test_outbox_processor():
    """Test OutboxProcessor processes operations"""
    
    conn = create_test_db()
    manager = OutboxManager(lambda: conn)
    
    # Mock provider
    mock_provider = Mock()
    mock_provider.create_task_from_payload = AsyncMock()
    
    provider_registry = {"clickup": mock_provider}
    processor = OutboxProcessor(manager, provider_registry)
    
    # Add operation
    manager.add_operation("create_task", "clickup", "/tasks", {"title": "Test Task"})
    
    # Process operations
    stats = await processor.process_pending(batch_size=10)
    
    assert stats["processed"] == 1
    assert stats["completed"] == 1
    
    # Verify provider was called
    mock_provider.create_task_from_payload.assert_called_once()

def test_helper_functions():
    """Test helper functions for common operations"""
    
    conn = create_test_db()
    manager = OutboxManager(lambda: conn)
    
    # Test create task operation
    task_data = {"id": "task_123", "title": "Helper Test"}
    operation = create_task_operation("clickup", task_data, manager)
    
    assert operation.operation_type == "create_task"
    assert operation.provider == "clickup"
    assert operation.payload == task_data
    
    # Test update task operation  
    updates = {"status": "completed"}
    operation = update_task_operation("clickup", "task_123", updates, manager)
    
    assert operation.operation_type == "update_task"
    assert operation.payload["task_id"] == "task_123"
    assert operation.payload["updates"] == updates

if __name__ == "__main__":
    # Run tests without pytest for quick verification
    test_outbox_operation_creation()
    test_idempotency_key_generation()
    test_outbox_manager_initialization()
    test_add_operation()
    test_idempotency_enforcement()
    test_get_pending_operations()
    test_mark_operations()
    test_mark_failed_with_retry()
    test_mark_failed_max_retries()
    test_cleanup_completed()
    test_get_stats()
    test_helper_functions()
    print("✅ All outbox tests passed!")