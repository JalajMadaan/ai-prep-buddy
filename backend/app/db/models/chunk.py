"""Chunk model: a retrievable slice of a document. See docs/03.

The chunk ``id`` is reused as the Qdrant point id (M1-T3), so Postgres and the
vector store stay in lockstep.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import UUIDAuditBase


class Chunk(UUIDAuditBase):
    __tablename__ = "chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    section_path: Mapped[str] = mapped_column(String(1024), default="")
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    topic_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    kb_version: Mapped[int] = mapped_column(Integer, default=1)
