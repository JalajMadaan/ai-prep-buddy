"""Cross-encoder reranker: reorder the fused top-N by scoring (query, chunk) pairs.

A cross-encoder reads the query and a chunk together and emits a single relevance
score — more accurate than the bi-encoder retriever, but it can't be precomputed,
so we only run it over the fused top-N. Disable via ``RERANK_ENABLED=false``.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import replace
from functools import lru_cache

from fastembed.rerank.cross_encoder import TextCrossEncoder

from app.config import get_settings
from app.core.logging import get_logger
from app.rag.retriever import RetrievedChunk

logger = get_logger("rag.reranker")


@lru_cache
def _model() -> TextCrossEncoder:
    return TextCrossEncoder(model_name=get_settings().rerank_model)


class Reranker:
    """Reorder retrieved chunks with a cross-encoder, keeping the top-N."""

    def rerank(
        self, query: str, chunks: Sequence[RetrievedChunk], *, top_n: int | None = None
    ) -> list[RetrievedChunk]:
        settings = get_settings()
        n = top_n or settings.rerank_top_n
        if not settings.rerank_enabled or not chunks:
            return list(chunks[:n])

        started = time.perf_counter()
        scores = list(_model().rerank(query, [c.text for c in chunks]))
        latency_ms = (time.perf_counter() - started) * 1000.0

        ranked = sorted(zip(chunks, scores, strict=True), key=lambda pair: pair[1], reverse=True)
        logger.info("rerank", pairs=len(chunks), top_n=n, latency_ms=round(latency_ms, 1))
        return [replace(chunk, score=float(score)) for chunk, score in ranked[:n]]
