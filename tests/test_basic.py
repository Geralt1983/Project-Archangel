"""
Basic tests to ensure CI pipeline works
"""

from app.utils.retry import next_backoff, retry
from app.utils.outbox import OutboxOperation, make_idempotency_key


def test_next_backoff():
    """Test exponential backoff calculation"""
    # First retry should be around 0.5s
    delay1 = next_backoff(1)
    assert 0.35 <= delay1 <= 0.65  # 0.5 ± 30% jitter
    
    # Second retry should be around 1.0s
    delay2 = next_backoff(2) 
    assert 0.7 <= delay2 <= 1.3  # 1.0 ± 30% jitter
    
    # Should cap at 60s
    delay_max = next_backoff(20)
    assert delay_max <= 60.0


def test_idempotency_key():
    """Test idempotency key generation"""
    key1 = make_idempotency_key("webhook", "/api/task", {"id": 123})
    key2 = make_idempotency_key("webhook", "/api/task", {"id": 123})
    key3 = make_idempotency_key("webhook", "/api/task", {"id": 456})
    
    # Same inputs should produce same key
    assert key1 == key2
    
    # Different inputs should produce different keys
    assert key1 != key3
    
    # Keys should be SHA256 hashes (64 hex chars)
    assert len(key1) == 64
    assert all(c in '0123456789abcdef' for c in key1)


def test_outbox_operation():
    """Test OutboxOperation data class"""
    op = OutboxOperation(
        id=1,
        idempotency_key="test-key",
        operation_type="webhook", 
        endpoint="/test",
        request_body='{"test": true}',
        created_at="2025-01-01T00:00:00Z",
        attempts=0,
        next_attempt="2025-01-01T00:00:00Z"
    )
    
    assert op.id == 1
    assert op.operation_type == "webhook"
    assert op.attempts == 0


def test_retry_function():
    """Test retry decorator"""
    call_count = 0
    
    def failing_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Test error")
        return "success"
    
    # Should succeed after 3 attempts
    result = retry(failing_function, max_tries=5)
    assert result == "success"
    assert call_count == 3