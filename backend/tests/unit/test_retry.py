"""Spec for the [YOU-WRITE] retry_with_backoff. These fail until it's implemented.

Run just these with:  uv run --directory backend pytest tests/unit/test_retry.py
"""

import asyncio

import pytest

from app.llm.retry import retry_with_backoff


class Boom(Exception):
    pass


async def test_returns_immediately_on_success() -> None:
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    out = await retry_with_backoff(fn, attempts=3, base=0.5, max_delay=8, jitter=False)
    assert out == "ok"
    assert calls == 1


async def test_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []

    async def fake_sleep(d: float) -> None:
        delays.append(d)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise Boom()
        return "done"

    out = await retry_with_backoff(fn, attempts=3, base=0.5, max_delay=8, jitter=False)
    assert out == "done"
    assert calls == 3
    assert delays == [0.5, 1.0]  # no sleep after the final (successful) attempt


async def test_raises_last_exception_after_exhausting(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_sleep(d: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        raise Boom()

    with pytest.raises(Boom):
        await retry_with_backoff(fn, attempts=3, base=0.5, max_delay=8, jitter=False)
    assert calls == 3


async def test_backoff_capped_by_max_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []

    async def fake_sleep(d: float) -> None:
        delays.append(d)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        if calls < 5:
            raise Boom()
        return "ok"

    await retry_with_backoff(fn, attempts=5, base=1.0, max_delay=3.0, jitter=False)
    # 1*2^0, 1*2^1, 1*2^2, 1*2^3 -> 1, 2, 4, 8 -> capped to 1, 2, 3, 3
    assert delays == [1.0, 2.0, 3.0, 3.0]


async def test_full_jitter_stays_within_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []

    async def fake_sleep(d: float) -> None:
        delays.append(d)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise Boom()
        return "ok"

    await retry_with_backoff(fn, attempts=3, base=0.5, max_delay=8, jitter=True)
    assert 0.0 <= delays[0] <= 0.5  # cap for attempt 1
    assert 0.0 <= delays[1] <= 1.0  # cap for attempt 2
