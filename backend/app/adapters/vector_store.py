"""Vector store adapter over Qdrant (hybrid: dense + sparse named vectors).

Behind a Protocol so the provider is swappable by config. The chunk's DB id is
the Qdrant point id, keeping Postgres and Qdrant in lockstep.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from qdrant_client import AsyncQdrantClient, models

from app.config import get_settings
from app.rag.embeddings import embed_dense, embed_query_dense, embed_query_sparse, embed_sparse


@dataclass(frozen=True)
class ChunkRecord:
    id: uuid.UUID
    document_id: uuid.UUID
    source_key: str
    text: str
    title: str
    url: str | None
    section_path: str
    topic_ids: list[str]
    kb_version: int


@dataclass(frozen=True)
class SearchHit:
    chunk_id: uuid.UUID
    score: float
    payload: dict[str, Any]


def _topic_filter(topic_ids: list[str] | None) -> models.Filter | None:
    if not topic_ids:
        return None
    return models.Filter(
        must=[models.FieldCondition(key="topic_ids", match=models.MatchAny(any=topic_ids))]
    )


class VectorStore(Protocol):
    async def ensure_collection(self) -> None: ...
    async def upsert_chunks(self, records: Sequence[ChunkRecord]) -> None: ...
    async def delete_document(self, document_id: uuid.UUID) -> None: ...
    async def search_dense(
        self, query: str, *, limit: int, topic_ids: list[str] | None = None
    ) -> list[SearchHit]: ...
    async def search_sparse(
        self, query: str, *, limit: int, topic_ids: list[str] | None = None
    ) -> list[SearchHit]: ...


class QdrantVectorStore:
    """Qdrant implementation: `kb_chunks` with named `dense` + `sparse` vectors."""

    def __init__(
        self, client: AsyncQdrantClient | None = None, collection: str | None = None
    ) -> None:
        s = get_settings()
        self._client = client or AsyncQdrantClient(
            url=s.qdrant_url, api_key=s.qdrant_api_key or None
        )
        self._collection = collection or s.qdrant_collection
        self._dim = s.embed_dim

    async def ensure_collection(self) -> None:
        if await self._client.collection_exists(self._collection):
            return
        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config={
                "dense": models.VectorParams(size=self._dim, distance=models.Distance.COSINE)
            },
            # Modifier.IDF: Qdrant applies BM25's IDF term at query time.
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )
        await self._client.create_payload_index(
            self._collection, field_name="topic_ids", field_schema=models.PayloadSchemaType.KEYWORD
        )
        await self._client.create_payload_index(
            self._collection, field_name="kb_version", field_schema=models.PayloadSchemaType.INTEGER
        )
        await self._client.create_payload_index(
            self._collection,
            field_name="document_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

    async def upsert_chunks(self, records: Sequence[ChunkRecord]) -> None:
        if not records:
            return
        texts = [r.text for r in records]
        dense = embed_dense(texts)
        sparse = embed_sparse(texts)
        points = [
            models.PointStruct(
                id=str(r.id),
                vector={
                    "dense": dv,
                    "sparse": models.SparseVector(indices=sv.indices, values=sv.values),
                },
                payload={
                    "chunk_id": str(r.id),
                    "document_id": str(r.document_id),
                    "source_key": r.source_key,
                    "title": r.title,
                    "url": r.url,
                    "section_path": r.section_path,
                    "topic_ids": r.topic_ids,
                    "kb_version": r.kb_version,
                    "text": r.text,
                },
            )
            for r, dv, sv in zip(records, dense, sparse, strict=True)
        ]
        await self._client.upsert(collection_name=self._collection, points=points, wait=True)

    async def delete_document(self, document_id: uuid.UUID) -> None:
        await self._client.delete(
            collection_name=self._collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id", match=models.MatchValue(value=str(document_id))
                        )
                    ]
                )
            ),
            wait=True,
        )

    async def search_dense(
        self, query: str, *, limit: int, topic_ids: list[str] | None = None
    ) -> list[SearchHit]:
        result = await self._client.query_points(
            self._collection,
            query=embed_query_dense(query),
            using="dense",
            limit=limit,
            query_filter=_topic_filter(topic_ids),
        )
        return [self._to_hit(p) for p in result.points]

    async def search_sparse(
        self, query: str, *, limit: int, topic_ids: list[str] | None = None
    ) -> list[SearchHit]:
        sv = embed_query_sparse(query)
        result = await self._client.query_points(
            self._collection,
            query=models.SparseVector(indices=sv.indices, values=sv.values),
            using="sparse",
            limit=limit,
            query_filter=_topic_filter(topic_ids),
        )
        return [self._to_hit(p) for p in result.points]

    async def search_hybrid_native(
        self, query: str, *, limit: int, topic_ids: list[str] | None = None
    ) -> list[SearchHit]:
        """Qdrant's built-in RRF fusion (for comparison with our own in M1-T4)."""
        sv = embed_query_sparse(query)
        result = await self._client.query_points(
            self._collection,
            prefetch=[
                models.Prefetch(query=embed_query_dense(query), using="dense", limit=limit),
                models.Prefetch(
                    query=models.SparseVector(indices=sv.indices, values=sv.values),
                    using="sparse",
                    limit=limit,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            query_filter=_topic_filter(topic_ids),
        )
        return [self._to_hit(p) for p in result.points]

    @staticmethod
    def _to_hit(point: models.ScoredPoint) -> SearchHit:
        payload = point.payload or {}
        chunk_id = payload.get("chunk_id", point.id)
        return SearchHit(
            chunk_id=uuid.UUID(str(chunk_id)), score=float(point.score), payload=payload
        )
