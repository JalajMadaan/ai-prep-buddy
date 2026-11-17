"""Ingestion pipeline: load notes -> content-hash skip -> chunk -> atomic replace.

`make ingest` runs :func:`main`. Unchanged documents (same content hash) are
skipped; changed ones have their chunks replaced in one transaction, so a reader
never sees a half-updated document. Embedding + Qdrant upsert is added in M1-T3.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.vector_store import ChunkRecord, QdrantVectorStore, VectorStore
from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.repositories.content import ContentRepository
from app.db.session import get_sessionmaker
from app.rag.chunking import chunk_markdown
from app.rag.loader import NOTES_DIR, load_notes

logger = get_logger("rag.ingest")


@dataclass
class IngestReport:
    ingested: int = 0
    skipped: int = 0
    chunks: int = 0


def _content_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def ingest_notes(
    session: AsyncSession,
    notes_dir: Path = NOTES_DIR,
    *,
    kb_version: int | None = None,
    vector_store: VectorStore | None = None,
) -> IngestReport:
    """Ingest every note under ``notes_dir`` with content-hash skip + atomic replace.

    When a ``vector_store`` is given, each changed document's vectors are replaced
    too (delete old, upsert new), keeping Qdrant in sync with Postgres.
    """
    version = get_settings().kb_version if kb_version is None else kb_version
    repo = ContentRepository(session)
    report = IngestReport()

    if vector_store is not None:
        await vector_store.ensure_collection()

    for note in load_notes(notes_dir):
        digest = _content_hash(note.raw)
        existing = await repo.get_document(note.source_key)
        if existing is not None and existing.content_hash == digest:
            report.skipped += 1
            continue

        doc = await repo.upsert_document(
            source_key=note.source_key,
            source_url=note.source_url,
            title=note.title,
            licence=note.licence,
            source_type=note.source_type,
            content_hash=digest,
            kb_version=version,
        )
        produced = chunk_markdown(note.body)
        rows = await repo.replace_chunks(
            doc.id, produced, topic_ids=note.topic_ids, kb_version=version
        )
        if vector_store is not None:
            await vector_store.delete_document(doc.id)
            await vector_store.upsert_chunks(
                [
                    ChunkRecord(
                        id=row.id,
                        document_id=doc.id,
                        source_key=doc.source_key,
                        text=row.text,
                        title=doc.title,
                        url=doc.source_url,
                        section_path=row.section_path,
                        topic_ids=list(row.topic_ids),
                        kb_version=version,
                    )
                    for row in rows
                ]
            )
        await session.commit()
        report.ingested += 1
        report.chunks += len(rows)
        logger.info("ingested_document", source_key=note.source_key, chunks=len(rows))

    logger.info(
        "ingest_complete",
        ingested=report.ingested,
        skipped=report.skipped,
        chunks=report.chunks,
    )
    return report


async def main() -> None:
    setup_logging()
    store = QdrantVectorStore()
    async with get_sessionmaker()() as session:
        await ingest_notes(session, vector_store=store)


if __name__ == "__main__":
    asyncio.run(main())
