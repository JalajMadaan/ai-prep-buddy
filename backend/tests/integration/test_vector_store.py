"""Integration test: hybrid retrieval finds chunks by paraphrase and exact term.

Requires `make up`. First run downloads the fastembed models (~130 MB).
"""

import uuid

import pytest
from qdrant_client import AsyncQdrantClient

from app.adapters.vector_store import ChunkRecord, QdrantVectorStore
from app.config import get_settings

COLLECTION = "kb_chunks_test"


@pytest.mark.integration
async def test_hybrid_find_by_paraphrase_and_exact_term() -> None:
    client = AsyncQdrantClient(url=get_settings().qdrant_url)
    if await client.collection_exists(COLLECTION):
        await client.delete_collection(COLLECTION)

    store = QdrantVectorStore(client=client, collection=COLLECTION)
    await store.ensure_collection()

    document_id = uuid.uuid4()
    qlora = ChunkRecord(
        id=uuid.uuid4(),
        document_id=document_id,
        text="QLoRA fine-tunes a 4-bit quantized model with low-rank adapters on a single GPU.",
        title="LoRA and QLoRA",
        url=None,
        section_path="QLoRA",
        topic_ids=["ft.lora_qlora"],
        kb_version=1,
    )
    hybrid = ChunkRecord(
        id=uuid.uuid4(),
        document_id=document_id,
        text="Hybrid retrieval fuses dense embeddings with BM25 sparse scores using RRF.",
        title="Hybrid retrieval",
        url=None,
        section_path="Fusion",
        topic_ids=["ret.hybrid_fusion"],
        kb_version=1,
    )
    await store.upsert_chunks([qlora, hybrid])

    # Dense: a paraphrase with almost no shared words should still find the QLoRA chunk.
    dense = await store.search_dense(
        "efficient tuning of a compressed network using small adapter matrices", limit=5
    )
    assert qlora.id in [h.chunk_id for h in dense]

    # Sparse: an exact rare term should find the chunk that contains it.
    sparse = await store.search_sparse("BM25", limit=5)
    assert hybrid.id in [h.chunk_id for h in sparse]
    assert any("BM25" in h.payload["text"] for h in sparse)

    await client.delete_collection(COLLECTION)
