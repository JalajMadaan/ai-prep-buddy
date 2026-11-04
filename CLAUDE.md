# CLAUDE.md — AI Prep Buddy

This file is read by Claude Code at the start of every session. It explains what we are building, how we work together, and the rules for code in this repo. The detailed specs live in `docs/`.

## 1. What we are building

**AI Prep Buddy** is an AI prep coach for AI/ML/GenAI engineering interviews. It has four modules around one shared **skill map**:

1. **Study assistant** — ask any AI question, get an interview-ready answer with citations from a curated knowledge base (RAG).
2. **Quiz** — daily drills (MCQ, short answer, flashcards) chosen from weak topics, scheduled with spaced repetition.
3. **Interview bot** — mock interview rounds by chat and later voice: it asks, follows up, scores with a rubric and writes a report.
4. **Prep planner** — reads a resume and a job post, finds gaps, plans what to study and which mocks to run.

The owner (Jalaj) is a data scientist moving into AI engineering. **The project has two equal goals:**

- Ship a real, deployed product that Jalaj and his friends use daily.
- Teach Jalaj backend engineering, system design, RAG, agents, evals, fine-tuning, voice and deployment well enough to answer interview questions on all of them.

Read these before starting any milestone:

| File | What it holds |
|---|---|
| `docs/01_PRODUCT.md` | Users, modules, user stories, scope, success metrics |
| `docs/02_ARCHITECTURE.md` | Components, request flows, latency budgets, design decisions, failure modes |
| `docs/03_DATA_MODEL_AND_API.md` | Tables, indexes, API endpoints and schemas |
| `docs/04_BUILD_PLAN.md` | Milestones M0–M9 and every ticket, with acceptance criteria |
| `docs/05_EVALS.md` | Eval datasets, metrics, thresholds, promptfoo, Ragas, DSPy, CI gates |
| `docs/06_MODELS_AND_TRAINING.md` | Model routing, fine-tuning, DPO, serving |
| `docs/07_DEPLOYMENT_AND_OPS.md` | Local setup, Azure deploy, CI/CD, monitoring, runbooks, cost controls |
| `docs/08_INTERVIEW_PREP.md` | Concepts and interview questions per milestone |

## 2. How we work: learning mode

Jalaj must be able to explain every line in `backend/app/core/`, `backend/app/services/` and `backend/app/agents/`. So for **every ticket**:

1. **Explain first (max ~200 words).** What concept this ticket uses, 2–3 design options, which one we pick and why. Name the tradeoff.
2. **Plan.** List the files you will create or change and the tests you will write. Wait for "go" unless Jalaj said "autopilot" for this ticket.
3. **Build the smallest working slice** with tests. Prefer several small commits over one large one.
4. **Explain the code** in a short walkthrough: request path, key functions, where it can fail.
5. **Update `docs/LEARNING_LOG.md`** with: concept, decision, tradeoff, one interview question and a 3–4 sentence answer.
6. **If the ticket changes a design decision**, add or update a decision record in `docs/adr/` using `docs/adr/0000-template.md`.

Tickets marked **`[YOU-WRITE]`** in the build plan are for Jalaj to implement himself. For those: write the tests and function signatures with docstrings, explain the approach, then stop. Review his code afterwards, point out issues and explain why.

When Jalaj asks "why?", answer at the level of a senior engineer in an interview: the mechanism, the alternative, and the numbers if any.

## 3. Rules

### Never
- Never commit secrets. All secrets come from environment variables; `.env` is git-ignored. Update `.env.example` when you add a variable.
- Never call a paid API or create a paid cloud resource without asking first. Free tiers are listed in `docs/07_DEPLOYMENT_AND_OPS.md`.
- Never store raw personal data (phone, email, addresses) from resumes in logs or traces. Mask it first (`app/core/pii.py`).
- Never copy question text from interview-report websites. Questions are written in our own words; a company tag needs a public source URL.
- Never put eval-set examples into fine-tuning data. Use the dedupe check in `evals/tools/dedupe.py`.
- Never let an LLM call run without a timeout, a retry policy and a trace.

### Always
- Check the current documentation of a library before using its API. LlamaIndex, LangGraph, DSPy, Ragas, LiveKit and LiteLLM change often; versions in this spec are guidance, the lockfile is the truth.
- Keep business logic out of route handlers (see layering below).
- Make every external dependency (LLM, embeddings, vector store, speech) an adapter behind an interface, so providers can be swapped by config.
- Write tests with every change. Unit tests mock adapters; integration tests use the docker-compose services.
- Run `make check` (lint, type-check, tests) before saying a ticket is done.
- Record LLM cost and latency for every call (the gateway does this; do not bypass it).

## 4. Tech stack (summary; details in docs)

| Concern | Choice |
|---|---|
| Language and packaging | Python 3.12, `uv` |
| API | FastAPI, Pydantic v2, uvicorn |
| Database | PostgreSQL 16 with SQLAlchemy 2.0 (async) and Alembic |
| Vector store | Qdrant (dense + sparse hybrid) |
| Cache, queues, rate limits | Redis; background jobs with `arq` |
| RAG framework | LlamaIndex (ingestion, retrievers, Qdrant store) plus our own reranking and citation code |
| Agents | LangGraph, with the Postgres checkpointer |
| LLM access | Our gateway in `app/llm/` on top of LiteLLM |
| Embeddings and reranker | fastembed (CPU, ONNX): `BAAI/bge-small-en-v1.5`, BM25 sparse, a cross-encoder reranker |
| Prompt optimisation | DSPy |
| Evals | promptfoo (behaviour + red team), Ragas (RAG), our calibrated judge, pytest |
| Tracing | Langfuse (LLM traces, prompt versions, scores), OpenTelemetry for HTTP |
| Metrics and logs | Prometheus metrics endpoint, structlog JSON logs |
| Voice (M5) | LiveKit Agents, Deepgram STT, Azure Neural TTS, Silero VAD, LiveKit turn detector |
| Training (M8) | Unsloth + Hugging Face TRL on Kaggle GPUs; vLLM on Modal for serving |
| Frontend | Next.js (App Router) + Tailwind in `frontend/`; keep it simple |
| Infra | Docker, docker compose, Terraform for Azure Container Apps, GitHub Actions |

## 5. Code layout and layering

```
backend/
  app/
    main.py              FastAPI app factory, middleware, routers
    config.py            Settings (pydantic-settings), one place for env vars
    api/                 Routers only: parse request, call a service, shape response
    services/            Business logic: study, quiz, interview, planner, skills
    agents/              LangGraph graphs (interview engine)
    rag/                 Ingestion, chunking, retrieval, reranking, citations
    llm/                 Gateway: routing, retries, fallbacks, budgets, cost, tracing
    evals/               Runtime judge and scorers used by the product
    prompts/             Versioned prompt files: <name>/v<N>.md
    db/                  SQLAlchemy models, session, repositories
    adapters/            Qdrant, Redis, speech, storage clients behind interfaces
    core/                Logging, errors, security, PII masking, rate limiting, ids
    workers/             arq tasks: ingestion, scoring, reports, nightly jobs
  tests/
    unit/  integration/  fixtures/
voice_agent/             LiveKit worker (M5), imports the same interview engine
evals/                   Datasets, promptfoo configs, Ragas runs, DSPy programs, reports
training/                Notebooks and scripts for SFT, DPO, encoder fine-tuning
content/                 Knowledge base sources (markdown notes, licensed docs)
infra/                   Terraform, Dockerfiles
frontend/                Next.js app
docs/                    Specs, ADRs, learning log
```

**Layering rule:** `api → services → (agents, rag, llm, db repositories, adapters)`. Lower layers never import from `api`. Services never import FastAPI.

## 6. Conventions

- Formatting and lint: `ruff format`, `ruff check`. Types: `mypy --strict` on `app/`.
- All I/O is async. No blocking calls in request handlers; CPU-heavy work (embedding large batches, PDF parsing) goes to a worker or `run_in_threadpool`.
- IDs: UUIDv7 (time-ordered) for all primary keys.
- Times: UTC everywhere, `timestamptz` in Postgres.
- Errors: raise domain errors from `app/core/errors.py`; one exception handler maps them to HTTP responses with a stable `code` field.
- Logging: structlog, JSON, include `request_id`, `user_id` (hashed), `session_id`, never raw text from users.
- Prompts: stored as versioned files in `backend/app/prompts/<name>/v<N>.md` and registered in Langfuse; code refers to prompts by name and version.
- Config: every tunable (thresholds, model names, top-k, timeouts) lives in `config.py` with a default and an env override.
- Commits: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `eval:`), one ticket per pull request, PR description includes "Eval impact".

## 7. Commands

```
make setup        # uv sync, pre-commit install
make up           # docker compose up -d (postgres, redis, qdrant)
make migrate      # alembic upgrade head
make dev          # uvicorn with reload
make worker       # arq worker
make check        # ruff + mypy + pytest (unit)
make test-int     # integration tests against compose services
make ingest       # build the knowledge base from content/
make eval-fast    # PR-sized eval subset (promptfoo + judge + RAG subset)
make eval-full    # full nightly eval suite, writes a report to evals/reports/
```

## 8. Definition of done (every ticket)

- Acceptance criteria in `docs/04_BUILD_PLAN.md` are met.
- Tests added and `make check` passes.
- Eval impact measured if the ticket touches prompts, retrieval, models or scoring (`make eval-fast`), and noted in the PR.
- `docs/LEARNING_LOG.md` updated; ADR added if a decision changed.
- No new secrets, no new paid services without approval.
