import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Awaitable, TypeVar, Tuple, Type, Union
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded"""
    def __init__(self, retry_after: Optional[Union[int, float]] = None, message: str = "Rate limited"):
        super().__init__(message)
        self.retry_after = retry_after


class ServerError(Exception):
    """Raised when server returns 5xx error"""
    def __init__(self, status_code: int, body: str = ""):
        super().__init__(f"Server error {status_code}: {body[:200]}")
        self.status_code = status_code
        self.body = body


class RetryConfig:
    """
    Configuration for retry behavior.
    
    Attributes:
        max_tries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff  
        max_delay: Maximum delay in seconds (cap for backoff)
        jitter: Jitter factor (0-1) to add randomness to delays
    """
    
    def __init__(
        self, 
        max_tries: int = 5, 
        base_delay: float = 0.5, 
        max_delay: float = 60.0, 
        jitter: float = 0.3
    ) -> None:
        if max_tries < 1:
            raise ValueError("max_tries must be at least 1")
        if base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if max_delay < base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if not 0 <= jitter <= 1:
            raise ValueError("jitter must be between 0 and 1")
            
        self.max_tries = max_tries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter


def next_backoff(retry_count: int, base: float = 0.5, cap: float = 60.0, jitter: float = 0.3) -> float:
    """
    Exponential backoff with jitter, hard-capped at `cap`.
    retry_count starts at 1 for the first retry.
    Guarantees: return <= cap, return >= 0.05
    """
    # Base exponential (1 -> base, 2 -> base*2, 3 -> base*4, ...)
    base_exp = base * (2 ** max(0, retry_count - 1))
    # Symmetric jitter around the base
    j = random.uniform(-jitter, jitter) * base_exp
    delay = base_exp + j
    # Clamp after jitter so we never exceed the cap
    if delay > cap:
        delay = cap
    if delay < 0.05:
        delay = 0.05
    return delay


def retry(fn: Callable, max_tries: int = 5, retry_if: Optional[Callable[[BaseException], bool]] = None):
    """Retry a sync callable with backoff."""
    tries = 0
    while True:
        try:
            return fn()
        except BaseException as e:  # narrow via retry_if
            tries += 1
            if tries >= max_tries or (retry_if and not retry_if(e)):
                raise
            time.sleep(next_backoff(tries))


T = TypeVar("T")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    max_tries: int = 5,
    retry_if: Optional[Callable[[BaseException], bool]] = None,
) -> T:
    """Retry an async callable with backoff."""
    tries = 0
    while True:
        try:
            return await fn()
        except BaseException as e:  # narrow via retry_if
            tries += 1
            if tries >= max_tries or (retry_if and not retry_if(e)):
                raise
            await asyncio.sleep(next_backoff(tries))


# Enhanced Retry Framework for Providers
@dataclass 
class EnhancedRetryConfig:
    """Enhanced retry configuration with better provider support"""
    max_attempts: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True
    backoff_multiplier: float = 2.0
    retryable_exceptions: Tuple[Type[BaseException], ...] = (RateLimitError, ServerError)


def _calc_delay(attempt_index: int, cfg: EnhancedRetryConfig, hint: Optional[Union[int, float]] = None) -> float:
    """Compute delay for attempt_index (0-based). Respect hint (e.g., Retry-After)."""
    if hint is not None:
        try:
            return float(min(cfg.max_delay, max(0.05, hint)))
        except Exception:
            pass
    delay = cfg.base_delay * (cfg.backoff_multiplier ** attempt_index)
    if cfg.jitter:
        # +/- 30% jitter
        jitter_span = 0.3 * delay
        delay = max(0.05, min(cfg.max_delay, delay + random.uniform(-jitter_span, jitter_span)))
    else:
        delay = max(0.05, min(cfg.max_delay, delay))
    return delay


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """Decorator for retrying functions with exponential backoff"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_async(
                    lambda: func(*args, **kwargs),
                    max_tries=config.max_tries,
                    retry_if=_should_retry_http_error
                )
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return retry(
                    lambda: func(*args, **kwargs),
                    max_tries=config.max_tries,
                    retry_if=_should_retry_http_error
                )
            return sync_wrapper
    
    return decorator


# Optional helper for httpx without hard dependency
def default_httpx_retryable(statuses: Iterable[int] = (429, 500, 502, 503, 504)):
    try:
        import httpx  # type: ignore
    except Exception:
        # If httpx is not installed, everything is considered retryable by status check caller
        def _pred(_e: BaseException) -> bool:
            return True
        return _pred

    status_set = set(statuses)

    def _pred(e: BaseException) -> bool:
        if isinstance(e, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteError)):
            return True
        if isinstance(e, httpx.HTTPStatusError):
            try:
                return int(e.response.status_code) in status_set
            except Exception:
                return False
        return False

    return _pred


def _should_retry_http_error(e: BaseException) -> bool:
    """Determine if an HTTP error should trigger a retry"""
    try:
        import httpx
        if isinstance(e, httpx.HTTPStatusError):
            status = e.response.status_code
            # Retry on rate limits and server errors
            if status == 429:
                return True
            if 500 <= status <= 599:
                return True
            return False
        if isinstance(e, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteError)):
            return True
    except ImportError:
        pass
    
    # For our custom exceptions
    if isinstance(e, (RateLimitError, ServerError)):
        return True
    
    return False



def _should_retry_http_error(e: BaseException) -> bool:
    try:
        import httpx
        if isinstance(e, httpx.HTTPStatusError):
            status = e.response.status_code
            # Retry on rate limits and server errors
            if status == 429:
                return True
            if 500 <= status <= 599:
                return True
            return False
        if isinstance(e, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteError)):
            return True
    except ImportError:
        pass
    
    # For our custom exceptions
    if isinstance(e, (RateLimitError, ServerError)):
        return True
    
    return False
