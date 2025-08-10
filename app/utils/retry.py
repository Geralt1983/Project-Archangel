"""
Exponential backoff with jitter for reliable API calls
"""

import asyncio
import random
import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        backoff_multiplier: float = 2.0,
        retryable_exceptions: tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.backoff_multiplier = backoff_multiplier
        self.retryable_exceptions = retryable_exceptions

def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate exponential backoff delay with optional jitter"""
    # Exponential backoff: base_delay * multiplier^attempt
    delay = config.base_delay * (config.backoff_multiplier ** attempt)
    
    # Cap at max_delay
    delay = min(delay, config.max_delay)
    
    # Add jitter to prevent thundering herd
    if config.jitter:
        # Add ±25% jitter
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(0.1, delay)  # Minimum 100ms delay

def retry_with_backoff(config: Optional[RetryConfig] = None):
    """Decorator for adding exponential backoff retry to functions"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # Last attempt failed, raise the exception
                        logger.error(f"All {config.max_attempts} attempts failed for {func.__name__}: {e}")
                        raise
                    
                    # Calculate delay and wait
                    delay = calculate_delay(attempt, config)
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s")
                    
                    await asyncio.sleep(delay)
            
            # This should never be reached due to the raise above
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        logger.error(f"All {config.max_attempts} attempts failed for {func.__name__}: {e}")
                        raise
                    
                    delay = calculate_delay(attempt, config)
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s")
                    
                    time.sleep(delay)
            
            raise last_exception
        
        # Return async or sync wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Predefined retry configurations
HTTP_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=60.0,
    jitter=True,
    retryable_exceptions=(Exception,)  # Catch all for HTTP - let adapters be specific
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    jitter=True,
    retryable_exceptions=(Exception,)  # Database-specific exceptions would go here
)

WEBHOOK_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    jitter=True,
    retryable_exceptions=(Exception,)
)

class RetryableHTTPError(Exception):
    """Base class for HTTP errors that should trigger retries"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")

class RateLimitError(RetryableHTTPError):
    """429 Rate limit exceeded"""
    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(429, f"Rate limit exceeded{f', retry after {retry_after}s' if retry_after else ''}")

class ServerError(RetryableHTTPError):
    """5xx server errors"""
    pass

class CircuitBreakerError(Exception):
    """Circuit breaker is open, not attempting request"""
    pass

class CircuitBreaker:
    """Simple circuit breaker pattern for failing fast"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function through circuit breaker"""
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerError(f"Circuit breaker is OPEN, last failure {time.time() - self.last_failure_time:.1f}s ago")
        
        try:
            result = func(*args, **kwargs)
            # Success resets circuit breaker
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
            
        except self.expected_exceptions as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
            
            raise

# Usage examples and testing utilities
def create_http_retry_config(provider_name: str) -> RetryConfig:
    """Create HTTP retry config for specific provider"""
    return RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=60.0,
        jitter=True,
        retryable_exceptions=(RateLimitError, ServerError, ConnectionError, TimeoutError)
    )

async def test_retry_behavior():
    """Test function for retry behavior"""
    attempt_count = 0
    
    @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.1))
    async def failing_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise RateLimitError()
        return "success"
    
    result = await failing_function()
    assert result == "success"
    assert attempt_count == 3
    print("✅ Retry test passed")

if __name__ == "__main__":
    # Run test
    asyncio.run(test_retry_behavior())