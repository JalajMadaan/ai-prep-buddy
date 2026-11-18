"""Question bank + rubric models (see docs/03)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import UUIDAuditBase


class Rubric(UUIDAuditBase):
    __tablename__ = "rubrics"
    __table_args__ = (Index("ix_rubrics_name_version", "name", "version", unique=True),)

    name: Mapped[str] = mapped_column(String(128))
    version: Mapped[int] = mapped_column(Integer, default=1)
    # dimensions: [{key, description, weight}]; anchors: example answers for 1/3/5.
    dimensions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=sa_text("'[]'::jsonb")
    )
    anchors: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=sa_text("'{}'::jsonb")
    )


class Question(UUIDAuditBase):
    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_status_kind", "status", "kind"),
        Index("ix_questions_topic_ids", "topic_ids", postgresql_using="gin"),
    )

    # Stable import identity so re-importing updates rather than duplicates.
    ext_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(16))  # mcq | short | flashcard | interview
    round: Mapped[str | None] = mapped_column(String(32), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    options: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=sa_text("'[]'::jsonb")
    )
    answer: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=sa_text("'{}'::jsonb")
    )
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rubrics.id", ondelete="SET NULL"), nullable=True
    )
    topic_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    source_chunk_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), default=list)
    company_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|approved|retired
    created_by: Mapped[str] = mapped_column(String(16), default="human")  # human|generator
    generator_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
