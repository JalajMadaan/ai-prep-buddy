---
title: "Chunking strategies for RAG"
topic_ids: [rag.chunking]
source_url: null
licence: original
tags: [rag, chunking, ingestion]
status: outline
---

<!-- OUTLINE — write in your own words. -->

# Chunking strategies for RAG

## Why chunk at all
- Cover: embeddings and context windows are finite; retrieval granularity = chunk granularity.

## The tradeoffs
- Cover: too small → loses context, answer spread across many chunks; too large → dilutes the
  embedding (one vector for many ideas), wastes context, hurts precision.
- Number: our default ≈ 512 tokens, 64 overlap — state this and why overlap avoids cutting an
  idea across a boundary.

## Structure-aware chunking
- Cover: split by headings first (MarkdownNodeParser), then size-limit; keep code blocks whole.

## Metadata per chunk
- Cover: title, section_path, url, topic_ids, kb_version — carried into Qdrant payload for
  filtering and citations.

## Interview angle
- "How did you choose chunk size/overlap?" → tie to the retrieval eval (recall@k) in M1-T6.

## Suggested source
- doc_llamaindex_docs
