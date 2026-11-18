"""Integration test: import a bank into Postgres + Qdrant, idempotently."""

from pathlib import Path

import pytest
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.question_index import QdrantQuestionIndex
from app.config import get_settings
from app.db.models import Base
from app.db.repositories.questions import QuestionRepository
from app.quiz.bank import load_bank
from app.quiz.importer import import_bank

TEST_DB_URL = "postgresql+asyncpg://app:app@localhost:5432/app_test"
COLLECTION = "questions_test"

BANK = """
rubrics:
  - name: short_answer_default
    version: 1
    dimensions:
      - {key: correctness, description: "correct", weight: 1.0}
questions:
  - key: qi-mcq
    kind: mcq
    topic_ids: [llm.attention]
    difficulty: 2
    text: "Why scale attention scores by sqrt(d_k)?"
    options: ["dropout", "stabilise softmax"]
    answer: {correct_index: 1}
  - key: qi-short
    kind: short
    topic_ids: [ret.hybrid_fusion]
    text: "Why reciprocal rank fusion?"
    answer: {reference: "scores are on different scales; RRF uses rank"}
    rubric: short_answer_default
"""


@pytest.mark.integration
async def test_import_is_idempotent_and_indexes(tmp_path: Path) -> None:
    client = AsyncQdrantClient(url=get_settings().qdrant_url)
    if await client.collection_exists(COLLECTION):
        await client.delete_collection(COLLECTION)

    path = tmp_path / "bank.yaml"
    path.write_text(BANK, encoding="utf-8")
    bank = load_bank(path)

    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        sm = async_sessionmaker(engine, expire_on_commit=False)
        index = QdrantQuestionIndex(client=client, collection=COLLECTION)

        async with sm() as s:
            report = await import_bank(s, index, bank)
        assert report.questions == 2
        assert report.rubrics == 1

        async with sm() as s:
            approved = await QuestionRepository(s).list(status="approved")
        assert len(approved) == 2
        assert (await client.get_collection(COLLECTION)).points_count == 2

        # Re-import: idempotent (no duplicates in Postgres or Qdrant).
        async with sm() as s:
            await import_bank(s, index, bank)
            again = await QuestionRepository(s).list()
        assert len(again) == 2
        assert (await client.get_collection(COLLECTION)).points_count == 2

        # A short question is linked to its rubric.
        async with sm() as s:
            short = next(q for q in await QuestionRepository(s).list(kind="short"))
        assert short.rubric_id is not None
    finally:
        await engine.dispose()
        if await client.collection_exists(COLLECTION):
            await client.delete_collection(COLLECTION)
