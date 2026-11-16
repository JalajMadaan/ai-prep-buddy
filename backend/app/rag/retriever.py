"""Hybrid retriever: query dense + sparse, fuse with RRF, apply a topic filter."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.adapters.vector_store import SearchHit, VectorStore
from app.config import get_settings
from app.rag.fusion import reciprocal_rank_fusion


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    score: float
    text: str
    title: str
    url: str | None
    section_path: str
    topic_ids: list[str]


class HybridRetriever:
    """Fuse dense + sparse retrieval into a single ranked list via our RRF."""

    def __init__(self, store: VectorStore) -> None:
        self._store = store

    async def retrieve(
        self, query: str, *, top_k: int | None = None, topic_ids: list[str] | None = None
    ) -> list[RetrievedChunk]:
        limit = top_k or get_settings().retrieve_top_k
        dense = await self._store.search_dense(query, limit=limit, topic_ids=topic_ids)
        sparse = await self._store.search_sparse(query, limit=limit, topic_ids=topic_ids)

        by_id: dict[uuid.UUID, SearchHit] = {}
        for hit in (*dense, *sparse):
            by_id.setdefault(hit.chunk_id, hit)

        fused = reciprocal_rank_fusion([[h.chunk_id for h in dense], [h.chunk_id for h in sparse]])
        results: list[RetrievedChunk] = []
        for chunk_id, score in fused[:limit]:
            payload = by_id[chunk_id].payload
            results.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    score=score,
                    text=str(payload.get("text", "")),
                    title=str(payload.get("title", "")),
                    url=str(payload["url"]) if payload.get("url") else None,
                    section_path=str(payload.get("section_path", "")),
                    topic_ids=[str(t) for t in (payload.get("topic_ids") or [])],
                )
            )
        return results
