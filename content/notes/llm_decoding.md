---
title: "Decoding strategies: greedy, beam, top-k, top-p, temperature"
topic_ids: [llm.decoding]
source_url: null
licence: original
tags: [decoding, sampling, temperature]
status: outline
---

<!-- OUTLINE — write in your own words. -->

# Decoding strategies

## The setup
- Cover: an LLM outputs a probability distribution over the next token; decoding = how we pick.

## Deterministic
- Cover: greedy (argmax, repetitive); beam search (keeps top-b sequences; good for MT, bland for open-ended).

## Sampling
- Cover: temperature (scales logits: <1 sharper/safer, >1 flatter/creative; T→0 ≈ greedy);
  top-k (sample from k most likely); top-p / nucleus (smallest set whose prob ≥ p).
- Number/tradeoff: typical interview answer ≈ temperature 0 for extraction/grading, 0.7 for chat.

## When to use which (map to our product)
- Cover: judge/grading → temperature 0 (consistency); interviewer wording → modest temperature.

## Interview angle
- "How would you make an LLM judge reproducible?" (temp 0, pinned model/version).

## Suggested source
- (own knowledge; optionally link a decoding blog under a permissive licence)
