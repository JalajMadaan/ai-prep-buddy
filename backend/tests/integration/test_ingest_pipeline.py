"""Integration test: content-hash skip + atomic replace (requires `make up`)."""

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.models.chunk import Chunk
from app.db.repositories.content import ContentRepository
from app.rag.ingest import ingest_notes

TEST_DB_URL = "postgresql+asyncpg://app:app@localhost:5432/app_test"

NOTE_V1 = """---
title: "Ingest test"
topic_ids: [rag.chunking]
licence: original
---
# Section
Original content about chunking and retrieval.
"""

NOTE_V2 = """---
title: "Ingest test"
topic_ids: [rag.chunking]
licence: original
---
# Section
Completely rewritten content with different words so the hash changes.
"""


@pytest.mark.integration
async def test_ingest_skip_and_atomic_replace(tmp_path: Path) -> None:
    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        sm = async_sessionmaker(engine, expire_on_commit=False)

        note = tmp_path / "ingest_test.md"
        note.write_text(NOTE_V1, encoding="utf-8")

        async with sm() as s:
            r1 = await ingest_notes(s, tmp_path)
        assert r1.ingested == 1
        assert r1.skipped == 0
        assert r1.chunks >= 1

        # Unchanged -> skipped, no work.
        async with sm() as s:
            r2 = await ingest_notes(s, tmp_path)
        assert r2.ingested == 0
        assert r2.skipped == 1

        async with sm() as s:
            doc = await ContentRepository(s).get_document("notes/ingest_test.md")
            assert doc is not None
            doc_id = doc.id

        # Changed content -> atomic replace (same document, new chunks).
        note.write_text(NOTE_V2, encoding="utf-8")
        async with sm() as s:
            r3 = await ingest_notes(s, tmp_path)
        assert r3.ingested == 1
        assert r3.skipped == 0

        async with sm() as s:
            doc2 = await ContentRepository(s).get_document("notes/ingest_test.md")
            assert doc2 is not None
            assert doc2.id == doc_id  # updated in place, not duplicated
            rows = (
                (await s.execute(select(Chunk).where(Chunk.document_id == doc_id))).scalars().all()
            )
            assert rows
            assert any("rewritten" in c.text for c in rows)
            assert not any("Original content" in c.text for c in rows)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()
