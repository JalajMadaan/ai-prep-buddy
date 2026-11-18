"""Turn a study answer into draft flashcards for review."""

from __future__ import annotations

import hashlib
import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.question_index import QdrantQuestionIndex, QuestionVector
from app.core.errors import NotFoundError
from app.db.models.chunk import Chunk
from app.db.repositories.conversations import ConversationRepository
from app.db.repositories.questions import QuestionRepository
from app.llm.gateway import Gateway
from app.prompts.registry import render_prompt

GENERATOR_VERSION = "to_cards/v1"


class Flashcard(BaseModel):
    front: str
    back: str


class FlashcardSet(BaseModel):
    cards: list[Flashcard]


class CardMaker:
    def __init__(self, session: AsyncSession, gateway: Gateway, index: QdrantQuestionIndex) -> None:
        self._session = session
        self._gateway = gateway
        self._index = index

    async def from_message(self, message_id: uuid.UUID) -> list[uuid.UUID]:
        message = await ConversationRepository(self._session).get_message(message_id)
        if message is None or message.role != "assistant":
            raise NotFoundError(f"Assistant message {message_id} not found")

        topic_ids = await self._topics_for(message.citations)
        result = await self._gateway.structured(
            [{"role": "user", "content": render_prompt("to_cards", 1, answer=message.text_masked)}],
            FlashcardSet,
            alias="fast",
        )

        repo = QuestionRepository(self._session)
        created: list[uuid.UUID] = []
        vectors: list[QuestionVector] = []
        for card in result.cards:
            ext_key = "card_" + hashlib.sha256(card.front.encode("utf-8")).hexdigest()[:26]
            question = await repo.upsert(
                ext_key=ext_key,
                kind="flashcard",
                text=card.front,
                answer={"back": card.back},
                topic_ids=topic_ids,
                difficulty=2,
                status="draft",
                created_by="generator",
                generator_version=GENERATOR_VERSION,
            )
            created.append(question.id)
            vectors.append(
                QuestionVector(
                    id=question.id,
                    text=card.front,
                    payload={
                        "question_id": str(question.id),
                        "kind": "flashcard",
                        "topic_ids": topic_ids,
                        "status": "draft",
                    },
                )
            )

        await self._index.ensure_collection()
        await self._index.upsert(vectors)
        return created

    async def _topics_for(self, citations: list[dict[str, object]]) -> list[str]:
        chunk_ids = [uuid.UUID(str(c["chunk_id"])) for c in citations if c.get("chunk_id")]
        if not chunk_ids:
            return []
        rows = await self._session.execute(select(Chunk.topic_ids).where(Chunk.id.in_(chunk_ids)))
        topics: set[str] = set()
        for (chunk_topics,) in rows.all():
            topics.update(chunk_topics or [])
        return sorted(topics)
