"""Skill state + event models (see docs/03).

skill_states holds per-(user, topic) mastery; skill_events is the audit trail of
every mastery change.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDAuditBase


class SkillState(Base):
    __tablename__ = "skill_states"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mastery: Mapped[float] = mapped_column(Float, default=0.5, server_default=sa_text("0.5"))
    confidence: Mapped[float] = mapped_column(Float, default=0.0, server_default=sa_text("0"))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=sa_text("0"))
    last_evidence_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SkillEvent(UUIDAuditBase):
    __tablename__ = "skill_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    topic_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(16))  # quiz | interview | study
    delta: Mapped[float] = mapped_column(Float)
    evidence_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
