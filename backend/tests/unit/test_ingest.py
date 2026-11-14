"""Unit tests for loading + chunking (no DB)."""

from pathlib import Path

from app.rag.chunking import chunk_markdown
from app.rag.loader import load_notes, parse_front_matter

NOTE = """---
title: "Test note"
topic_ids: [llm.attention, rag.chunking]
licence: original
---
# Heading one

Some content about attention and vectors.

## Heading two

More content in a second section with enough words to form a chunk.
"""


def test_parse_front_matter() -> None:
    meta, body = parse_front_matter(NOTE)
    assert meta["title"] == "Test note"
    assert meta["topic_ids"] == ["llm.attention", "rag.chunking"]
    assert body.startswith("# Heading one")


def test_load_notes(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text(NOTE, encoding="utf-8")
    notes = load_notes(tmp_path)
    assert len(notes) == 1
    note = notes[0]
    assert note.source_key == "notes/a.md"
    assert note.title == "Test note"
    assert note.topic_ids == ["llm.attention", "rag.chunking"]
    assert note.licence == "original"


def test_chunk_markdown_produces_ordered_chunks() -> None:
    _, body = parse_front_matter(NOTE)
    chunks = chunk_markdown(body)
    assert len(chunks) >= 1
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert all(c.text for c in chunks)
    assert all(c.token_count > 0 for c in chunks)
