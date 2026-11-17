"""Integration test: the cross-encoder reranker orders by relevance.

Requires no infra, but downloads the MiniLM cross-encoder (~80 MB) on first run,
so it's marked integration to keep `make check` fast and offline.
"""

import uuid

import pytest

from app.rag.reranker import Reranker
from app.rag.retriever import RetrievedChunk


def _chunk(text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        score=0.0,
        text=text,
        title="",
        url=None,
        section_path="",
        topic_ids=[],
    )


@pytest.mark.integration
def test_reranker_orders_most_relevant_first() -> None:
    chunks = [
        _chunk("The Eiffel Tower is a landmark in Paris, France."),
        _chunk("QLoRA fine-tunes a 4-bit quantized model with low-rank adapters."),
        _chunk("BM25 is a sparse lexical ranking function used in search."),
    ]
    out = Reranker().rerank("Explain QLoRA fine-tuning", chunks, top_n=2)
    assert len(out) == 2
    assert "QLoRA" in out[0].text  # most relevant floated to the top
