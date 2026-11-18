"""Qdrant index of questions (dense only) for near-duplicate detection (M2-T2)
and picking related questions."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from qdrant_client import AsyncQdrantClient, models

from app.adapters.vector_store import SearchHit
from app.config import get_settings
from app.rag.embeddings import embed_dense, embed_query_dense


@dataclass(frozen=True)
class QuestionVector:
    id: uuid.UUID
    text: str
    payload: dict[str, Any]


class QdrantQuestionIndex:
    def __init__(
        self, client: AsyncQdrantClient | None = None, collection: str | None = None
    ) -> None:
        s = get_settings()
        self._client = client or AsyncQdrantClient(
            url=s.qdrant_url, api_key=s.qdrant_api_key or None
        )
        self._collection = collection or "questions"
        self._dim = s.embed_dim

    async def ensure_collection(self) -> None:
        if await self._client.collection_exists(self._collection):
            return
        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config={
                "dense": models.VectorParams(size=self._dim, distance=models.Distance.COSINE)
            },
        )
        for field in ("topic_ids", "status", "kind"):
            await self._client.create_payload_index(
                self._collection, field_name=field, field_schema=models.PayloadSchemaType.KEYWORD
            )

    async def upsert(self, items: Sequence[QuestionVector]) -> None:
        if not items:
            return
        vectors = embed_dense([q.text for q in items])
        points = [
            models.PointStruct(id=str(q.id), vector={"dense": vec}, payload=q.payload)
            for q, vec in zip(items, vectors, strict=True)
        ]
        await self._client.upsert(collection_name=self._collection, points=points, wait=True)

    async def search_similar(self, text: str, *, limit: int = 5) -> list[SearchHit]:
        result = await self._client.query_points(
            self._collection, query=embed_query_dense(text), using="dense", limit=limit
        )
        hits = []
        for point in result.points:
            payload = point.payload or {}
            hits.append(
                SearchHit(
                    chunk_id=uuid.UUID(str(point.id)), score=float(point.score), payload=payload
                )
            )
        return hits
