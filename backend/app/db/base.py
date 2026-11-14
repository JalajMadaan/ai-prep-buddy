"""Declarative base and the shared columns every table gets.

All primary keys are UUIDv7 (time-ordered: good index locality on insert, still
globally unique). All timestamps are ``timestamptz`` in UTC, set by the database.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid6 import uuid7


class Base(DeclarativeBase):
    """Declarative base; ``Base.metadata`` is what Alembic targets."""


class UUIDAuditBase(Base):
    """Abstract base: a UUIDv7 primary key plus created/updated timestamps."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
