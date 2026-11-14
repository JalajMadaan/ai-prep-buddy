---
title: "Grounding, citations, and faithfulness"
topic_ids: [rag.citations_grounding, rag.eval]
source_url: null
licence: original
tags: [rag, grounding, faithfulness, hallucination]
status: outline
---

<!-- OUTLINE — write in your own words. -->

# Grounding, citations, and faithfulness

## Grounding
- Cover: the answer must be supported by retrieved context, not the model's parametric memory.

## Citations
- Cover: numbered `[n]` markers mapping to retrieved chunks; prompt instructs "cite each claim";
  a verifier strips any `[n]` that does not map to a real retrieved chunk (our verify_citations, M1-T7).

## Faithfulness vs relevancy
- Cover: faithfulness = is every statement entailed by the context? relevancy = does it answer the
  question? (Ragas measures both — M1-T9.)

## Abstention
- Cover: if top rerank score < threshold, say "not covered" and suggest nearest topics rather than
  inventing an answer; log a content gap.

## Interview angle
- "How do you know an answer is grounded?" (faithfulness score + citation-invalid rate).

## Suggested source
- (own knowledge; Ragas docs when writing M1-T9)
