"""Document model: one ingested source (a note, doc, or paper). See docs/03."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import UUIDAuditBase


class Document(UUIDAuditBase):
    """A source document. ``source_key`` is the stable identity used for
    content-hash skip and atomic replace (the note's relative path, or a
    sources.yaml id); ``source_url`` is the external URL when there is one."""

    __tablename__ = "documents"

    source_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    licence: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(32))  # note | doc | paper
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    kb_version: Mapped[int] = mapped_column(Integer, default=1)
