"""Embeddings via fastembed (CPU, ONNX) — dense (bge-small) and sparse (BM25).

Models are loaded lazily and cached; the first call downloads the ONNX weights.
Document and query sides differ for BM25 (IDF is applied by Qdrant at query time),
so queries use ``query_embed``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from fastembed import SparseTextEmbedding, TextEmbedding

from app.config import get_settings


@dataclass(frozen=True)
class SparseVector:
    indices: list[int]
    values: list[float]


@lru_cache
def _dense_model() -> TextEmbedding:
    return TextEmbedding(model_name=get_settings().embed_model)


@lru_cache
def _sparse_model() -> SparseTextEmbedding:
    return SparseTextEmbedding(model_name=get_settings().sparse_model)


def embed_dense(texts: list[str]) -> list[list[float]]:
    """Dense embeddings for a batch of document texts."""
    return [vector.tolist() for vector in _dense_model().embed(texts)]


def embed_sparse(texts: list[str]) -> list[SparseVector]:
    """Sparse (BM25) embeddings for a batch of document texts."""
    return [
        SparseVector(indices=e.indices.tolist(), values=e.values.tolist())
        for e in _sparse_model().embed(texts)
    ]


def embed_query_dense(text: str) -> list[float]:
    """Dense embedding for a single query."""
    vector: list[float] = next(iter(_dense_model().query_embed(text))).tolist()
    return vector


def embed_query_sparse(text: str) -> SparseVector:
    """Sparse (BM25) embedding for a single query."""
    e = next(iter(_sparse_model().query_embed(text)))
    return SparseVector(indices=e.indices.tolist(), values=e.values.tolist())
