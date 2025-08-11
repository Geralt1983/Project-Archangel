import random
import time
from typing import Callable, Iterable, Optional


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