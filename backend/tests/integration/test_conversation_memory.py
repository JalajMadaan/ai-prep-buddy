"""Integration test (the M1-T8 AC): a follow-up is rewritten using memory so
"what about memory?" after a LoRA question retrieves LoRA content."""

import uuid
from collections.abc import Sequence
from typing import Any

import pytest
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.vector_store import ChunkRecord, QdrantVectorStore
from app.config import get_settings
from app.db.models import Base
from app.db.repositories.conversations import ConversationRepository
from app.db.repositories.users import UserRepository
from app.rag.retriever import HybridRetriever, RetrievedChunk
from app.services.study import StudyService

TEST_DB_URL = "postgresql+asyncpg://app:app@localhost:5432/app_test"
COLLECTION = "kb_chunks_test"
LORA_KEY = "notes/lora_qlora.md"


class _PassthroughReranker:
    def rerank(
        self, query: str, chunks: Sequence[RetrievedChunk], *, top_n: int | None = None
    ) -> list[RetrievedChunk]:
        return list(chunks)[: (top_n or len(chunks))]


class _FakeResult:
    def __init__(self, text: str) -> None:
        self.text = text
        self.model = "fake"
        self.cost_usd = 0.0
        self.latency_ms = 1.0


class _FakeGateway:
    """Rewrite prompt -> a LoRA-memory query; otherwise a cited answer."""

    async def complete(self, messages: Any, *, alias: str, **kw: Any) -> _FakeResult:
        content = messages[0]["content"]
        if "standalone" in content:
            return _FakeResult("How does LoRA reduce memory usage during fine-tuning?")
        return _FakeResult(
            "LoRA freezes the base weights and trains small adapters, saving memory [1]."
        )


def _record(source_key: str, text: str) -> ChunkRecord:
    return ChunkRecord(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        source_key=source_key,
        text=text,
        title=source_key,
        url=None,
        section_path="",
        topic_ids=["ft.lora_qlora"],
        kb_version=1,
    )


async def _events(agen: Any) -> list[tuple[str, dict[str, Any]]]:
    return [e async for e in agen]


@pytest.mark.integration
async def test_followup_uses_memory_to_retrieve_lora() -> None:
    # Vector store with a LoRA chunk + a distractor.
    client = AsyncQdrantClient(url=get_settings().qdrant_url)
    if await client.collection_exists(COLLECTION):
        await client.delete_collection(COLLECTION)
    store = QdrantVectorStore(client=client, collection=COLLECTION)
    await store.ensure_collection()
    await store.upsert_chunks(
        [
            _record(
                LORA_KEY,
                "LoRA injects low-rank adapters and keeps the base frozen, cutting memory.",
            ),
            _record(
                "notes/hybrid.md", "Hybrid retrieval fuses dense and BM25 sparse scores with RRF."
            ),
        ]
    )

    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        sm = async_sessionmaker(engine, expire_on_commit=False)

        user_id = uuid.uuid4()
        async with sm() as s:
            await UserRepository(s).ensure(user_id, display_name="Tester")
            conv = await ConversationRepository(s).create(user_id=user_id)
            await s.commit()
            conv_id = conv.id

        service = StudyService(HybridRetriever(store), _PassthroughReranker(), _FakeGateway(), sm)  # type: ignore[arg-type]

        # Turn 1: establish LoRA context.
        await _events(service.ask("Explain LoRA", conversation_id=conv_id, style="interview"))

        # Turn 2: a bare follow-up — only works if memory rewrites it.
        events = await _events(service.ask("what about memory?", conversation_id=conv_id))
        citations = [data for kind, data in events if kind == "citation"]
        assert citations, "expected at least one citation"
        assert citations[0]["source_key"] == LORA_KEY

        # Both turns persisted (2 user + 2 assistant).
        async with sm() as s:
            msgs = await ConversationRepository(s).recent_messages(conv_id, limit=10)
        assert len(msgs) == 4
        assert [m.role for m in msgs] == ["user", "assistant", "user", "assistant"]
        assert msgs[2].text_masked == "what about memory?"
    finally:
        await engine.dispose()
        if await client.collection_exists(COLLECTION):
            await client.delete_collection(COLLECTION)
