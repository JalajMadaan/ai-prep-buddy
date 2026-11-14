# Learning log

One entry per ticket. Keep each entry short enough to reread before an interview.

## Template

### <ticket id> · <title> · <date>
- **Concept:** what this ticket taught, in two sentences.
- **Decision:** what we chose.
- **Alternatives:** what we didn't choose, and why.
- **Tradeoff:** what we gave up.
- **Numbers:** any measurement (latency, recall, kappa, cost).
- **Interview question:** a question this lets me answer.
- **My answer (3–4 sentences):**

---

### M0-T1 · Repo scaffold · 2026-11-04
- **Concept:** A reproducible Python project needs a *lockfile* (exact pinned versions + hashes of every transitive dep) and *enforced types*. `uv` gives the lockfile (`uv.lock`); `mypy --strict` turns optional hints into contracts checked at edit-time.
- **Decision:** `uv` for packaging; `ruff` (lint + format) and `mypy --strict` on `app/`; `pytest` + `pytest-asyncio`; `pre-commit` ruff hooks; a root `Makefile` as the single command surface. Installed GNU Make on Windows rather than forking the command vocabulary.
- **Alternatives:** poetry/pip-tools (slower, heavier) vs uv; `just`/`tasks.py` instead of make (but every doc + CI assumes `make`).
- **Tradeoff:** one extra Windows dependency (GNU Make) in exchange for keeping specs, CLAUDE.md §7 and Linux CI all speaking the same commands.
- **Numbers:** `uv sync` resolved 25 packages in ~0.6s, installed 24 in ~3.8s; `make check` (ruff + mypy + 1 test) runs in well under a second.
- **Interview question:** Why do lockfiles matter, and what does strict typing buy you?
- **My answer:** A lockfile pins the exact version and hash of every transitive dependency, so a fresh clone on my laptop, in CI, and in prod all resolve to byte-identical packages — that kills "works on my machine" and makes builds reproducible and auditable. Strict typing (`mypy --strict`) promotes Python's optional hints into enforced contracts, so `None`-handling mistakes, wrong signatures, and refactor breakage are caught at edit-time instead of in production. The cost is a bit more upfront annotation, but the payoff compounds as the codebase and team grow. It also documents intent: the types are a spec that can't drift from the code.

### M0-T2 · Settings, logging, errors · 2026-11-04
- **Concept:** The request-handling backbone: 12-factor config (one typed `Settings` from env), structured JSON logs correlated by a `request_id` carried in a `contextvar`, and a domain-error hierarchy mapped to one stable JSON shape at the HTTP edge.
- **Decision:** `pydantic-settings` for config; `structlog` → JSON with a `request_id` processor; a `ContextVar` + HTTP middleware to carry the id; `AppError` subclasses (each with a stable `code` + `status_code`) mapped by one exception handler to `{error:{code,message,request_id}}`.
- **Alternatives:** scattered `os.getenv` (untyped); stdlib `logging`/`loguru` (weaker processor model); raising `HTTPException` inside services (couples business logic to FastAPI, breaks layering).
- **Tradeoff:** a bit of setup ceremony (processor chain, middleware, error classes) and one central config module everything imports — accepted because it buys type-safety, log correlation, and transport-free services.
- **Numbers:** 11 unit tests, `make check` ~3s; log lines are single-line JSON with `request_id`, `level`, `timestamp`.
- **Interview question:** Why route domain errors through one handler instead of raising `HTTPException` in your services, and why a stable `code` field?
- **My answer:** Services live below the API layer and must stay transport-agnostic, so they raise domain errors (`NotFoundError`, `BudgetExceededError`) that carry a stable machine-readable `code` and an HTTP status, but know nothing about FastAPI. A single exception handler at the edge translates any `AppError` into one consistent JSON envelope, `{error:{code,message,request_id}}`, which means clients branch on `code` — a contract that never changes — rather than on human-readable messages that get reworded. The `request_id` in both the body and the `X-Request-ID` header ties a user's error report straight to the correlated log lines. It also centralizes the guarantee that we never leak internals or stack traces to clients.

### M0-T3 · Local infrastructure · 2026-11-04
- **Concept:** Run the stateful backing services (Postgres, Redis, Qdrant) as containers via Docker Compose so local = CI = prod, with health checks that report *readiness* (accepting queries), not just liveness (process started).
- **Decision:** `docker-compose.yml` with pinned images (`postgres:16`, `redis:7`, `qdrant/qdrant:v1.12.4`), per-service healthchecks, named volumes (`pgdata`, `qdrant_data`); `make up` = `docker compose up -d --wait` (blocks until healthy, idempotent). Postgres init script creates `app_test` for integration tests.
- **Alternatives:** native installs on Windows (version drift, hard to reset); one shared DB for tests and dev (risk of tests clobbering dev data).
- **Tradeoff:** Docker Desktop must be running; bind mounts/ports need Windows care — accepted for reproducibility and one-command setup.
- **Numbers:** cold `make up` ≈ image pull time; warm start to all-healthy ≈ a few seconds; three containers.
- **Interview question:** What's the difference between a liveness and a readiness check, and why does it matter in a compose/orchestrated setup?
- **My answer:** Liveness answers "is the process alive?" — restart it if not. Readiness answers "can it actually serve requests right now?" — e.g. Postgres has finished recovery and is accepting connections. They differ during startup and transient overload: a container can be *live* but not yet *ready*. In Compose I use `--wait` on healthchecks so dependents (migrations, tests, the API's `/readyz`) only proceed once services are truly ready, which avoids flaky "connection refused" races. In Kubernetes the same split drives traffic routing (readiness gates the Service) versus restarts (liveness), so conflating them can either drop traffic or crash-loop a pod that just needed a moment.

### M0-T4 · Database layer · 2026-11-14
- **Concept:** Async SQLAlchemy 2.0 over asyncpg so DB I/O yields the event loop; a pooled engine; Alembic for versioned migrations; the repository pattern to keep SQL out of services; UUIDv7 primary keys and UTC `timestamptz` audit columns.
- **Decision:** cached async engine + `async_sessionmaker` + a `get_session` dependency; `UUIDAuditBase` (uuid7 id, created/updated); `User` model; `UserRepository` (flush, not commit — caller owns the transaction); async Alembic `env.py` pulling URL+metadata from the app; unit/integration split via a pytest marker so `make check` needs no DB.
- **Alternatives:** sync SQLAlchemy/psycopg (blocks the loop); ORM calls directly in services (couples logic to persistence, hard to unit-test); auto-increment int PKs (not globally unique, leaks row counts); `gen_random_uuid()` server default (that's UUIDv4 — not time-ordered).
- **Tradeoff:** async adds a `greenlet` bridge and more moving parts; repositories are a little boilerplate — accepted for non-blocking I/O and testable, swappable data access.
- **Numbers:** pool_size 5 + max_overflow 10 (configurable); 1 integration test create→read; `make migrate` created `users` + `alembic_version`.
- **Interview question:** What happens if your DB connection pool is too small? Too large? And why UUIDv7 over a plain UUID or an auto-increment id?
- **My answer:** Too small and requests serialize waiting for a free connection — latency climbs and you get pool-timeout errors under load even though Postgres is idle. Too large and every app replica multiplies its pool against Postgres's hard `max_connections`, so you exhaust server slots, burn memory, and can crash the database; the fix at scale is a pooler like PgBouncer rather than ever-bigger app pools. UUIDv7 is time-ordered, so new rows insert near the right edge of the B-tree index (good locality, less page fragmentation) while staying globally unique and non-guessable — unlike auto-increment ints, which leak counts and collide across shards, and unlike UUIDv4, whose randomness scatters writes across the index.

### M0-T5 · FastAPI app · 2026-11-14
- **Concept:** An app factory that composes the pieces built so far — request-id middleware, domain-error handlers, CORS — and exposes operational endpoints: `/healthz` (liveness), `/readyz` (readiness: Postgres + Redis + Qdrant, 503 if any down), `/metrics` (Prometheus request histograms). A dev-auth dependency returns a fixed local user so the app is usable without login.
- **Decision:** `create_app()` factory + module-level `app` for `uvicorn app.main:app`; readiness runs the three checks concurrently with `asyncio.gather`, each bounded by a 3s timeout; `prometheus-fastapi-instrumentator` for `/metrics`; `Principal` from a dev-auth dependency (real OAuth in M7).
- **Alternatives:** a global app built at import with no factory (harder to test/configure per-env); readiness that only checks the process (misses dependency outages); checking deps sequentially (slower, unbounded).
- **Tradeoff:** the factory + instrumentation add a little wiring; bounded checks can report a slow-but-alive dependency as not-ready — accepted, because a readiness probe must be fast and must never hang.
- **Numbers:** readiness fan-out bounded at 3s/check; live boot verified `/docs` 200 and `/readyz` all-true; 4 new unit tests + 1 readiness integration test.
- **Interview question:** Why separate `/healthz` from `/readyz`, and what exactly does each check?
- **My answer:** `/healthz` is liveness — it only proves the process is running and the event loop responds; an orchestrator uses it to decide whether to restart the container. `/readyz` is readiness — it actively checks that every backing service (Postgres, Redis, Qdrant) answers, and returns 503 if any is down, so the load balancer stops sending user traffic to an instance that would just error. Conflating them is dangerous: if liveness also checked the database, a brief DB blip would make Kubernetes kill and restart healthy app pods (a crash-loop) instead of simply pausing traffic. I run the readiness checks concurrently with per-check timeouts, because a probe that hangs is worse than one that fails — a stuck probe ties up the orchestrator and hides the real state.

### M0-T6 · LLM gateway v0 · 2026-11-14
- **Concept:** A single gateway for every LLM call so retries, timeouts, fallbacks, cost and tracing live in one place. Transient failures are retried with exponential backoff + full jitter; an exhausted model falls back to the next in the alias's chain; structured calls validate JSON against a Pydantic schema.
- **Decision:** alias→(models, timeout) resolution from config; `retry_with_backoff` (attempts, base, cap, jitter) wrapping each model; fallback loop across the chain; `complete`/`structured`/`stream`; cost+latency computed and logged. Tested against a mocked LiteLLM (no keys). Langfuse + `llm_calls` persistence deferred to M1.
- **Alternatives:** provider SDKs called directly in services (no central retries/budgets/traces); fixed-interval retries (thundering herd); retrying with no cap (unbounded latency); free-text LLM output (unparseable, unevaluable).
- **Tradeoff:** an extra layer every call passes through, and retries add latency on failures — accepted for reliability, swappable providers, and one place to enforce cost/tracing.
- **Numbers:** attempts = max_retries + 1 (default 3); backoff base 0.5s capped at 8s; full jitter; mocked-LiteLLM tests cover fallback, 429-retry-then-succeed, cost recording, schema validation.
- **Interview question:** What's the relationship between retries and idempotency, and why add jitter?
- **My answer:** Retrying is only safe when the operation is idempotent — if a call might have succeeded before the error (e.g. a timeout on the response, not the request), a blind retry can double the effect, so write operations need idempotency keys while pure reads like an LLM completion are naturally safe to repeat. Exponential backoff spaces out retries so a struggling provider gets time to recover instead of being hammered. Jitter adds randomness to each delay so that many clients that all failed during the same outage don't retry in lockstep the instant it recovers — without it you get a synchronized "thundering herd" that spikes load and causes a second outage. Full jitter (uniform between 0 and the capped delay) is the simple, well-tested choice.

### M0-T7 · Prompt registry · 2026-11-14
- **Concept:** Treat prompts as versioned artifacts, not strings in code. Files live at `app/prompts/<name>/v<N>.md` with YAML front matter (model alias, temperature, description) and a Jinja2 body; code references them by (name, version). A change means a NEW version file, so a prompt change is a reviewable diff and an eval can pin a version.
- **Decision:** a small registry (`load_prompt`/`render_prompt`, cached) using Jinja2 with `StrictUndefined` so a missing variable raises; a `prompts-sync` command that validates every prompt compiles (CI-useful) and defers the Langfuse push to M1.
- **Alternatives:** f-strings/constants in code (no diff history, no versioning, no eval pinning); editing a prompt in place (silently changes behaviour for every past eval/trace).
- **Tradeoff:** a tiny bit of loader machinery and the discipline of adding version files — worth it for reviewable, rollback-able, independently-evaluable prompts.
- **Numbers:** 6 registry tests; `StrictUndefined` turns a missing template variable into a loud error instead of an empty string.
- **Interview question:** Why version prompts in files instead of editing them in place, and why is a prompt change effectively a deploy?
- **My answer:** A prompt is as load-bearing as code — it determines model behaviour — so it deserves the same discipline: a new version is a new file, which gives a reviewable diff, a clean rollback, and a stable identifier an eval run or a trace can pin to. If I edited a prompt in place, every historical eval score and Langfuse trace would silently refer to text that no longer exists, so I could never reproduce or compare results. That's why a prompt change is a deploy: it can change faithfulness, latency, and cost, so it must pass the same eval gate and be rolled out (and rolled back) like any code change.
