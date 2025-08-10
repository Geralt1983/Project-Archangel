"""
Simple retry test to verify basic functionality
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.retry import retry_with_backoff, RetryConfig, RateLimitError

def test_basic_retry():
    """Test basic retry functionality"""
    
    attempts = 0
    
    @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.01))
    def sometimes_fails():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RateLimitError()
        return "success"
    
    result = sometimes_fails()
    assert result == "success"
    assert attempts == 3
    print("✅ Basic retry test passed")

async def test_async_retry():
    """Test async retry"""
    
    attempts = 0
    
    @retry_with_backoff(RetryConfig(max_attempts=2, base_delay=0.01))
    async def async_function():
        nonlocal attempts  
        attempts += 1
        if attempts < 2:
            raise RateLimitError()
        return "async_success"
    
    result = await async_function()
    assert result == "async_success"
    assert attempts == 2
    print("✅ Async retry test passed")

if __name__ == "__main__":
    test_basic_retry()
    asyncio.run(test_async_retry())
    print("✅ All simple retry tests passed!")