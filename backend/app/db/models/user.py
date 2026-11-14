"""User model — the system's account record (see docs/03 §Users)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import UUIDAuditBase


class User(UUIDAuditBase):
    """An account. ``github_id``/``email_hash`` are null for the dev local user.

    Personal data is never stored raw: only a hash of the email is kept.
    ``settings`` holds preferences (persona, daily quiz size, voice opt-in, ...).
    """

    __tablename__ = "users"

    github_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
