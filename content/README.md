# Knowledge base content

Source material the study assistant (RAG) retrieves from. Ingested by `make ingest`
(M1-T2) into Postgres (`documents`, `chunks`) + Qdrant (`kb_chunks`).

## Layout

```
content/
  notes/*.md       Our own notes (written in our own words). Front matter below.
  sources.yaml     External documents (papers, docs) with URL + licence.
```

## Note front matter

Every file in `notes/` starts with YAML front matter:

```yaml
---
title: "Scaled dot-product and multi-head attention"
topic_ids: [llm.attention, llm.transformer_arch]   # MUST match docs/01 taxonomy
source_url: null         # set if the note is adapted from a specific source
licence: original        # "original" = our own words (we own it)
tags: [transformers, attention]
status: outline          # outline | draft | done
---
```

- `topic_ids` are the join key across KB ↔ skill map ↔ quiz ↔ planner — use the exact
  IDs from [docs/01_PRODUCT.md](../docs/01_PRODUCT.md) §4. A wrong/misspelled id silently
  breaks topic filtering.
- Write **in your own words** (`licence: original`). Do not paste copyrighted text.
- Prefer clear heading hierarchy and keep code blocks whole — the splitter chunks by headings.

## Content policy (CLAUDE.md §6)

- External docs must be permissively licensed (MIT, Apache-2.0, CC-BY) or arXiv, with the
  **URL and licence recorded** in `sources.yaml`. Verify each licence (`verified: true`)
  **before** ingesting — the pipeline skips `verified: false` entries.
- Answers quote at most short excerpts and always link back to the source.

## Writing a good note (the target)

Each note should let you answer an interview question in ~2 minutes: define the concept,
give the mechanism, include **one number or tradeoff**, and note a common pitfall. The
outlines in `notes/` list exactly what each section should cover — fill them with prose.
