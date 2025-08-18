import asyncio
import random
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Awaitable, TypeVar, Tuple, Any, Type, Union


def next_backoff(retry_count: int, base: float = 0.5, cap: float = 60.0, jitter: float = 0.3) -> float:
    """
    Exponential backoff with jitter, capped at `cap`.
    retry_count starts at 1 for the first retry.
    Guarantees: 0.05 <= delay <= cap
    """
    # Base exponential (1 -> base, 2 -> base*2, 3 -> base*4, ...)
    base_exp = base * (2 ** max(0, retry_count - 1))
    # Symmetric jitter within +/- jitter proportion
    lo = max(0.05, base_exp * (1 - jitter))
    hi = min(cap, base_exp * (1 + jitter))
    delay = random.uniform(lo, hi)
    return max(0.05, min(cap, delay))


def retry(
    fn: Callable,
    max_tries: int = 5,
    retry_if: Optional[Callable[[BaseException], bool]] = None,
    max_elapsed: Optional[float] = None,
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
):
    """Retry a sync callable with backoff.
    - retry_if(e): returns True if we should retry the given exception
    - max_elapsed: optional cap on total time spent retrying (seconds)
    - on_retry: optional hook called with (tries, exception, delay)
    """
    start = time.monotonic()
    tries = 0
    while True:
        try:
            return fn()
        except BaseException as e:  # narrow via retry_if
            tries += 1
            if tries >= max_tries or (retry_if and not retry_if(e)):
                raise
            delay = next_backoff(tries)
            if max_elapsed is not None and (time.monotonic() - start + delay) > max_elapsed:
                raise
            if on_retry:
                try:
                    on_retry(tries, e, delay)
                except Exception:
                    pass
            time.sleep(delay)


T = TypeVar("T")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    max_tries: int = 5,
    retry_if: Optional[Callable[[BaseException], bool]] = None,
    max_elapsed: Optional[float] = None,
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
) -> T:
    """Retry an async callable with backoff.
    - retry_if(e): returns True if we should retry the given exception
    - max_elapsed: optional cap on total time spent retrying (seconds)
    - on_retry: optional hook called with (tries, exception, delay)
    """
    start = time.monotonic()
    tries = 0
    while True:
        try:
            return await fn()
        except BaseException as e:  # narrow via retry_if
            tries += 1
            if tries >= max_tries or (retry_if and not retry_if(e)):
                raise
            delay = next_backoff(tries)
            if max_elapsed is not None and (time.monotonic() - start + delay) > max_elapsed:
                raise
            if on_retry:
                try:
                    on_retry(tries, e, delay)
                except Exception:
                    pass
            await asyncio.sleep(delay)


# ----- New: Retry framework expected by providers -----

class RateLimitError(Exception):
    """Raised when a 429 is encountered. May carry a retry_after seconds hint."""
    def __init__(self, retry_after: Optional[Union[int, float]] = None, message: str = "Rate limited"):
        super().__init__(message)
        self.retry_after = retry_after


class ServerError(Exception):
    """Raised for 5xx responses to trigger retry."""
    def __init__(self, status_code: int, body: str = ""):
        super().__init__(f"Server error {status_code}: {body[:200]}")
        self.status_code = status_code
        self.body = body


@dataclass
class RetryConfig:
    max_attempts: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True
    backoff_multiplier: float = 2.0
    retryable_exceptions: Tuple[Type[BaseException], ...] = (RateLimitError, ServerError)


def _calc_delay(attempt_index: int, cfg: RetryConfig, hint: Optional[Union[int, float]] = None) -> float:
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
    """
    Decorator to retry sync callables on retryable exceptions.
    Usage:
      @retry_with_backoff()            # default config
      @retry_with_backoff(RetryConfig(max_attempts=3))
    """
    cfg = config or RetryConfig()

    def _decorator(fn: Callable[..., Any]):
        def _wrapped(*args, **kwargs):
            last_exc: Optional[BaseException] = None
            for attempt in range(cfg.max_attempts):
                try:
                    return fn(*args, **kwargs)
                except BaseException as e:
                    # Only retry on configured exceptions
                    if not isinstance(e, cfg.retryable_exceptions):
                        raise
                    last_exc = e
                    # If this was the last attempt, re-raise
                    if attempt == cfg.max_attempts - 1:
                        raise
                    # Compute delay (respect RateLimitError.retry_after)
                    hint = getattr(e, "retry_after", None)
                    time.sleep(_calc_delay(attempt, cfg, hint))
            # Should not reach here
            if last_exc:
                raise last_exc
        return _wrapped
    return _decorator


# Optional helper for httpx without hard dependency
def default_httpx_retryable(statuses: Iterable[int] = (429, 500, 502, 503, 504)):
    try:
        import httpx  # type: ignore
    except Exception:
        # If httpx is not installed, be conservative: do not retry by default
        def _pred(_e: BaseException) -> bool:
            return False
        return _pred

    status_set = set(int(s) for s in statuses)

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
