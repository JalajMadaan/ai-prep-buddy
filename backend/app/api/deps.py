"""Shared API dependencies: the current authenticated principal.

In dev mode (``DEV_AUTH=true``) we return a fixed local user so the app is usable
without login. Real GitHub OAuth replaces this in M7; everything downstream reads
the user id from this principal, never from the request body.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.config import get_settings
from app.core.errors import UnauthorizedError

# Stable id for the local dev user (not a UUIDv7 — it is a fixed constant).
DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class Principal(BaseModel):
    """The authenticated caller, as the API layer sees it."""

    id: UUID
    display_name: str


def get_current_user() -> Principal:
    """Return the current principal, or raise if auth is required but absent."""
    settings = get_settings()
    if settings.dev_auth:
        return Principal(id=DEV_USER_ID, display_name="Local Dev")
    raise UnauthorizedError("Authentication required")
