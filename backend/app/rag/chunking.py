"""Heading-aware chunking via LlamaIndex (MarkdownNodeParser + SentenceSplitter).

Split by markdown headings first (so a chunk stays within one section), then
size-limit to the configured token budget with overlap. Section headers are
captured into ``section_path`` for citations and filtering.
"""

from __future__ import annotations

from llama_index.core import Document as LIDocument
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

from app.config import get_settings
from app.db.repositories.content import ChunkData


def _pipeline() -> IngestionPipeline:
    s = get_settings()
    return IngestionPipeline(
        transformations=[
            MarkdownNodeParser(),
            SentenceSplitter(chunk_size=s.rag_chunk_size, chunk_overlap=s.rag_chunk_overlap),
        ]
    )


def _section_path(metadata: dict[str, object]) -> str:
    headers = [str(v) for k, v in metadata.items() if "header" in k.lower()]
    return " / ".join(headers)


def chunk_markdown(body: str) -> list[ChunkData]:
    """Chunk a markdown body into ordered :class:`ChunkData`."""
    nodes = _pipeline().run(documents=[LIDocument(text=body)])
    chunks: list[ChunkData] = []
    for ordinal, node in enumerate(nodes):
        text = node.get_content().strip()
        if not text:
            continue
        chunks.append(
            ChunkData(
                ordinal=ordinal,
                section_path=_section_path(node.metadata),
                text=text,
                token_count=len(text.split()),  # approximate (whitespace) token count
            )
        )
    return chunks
