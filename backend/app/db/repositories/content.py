"""Content repository: documents + chunks SQL for the ingestion pipeline."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chunk import Chunk
from app.db.models.document import Document


@dataclass(frozen=True)
class ChunkData:
    """A chunk to persist (before it has a DB id)."""

    ordinal: int
    section_path: str
    text: str
    token_count: int


class ContentRepository:
    """All documents/chunks access. Flushes; the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_document(self, source_key: str) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.source_key == source_key)
        )
        return result.scalars().one_or_none()

    async def upsert_document(
        self,
        *,
        source_key: str,
        source_url: str | None,
        title: str,
        licence: str,
        source_type: str,
        content_hash: str,
        kb_version: int,
    ) -> Document:
        """Create the document, or update it in place if it already exists."""
        doc = await self.get_document(source_key)
        if doc is None:
            doc = Document(
                source_key=source_key,
                source_url=source_url,
                title=title,
                licence=licence,
                source_type=source_type,
                content_hash=content_hash,
                kb_version=kb_version,
            )
            self._session.add(doc)
        else:
            doc.source_url = source_url
            doc.title = title
            doc.licence = licence
            doc.source_type = source_type
            doc.content_hash = content_hash
            doc.kb_version = kb_version
        await self._session.flush()
        return doc

    async def replace_chunks(
        self,
        document_id: uuid.UUID,
        chunks: Sequence[ChunkData],
        *,
        topic_ids: list[str],
        kb_version: int,
    ) -> list[Chunk]:
        """Atomically swap a document's chunks: delete the old, insert the new."""
        await self._session.execute(delete(Chunk).where(Chunk.document_id == document_id))
        rows = [
            Chunk(
                document_id=document_id,
                ordinal=c.ordinal,
                section_path=c.section_path,
                text=c.text,
                token_count=c.token_count,
                topic_ids=list(topic_ids),
                kb_version=kb_version,
            )
            for c in chunks
        ]
        self._session.add_all(rows)
        await self._session.flush()
        return rows

    async def count_chunks(self, document_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
        )
        return int(result.scalar_one())
