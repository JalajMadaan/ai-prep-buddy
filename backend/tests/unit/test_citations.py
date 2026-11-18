"""Tests for citation verification."""

import uuid

from app.rag.citations import verify_citations
from app.rag.retriever import RetrievedChunk


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        score=1.0,
        source_key="notes/x.md",
        text="t",
        title="T",
        url=None,
        section_path="",
        topic_ids=[],
    )


def test_strips_out_of_range_citations() -> None:
    retrieved = [_chunk(), _chunk(), _chunk()]  # valid: [1], [2], [3]
    clean, invalid = verify_citations("A [1] and [4] and [2].", retrieved)
    assert invalid == 1
    assert "[4]" not in clean
    assert "[1]" in clean
    assert "[2]" in clean


def test_no_citations_is_unchanged() -> None:
    clean, invalid = verify_citations("No citations here.", [_chunk()])
    assert invalid == 0
    assert clean == "No citations here."
