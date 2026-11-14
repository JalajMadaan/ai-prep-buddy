---
title: "Hybrid retrieval and reciprocal rank fusion"
topic_ids: [ret.hybrid_fusion, ret.bm25_sparse, ret.dense]
source_url: null
licence: original
tags: [retrieval, bm25, dense, rrf]
status: outline
---

<!-- OUTLINE — write in your own words. -->

# Hybrid retrieval and reciprocal rank fusion

## Dense vs sparse
- Cover: dense (embeddings) captures meaning/paraphrase; sparse (BM25) captures exact terms.
- Why both: technical tokens like `QLoRA`, `HNSW`, `bge-small` are matched reliably by BM25 but
  may be washed out in a dense vector.

## BM25 in one paragraph
- Cover: term frequency × inverse document frequency, with document-length normalisation.

## Fusing the two lists
- Cover: scores from dense (cosine) and BM25 are on different scales → you cannot just add them.
- Reciprocal Rank Fusion: `score(d) = Σ 1/(k + rank_i(d))` over each ranked list, k≈60.
  Uses *rank*, not raw score, so it is scale-free.

## Interview angle
- "Why RRF instead of averaging scores?" (different scales); "when does hybrid beat dense-only?"

## Suggested source
- doc_qdrant_docs (hybrid search), doc_llamaindex_docs
