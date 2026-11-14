"""Async retry with exponential backoff and optional jitter (M0-T6).

Used by the LLM gateway to retry transient failures (429/5xx/timeout) before
falling back to the next model.

Algorithm:
1. Call and ``await fn()``; return its value on the first success.
2. Allow at most ``attempts`` total calls. After the i-th failure (i = 1, 2, ...),
   if attempts remain, sleep before the next call:
       delay = min(max_delay, base * (2 ** (i - 1)))   # exponential, capped
       if jitter: delay = random.uniform(0, delay)     # "full jitter"
   There is no sleep after the final failed attempt.
3. If every attempt fails, re-raise the exception from the last one.

Jitter spreads retries so many clients recovering from the same outage don't
resynchronise into a thundering herd the instant the provider comes back.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable


async def retry_with_backoff[T](
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    base: float,
    max_delay: float,
    jitter: bool,
) -> T:
    """Call ``fn`` with retries; see the module docstring for the exact contract.

    Args:
        fn: zero-arg async callable to run (and retry).
        attempts: maximum number of times to call ``fn`` (>= 1).
        base: base delay in seconds for the exponential backoff.
        max_delay: cap on any single delay, in seconds.
        jitter: if True, apply full jitter to each delay.

    Returns:
        The value returned by the first successful ``fn()``.

    Raises:
        Exception: the exception from the final attempt, if every attempt fails.
    """
    last_exc: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if i >= attempts:
                break
            delay = min(max_delay, base * (2 ** (i - 1)))
            if jitter:
                delay = random.uniform(0, delay)
            await asyncio.sleep(delay)

    assert last_exc is not None  # unreachable unless attempts < 1
    raise last_exc
