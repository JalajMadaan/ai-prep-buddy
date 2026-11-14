---
title: "Attention and the Transformer block"
topic_ids: [llm.attention, llm.transformer_arch]
source_url: null
licence: original
tags: [transformers, attention, self-attention]
status: outline
---

<!-- OUTLINE — write this in your own words. Target: answer "what is attention?" in ~2 min. -->

# Attention and the Transformer block

## Why attention exists
- Cover: the limitation of RNNs (sequential, long-range dependencies fade); attention lets
  every token look at every other token in parallel.

## Scaled dot-product attention
- Cover: Q, K, V; `softmax(QKᵀ / √d_k) · V`; why the `√d_k` scaling (keeps dot products from
  growing with dimension and saturating softmax).
- Number to include: complexity is O(n²·d) in sequence length n — the reason context windows
  are expensive.

## Multi-head attention
- Cover: splitting into h heads so the model attends to different relationships at once; concat + project.

## The Transformer block
- Cover: attention + feed-forward, residual connections, layer norm; encoder vs decoder; causal
  (masked) attention for autoregressive generation.

## Interview angle
- "Why √d_k?" / "Why is long context expensive?" (the O(n²) answer) / "self vs cross attention".

## Suggested source
- doc_attention_paper (sources.yaml)
