# Tests for retry utilities
import asyncio

from app.utils.retry import next_backoff, retry_async


def test_backoff_bounds():
    """next_backoff stays within expected bounds."""
    b1 = next_backoff(1)
    b5 = next_backoff(5)
    assert b1 >= 0.05
    assert b5 <= 60.0


def test_backoff_progression():
    """Delays generally increase as retry count grows."""
    delays = [next_backoff(i) for i in range(1, 6)]
    for d in delays:
        assert 0.05 <= d <= 60.0


def test_retry_async(monkeypatch):
    attempts = {"count": 0}

    async def fn():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("fail")
        return "ok"

    async def fake_sleep(_):
        return None

    monkeypatch.setattr("app.utils.retry.asyncio.sleep", fake_sleep)
    result = asyncio.run(retry_async(fn, max_tries=5))
    assert result == "ok"
    assert attempts["count"] == 3

