---
title: "Bi-encoders vs cross-encoders"
topic_ids: [nlp.cross_vs_bi_encoders, ret.reranking]
source_url: null
licence: original
tags: [embeddings, reranking, retrieval]
status: outline
---

<!-- OUTLINE — write in your own words. -->

# Bi-encoders vs cross-encoders

## Bi-encoder
- Cover: encodes query and document separately into vectors; similarity = cosine/dot product.
- Key property: document vectors are precomputed and indexed → fast retrieval over millions.

## Cross-encoder
- Cover: feeds (query, document) together through the model → a single relevance score.
- Key property: more accurate (full attention over the pair) but cannot be precomputed →
  must run per candidate at query time.

## The tradeoff (this is the whole point)
- Cover: bi-encoder for recall over the whole corpus; cross-encoder to rerank the top-N.
- Number: we rerank top ~30 → 6, because scoring 30 pairs on CPU is ~ms-feasible but scoring
  the whole corpus is not.

## Map to our pipeline
- Cover: fastembed bge-small (bi-encoder) retrieve → MiniLM cross-encoder rerank.

## Interview angle
- "Why not just use the cross-encoder for everything?" (latency: O(corpus) vs O(top-N)).

## Suggested source
- (own knowledge)
