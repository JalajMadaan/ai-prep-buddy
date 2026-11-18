"""Study service: retrieve -> rerank -> abstain-or-generate -> verify citations.

Yields Server-Sent events (``meta``/``token``/``citation``/``done``). Generation
uses the gateway's non-streaming ``complete`` so citations can be verified against
the retrieved sources before anything is sent; true token streaming is a later
refinement.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, Literal

from app.adapters.vector_store import QdrantVectorStore
from app.config import get_settings
from app.llm.gateway import Gateway
from app.prompts.registry import render_prompt
from app.rag.citations import verify_citations
from app.rag.reranker import Reranker
from app.rag.retriever import HybridRetriever, RetrievedChunk

Style = Literal["concise", "interview", "deep"]
StudyEvent = tuple[str, dict[str, Any]]

# Deep answers use the strong model; concise/interview use the fast one.
_STYLE_ALIAS: dict[str, str] = {"concise": "fast", "interview": "fast", "deep": "strong"}


def _format_sources(chunks: Sequence[RetrievedChunk]) -> str:
    return "\n\n".join(f"[{i}] {c.title}: {c.text}" for i, c in enumerate(chunks, start=1))


class StudyService:
    def __init__(self, retriever: HybridRetriever, reranker: Reranker, gateway: Gateway) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._gateway = gateway

    async def ask(
        self, question: str, *, style: Style = "interview", topic_ids: list[str] | None = None
    ) -> AsyncIterator[StudyEvent]:
        settings = get_settings()
        retrieved = await self._retriever.retrieve(
            question, top_k=settings.retrieve_top_k, topic_ids=topic_ids
        )
        reranked = self._reranker.rerank(question, retrieved, top_n=settings.rerank_top_n)

        if not reranked or reranked[0].score < settings.abstain_threshold:
            nearest = sorted({t for c in reranked for t in c.topic_ids})
            yield ("meta", {"abstained": True})
            yield ("token", {"text": "This isn't covered in the knowledge base yet."})
            yield ("done", {"abstained": True, "nearest_topics": nearest})
            return

        prompt = render_prompt(
            f"study_answer/{style}", 1, question=question, sources=_format_sources(reranked)
        )
        result = await self._gateway.complete(
            [{"role": "user", "content": prompt}], alias=_STYLE_ALIAS[style]
        )
        clean, invalid = verify_citations(result.text, reranked)

        yield ("meta", {"abstained": False})
        yield ("token", {"text": clean})
        for i, chunk in enumerate(reranked, start=1):
            if f"[{i}]" in clean:
                yield (
                    "citation",
                    {
                        "n": i,
                        "chunk_id": str(chunk.chunk_id),
                        "source_key": chunk.source_key,
                        "title": chunk.title,
                        "url": chunk.url,
                    },
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
