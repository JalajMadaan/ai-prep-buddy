# ADR 0001: Modular monolith with background and voice workers

- **Status:** accepted
- **Date:** 2026-11-14
- **Milestone / ticket:** M0-T9

## Context

AI Prep Buddy has four product modules (study/RAG, quiz, interview bot, prep
planner) plus background scoring/ingestion and (later) a voice agent. We are a
team of one learning backend/AI engineering, on free tiers, who must ship a
real deployed product *and* be able to defend the architecture in interviews.
The decision: how to shape the services.

Constraints that matter: fast to build and debug by one person; low fixed cost
(Azure Container Apps + free external tiers); the voice worker and the chat API
must run the *same* interview engine; and we want the option to scale or split
hot paths later without a rewrite.

## Options considered

1. **Microservices from day one** — one service per module, each deployable.
   - Pros: independent scaling/deploys; strong boundaries.
   - Cons: network calls, distributed tracing, schema/version coordination, and
     ops overhead that one person on free tiers cannot justify at launch (20 DAU).
2. **Single flat app, no internal boundaries** — everything imported anywhere.
   - Pros: fastest to write initially.
   - Cons: boundaries erode, business logic leaks into route handlers, nothing
     can be split out later without untangling it first.
3. **Modular monolith + workers (chosen)** — one FastAPI app with strict internal
   module boundaries (`api → services → {agents, rag, llm, db, adapters}`), one
   `arq` worker process, one LiveKit voice worker — all sharing `backend/app`.
   - Pros: one deploy, one debugger, one trace per request; clean seams so any
     module (voice, scoring) can become its own service later; external
     dependencies sit behind adapter interfaces so providers are swappable.
   - Cons: a bug can affect the whole process; all modules share a release cadence
     and a runtime until we split.

## Decision

Build a **modular monolith plus a background worker and a voice worker**, all
sharing `backend/app`, with a strict layering rule (`api → services → lower
layers`; lower layers never import `api`; services never import FastAPI).

## Consequences

- **Easier:** local dev and debugging (one process), one request/LLM trace,
  shared models and the single LLM gateway, fast iteration across modules.
- **Harder:** we must *enforce* boundaries by discipline (lint/review), since
  nothing physically prevents a cross-layer import; the whole app shares a
  release and a blast radius until a module is split out.
- **What we'll measure / when we'd revisit:** split a module into its own service
  only when a real signal appears — a scaling hotspot (e.g. voice workers
  CPU-bound), a team/ownership boundary, or an independent release need. The
  module seams and adapter interfaces are what make that a move, not a rewrite.
