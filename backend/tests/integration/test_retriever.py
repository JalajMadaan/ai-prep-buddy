"""Integration test: hybrid retriever fuses dense+sparse and respects topic filter."""

import uuid

import pytest
from qdrant_client import AsyncQdrantClient

from app.adapters.vector_store import ChunkRecord, QdrantVectorStore
from app.config import get_settings
from app.rag.retriever import HybridRetriever

COLLECTION = "kb_chunks_test"


def _record(text: str, topic: str) -> ChunkRecord:
    return ChunkRecord(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        source_key=f"notes/{topic}.md",
        text=text,
        title=topic,
        url=None,
        section_path="",
        topic_ids=[topic],
        kb_version=1,
    )


@pytest.mark.integration
async def test_retriever_fuses_and_filters_by_topic() -> None:
    client = AsyncQdrantClient(url=get_settings().qdrant_url)
    if await client.collection_exists(COLLECTION):
        await client.delete_collection(COLLECTION)
    store = QdrantVectorStore(client=client, collection=COLLECTION)
    await store.ensure_collection()

    qlora = _record(
        "QLoRA fine-tunes a 4-bit quantized model with low-rank adapters.", "ft.lora_qlora"
    )
    hybrid = _record(
        "Hybrid retrieval fuses dense embeddings with BM25 sparse scores.", "ret.hybrid_fusion"
    )
    await store.upsert_chunks([qlora, hybrid])

    retriever = HybridRetriever(store)

    hits = await retriever.retrieve("low-rank adapters for compressed models", top_k=5)
    assert hits
    assert hits[0].chunk_id == qlora.id  # most relevant, fused to the top

    filtered = await retriever.retrieve("retrieval", top_k=5, topic_ids=["ret.hybrid_fusion"])
    assert filtered
    assert all("ret.hybrid_fusion" in h.topic_ids for h in filtered)
    assert qlora.id not in [h.chunk_id for h in filtered]

    await client.delete_collection(COLLECTION)
