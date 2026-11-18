"""Integration test: turn a study answer into draft flashcards."""

import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.db.repositories.conversations import ConversationRepository
from app.db.repositories.questions import QuestionRepository
from app.db.repositories.users import UserRepository
from app.quiz.cards import CardMaker, Flashcard, FlashcardSet

TEST_DB_URL = "postgresql+asyncpg://app:app@localhost:5432/app_test"


class _FakeGateway:
    async def structured(self, messages: Any, schema: Any, *, alias: str, **kw: Any) -> Any:
        return FlashcardSet(
            cards=[
                Flashcard(front="What does LoRA freeze?", back="the base weights"),
                Flashcard(front="What does LoRA train?", back="low-rank adapters"),
            ]
        )


class _FakeIndex:
    def __init__(self) -> None:
        self.upserted: list[Any] = []

    async def ensure_collection(self) -> None:
        return None

    async def upsert(self, items: Any) -> None:
        self.upserted.extend(items)


@pytest.mark.integration
async def test_from_message_creates_draft_flashcards() -> None:
    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        sm = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid.uuid4()

        async with sm() as s:
            await UserRepository(s).ensure(user_id, display_name="Tester")
            doc = Document(
                source_key="notes/lora_qlora.md",
                source_url=None,
                title="LoRA",
                licence="original",
                source_type="note",
                content_hash="h",
                kb_version=1,
            )
            s.add(doc)
            await s.flush()
            chunk = Chunk(
                document_id=doc.id,
                ordinal=0,
                section_path="",
                text="LoRA freezes base weights and trains adapters.",
                token_count=8,
                topic_ids=["ft.lora_qlora"],
                kb_version=1,
            )
            s.add(chunk)
            await s.flush()

            conv = await ConversationRepository(s).create(user_id=user_id)
            msg = await ConversationRepository(s).add_message(
                conversation_id=conv.id,
                role="assistant",
                text="LoRA freezes the base weights and trains low-rank adapters [1].",
                citations=[
                    {"n": 1, "chunk_id": str(chunk.id), "source_key": "notes/lora_qlora.md"}
                ],
            )
            await s.commit()
            message_id = msg.id

        index = _FakeIndex()
        async with sm() as s:
            ids = await CardMaker(s, _FakeGateway(), index).from_message(message_id)  # type: ignore[arg-type]
            await s.commit()
        assert len(ids) == 2
        assert len(index.upserted) == 2

        async with sm() as s:
            cards = await QuestionRepository(s).list(kind="flashcard", status="draft")
            assert len(cards) == 2
            assert all(c.topic_ids == ["ft.lora_qlora"] for c in cards)  # derived from citation
            assert all(c.answer.get("back") for c in cards)
    finally:
        await engine.dispose()
