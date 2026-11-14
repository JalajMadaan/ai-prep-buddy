"""Health and readiness endpoints.

``/healthz`` is liveness: the process is up. ``/readyz`` is readiness: every
backing service (Postgres, Redis, Qdrant) answers — if any is down we return 503
so a load balancer stops routing to this instance.
"""

from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, Response
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import get_settings
from app.db.session import get_engine

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness: the process is running."""
    return {"status": "ok"}


# Readiness probes must be bounded — a hanging check is worse than a failing one.
_CHECK_TIMEOUT_S = 3.0


async def _check_postgres() -> bool:
    async def ping() -> None:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(ping(), timeout=_CHECK_TIMEOUT_S)
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    client = Redis.from_url(
        get_settings().redis_url,
        socket_connect_timeout=_CHECK_TIMEOUT_S,
        socket_timeout=_CHECK_TIMEOUT_S,
    )
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()


async def _check_qdrant() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as http:
            resp = await http.get(f"{get_settings().qdrant_url}/readyz")
            return resp.status_code == 200
    except Exception:
        return False


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, object]:
    """Readiness: all backing services reachable (503 if not)."""
    postgres, redis_ok, qdrant = await asyncio.gather(
        _check_postgres(), _check_redis(), _check_qdrant()
    )
    checks = {"postgres": postgres, "redis": redis_ok, "qdrant": qdrant}
    ready = all(checks.values())
    if not ready:
        response.status_code = 503
    return {"status": "ok" if ready else "degraded", "checks": checks}
