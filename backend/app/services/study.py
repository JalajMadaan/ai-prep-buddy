"""Study service: retrieve -> rerank -> abstain-or-generate -> verify citations.

With a ``conversation_id`` it also loads the last 6 turns, rewrites a follow-up
into a standalone query (fast model) for retrieval, and persists both messages.
Yields Server-Sent events (``meta``/``token``/``citation``/``done``).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.vector_store import QdrantVectorStore
from app.config import get_settings
from app.db.models.conversation import Message
from app.db.repositories.conversations import ConversationRepository
from app.db.session import get_sessionmaker
from app.llm.gateway import Gateway
from app.prompts.registry import render_prompt
from app.rag.citations import verify_citations
from app.rag.reranker import Reranker
from app.rag.retriever import HybridRetriever, RetrievedChunk

Style = Literal["concise", "interview", "deep"]
StudyEvent = tuple[str, dict[str, Any]]
_STYLE_ALIAS: dict[str, str] = {"concise": "fast", "interview": "fast", "deep": "strong"}


def _format_sources(chunks: Sequence[RetrievedChunk]) -> str:
    return "\n\n".join(f"[{i}] {c.title}: {c.text}" for i, c in enumerate(chunks, start=1))


class StudyService:
    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: Reranker,
        gateway: Gateway,
        sessionmaker: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._gateway = gateway
        self._sessionmaker = sessionmaker

    def _sm(self) -> async_sessionmaker[AsyncSession]:
        return self._sessionmaker or get_sessionmaker()

    async def _recent_messages(self, conversation_id: uuid.UUID) -> list[Message]:
        async with self._sm()() as session:
            return await ConversationRepository(session).recent_messages(conversation_id, limit=6)

    async def _rewrite(self, question: str, history: list[Message]) -> str:
        hist_text = "\n".join(f"{m.role}: {m.text_masked}" for m in history)
        prompt = render_prompt("study_rewrite", 1, history=hist_text, question=question)
        result = await self._gateway.complete([{"role": "user", "content": prompt}], alias="fast")
        return result.text.strip() or question

    async def _persist(
        self,
        conversation_id: uuid.UUID,
        *,
        question: str,
        style: Style,
        answer: str,
        citations: list[dict[str, Any]],
        model: str | None,
        cost_usd: float,
        latency_ms: float,
        abstained: bool,
    ) -> None:
        async with self._sm()() as session:
            repo = ConversationRepository(session)
            await repo.add_message(
                conversation_id=conversation_id, role="user", text=question, style=style
            )
            await repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                text=answer,
                style=style,
                citations=citations,
                model=model,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                abstained=abstained,
            )
            await session.commit()

    async def ask(
        self,
        question: str,
        *,
        conversation_id: uuid.UUID | None = None,
        style: Style = "interview",
        topic_ids: list[str] | None = None,
    ) -> AsyncIterator[StudyEvent]:
        settings = get_settings()

        history = await self._recent_messages(conversation_id) if conversation_id else []
        query = await self._rewrite(question, history) if history else question

        retrieved = await self._retriever.retrieve(
            query, top_k=settings.retrieve_top_k, topic_ids=topic_ids
        )
        reranked = self._reranker.rerank(query, retrieved, top_n=settings.rerank_top_n)

        if not reranked or reranked[0].score < settings.abstain_threshold:
            nearest = sorted({t for c in reranked for t in c.topic_ids})
            answer = "This isn't covered in the knowledge base yet."
            yield ("meta", {"abstained": True})
            yield ("token", {"text": answer})
            if conversation_id:
                await self._persist(
                    conversation_id,
                    question=question,
                    style=style,
                    answer=answer,
                    citations=[],
                    model=None,
                    cost_usd=0.0,
                    latency_ms=0.0,
                    abstained=True,
                )
            yield ("done", {"abstained": True, "nearest_topics": nearest})
            return

        prompt = render_prompt(
            f"study_answer/{style}", 1, question=query, sources=_format_sources(reranked)
        )
        result = await self._gateway.complete(
            [{"role": "user", "content": prompt}], alias=_STYLE_ALIAS[style]
        )
        clean, invalid = verify_citations(result.text, reranked)

        citations: list[dict[str, Any]] = []
        for i, chunk in enumerate(reranked, start=1):
            if f"[{i}]" in clean:
                citations.append(
                    {
                        "n": i,
                        "chunk_id": str(chunk.chunk_id),
                        "source_key": chunk.source_key,
                        "title": chunk.title,
                        "url": chunk.url,
                    }
                )

        yield ("meta", {"abstained": False})
        yield ("token", {"text": clean})
        for citation in citations:
            yield ("citation", citation)
        if conversation_id:
            await self._persist(
                conversation_id,
                question=question,
                style=style,
                answer=clean,
                citations=citations,
                model=result.model,
                cost_usd=result.cost_usd,
                latency_ms=result.latency_ms,
                abstained=False,
            )
        yield (
            "done",
            {
                "cost_usd": result.cost_usd,
                "latency_ms": round(result.latency_ms, 1),
                "invalid_citations": invalid,
            },
        )


def build_study_service() -> StudyService:
    return StudyService(HybridRetriever(QdrantVectorStore()), Reranker(), Gateway())
