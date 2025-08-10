"""
Tests for exponential backoff retry mechanism
"""

import asyncio
import time
from unittest.mock import Mock, AsyncMock
from app.utils.retry import (
    RetryConfig, 
    retry_with_backoff, 
    calculate_delay,
    RateLimitError,
    ServerError,
    CircuitBreaker
)

def test_calculate_delay():
    """Test delay calculation with exponential backoff"""
    config = RetryConfig(base_delay=1.0, backoff_multiplier=2.0, max_delay=60.0, jitter=False)
    
    # Test exponential progression
    assert calculate_delay(0, config) == 1.0  # 1.0 * 2^0
    assert calculate_delay(1, config) == 2.0  # 1.0 * 2^1
    assert calculate_delay(2, config) == 4.0  # 1.0 * 2^2
    assert calculate_delay(3, config) == 8.0  # 1.0 * 2^3
    
    # Test max_delay cap
    assert calculate_delay(10, config) == 60.0  # Should be capped

def test_calculate_delay_with_jitter():
    """Test delay calculation includes jitter"""
    config = RetryConfig(base_delay=4.0, jitter=True)
    
    delays = [calculate_delay(1, config) for _ in range(10)]
    
    # All delays should be different due to jitter
    assert len(set(delays)) > 1
    
    # All delays should be within reasonable range (base ±25%)
    for delay in delays:
        assert 6.0 <= delay <= 10.0  # 8.0 ±25%

def test_sync_retry_success_after_failure():
    """Test sync retry decorator succeeds after initial failures"""
    
    call_count = 0
    
    @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.01))
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RateLimitError()
        return "success"
    
    result = flaky_function()
    assert result == "success"
    assert call_count == 3

def test_sync_retry_max_attempts():
    """Test sync retry gives up after max attempts"""
    
    @retry_with_backoff(RetryConfig(max_attempts=2, base_delay=0.01))
    def always_failing():
        raise ServerError(500, "Server error")
    
    try:
        always_failing()
        assert False, "Should have raised ServerError"
    except ServerError:
        pass  # Expected

async def test_async_retry_success():
    """Test async retry decorator"""
    
    call_count = 0
    
    @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.01))
    async def async_flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RateLimitError()
        return "async_success"
    
    result = await async_flaky()
    assert result == "async_success" 
    assert call_count == 2

def test_retry_respects_exception_types():
    """Test retry only retries configured exception types"""
    
    @retry_with_backoff(RetryConfig(
        max_attempts=3, 
        base_delay=0.01,
        retryable_exceptions=(RateLimitError,)
    ))
    def selective_retry():
        raise ValueError("Not retryable")
    
    # ValueError should not be retried
    try:
        selective_retry()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected

def test_circuit_breaker_opens():
    """Test circuit breaker opens after failures"""
    
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
    
    def failing_func():
        raise Exception("Always fails")
    
    # First 3 calls should fail and open circuit
    for _ in range(3):
        try:
            breaker.call(failing_func)
            assert False, "Should have raised Exception"
        except Exception:
            pass  # Expected
    
    # Circuit should now be open
    assert breaker.state == "OPEN"
    
    # Next call should fail fast with CircuitBreakerError
    from app.utils.retry import CircuitBreakerError
    try:
        breaker.call(failing_func)
        assert False, "Should have raised CircuitBreakerError"
    except CircuitBreakerError:
        pass  # Expected

def test_circuit_breaker_recovery():
    """Test circuit breaker recovers after timeout"""
    
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
    
    def failing_then_succeeding():
        if hasattr(failing_then_succeeding, 'should_fail'):
            raise Exception("Fail")
        return "success"
    
    # Fail enough to open circuit
    failing_then_succeeding.should_fail = True
    for _ in range(2):
        try:
            breaker.call(failing_then_succeeding)
            assert False, "Should have raised Exception"
        except Exception:
            pass  # Expected
    
    assert breaker.state == "OPEN"
    
    # Wait for recovery timeout
    time.sleep(0.02)
    
    # Remove failure condition
    del failing_then_succeeding.should_fail
    
    # Should succeed and close circuit
    result = breaker.call(failing_then_succeeding)
    assert result == "success"
    assert breaker.state == "CLOSED"

def test_rate_limit_error():
    """Test RateLimitError includes retry_after"""
    
    error = RateLimitError(retry_after=30)
    assert error.status_code == 429
    assert error.retry_after == 30
    assert "retry after 30s" in str(error)

def test_server_error():
    """Test ServerError formatting"""
    
    error = ServerError(502, "Bad Gateway")
    assert error.status_code == 502
    assert "HTTP 502: Bad Gateway" in str(error)

if __name__ == "__main__":
    # Run tests without pytest for quick verification
    test_calculate_delay()
    test_calculate_delay_with_jitter()
    test_sync_retry_success_after_failure()
    test_sync_retry_max_attempts()
    asyncio.run(test_async_retry_success())
    test_retry_respects_exception_types()
    test_circuit_breaker_opens()
    test_circuit_breaker_recovery()
    test_rate_limit_error()
    test_server_error()
    print("✅ All retry tests passed!")