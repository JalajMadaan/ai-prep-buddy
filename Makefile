# AI Prep Buddy — task runner. See CLAUDE.md §7 for the full command surface.
# The backend is a uv project under backend/. Two run styles:
#   UVDIR  : run WITH cwd = backend/   (ruff, mypy, pytest read backend config)
#   UVPROJ : run WITH cwd = repo root  (pre-commit needs .git + config at root)
UVDIR  := uv run --directory backend
UVPROJ := uv run --project backend
UVEVAL := uv run --project backend --group evals

.PHONY: setup fmt lint type test check \
        up down ps migrate revision prompts-sync dev worker test-int ingest eval-retrieval eval-fast eval-full

# ---------- Working now (M0-T1) ----------
setup:            ## Install deps and git hooks
	uv sync --project backend
	$(UVPROJ) pre-commit install

fmt:              ## Auto-format
	$(UVDIR) ruff format .

lint:             ## Lint (and check formatting)
	$(UVDIR) ruff check .
	$(UVDIR) ruff format --check .

type:             ## Type-check (mypy --strict on app/)
	$(UVDIR) mypy

test:             ## Unit tests (no live infra needed)
	$(UVDIR) pytest -m "not integration"

check: lint type test   ## Lint + type-check + unit tests

# ---------- Local infrastructure (M0-T3) ----------
up:               ## Start Postgres, Redis, Qdrant and wait until healthy
	docker compose up -d --wait

down:             ## Stop infra (keep data); use `docker compose down -v` to wipe
	docker compose down

ps:               ## Show infra container status
	docker compose ps

# ---------- Stubs (land in later tickets) ----------
migrate:          ## Apply database migrations (alembic upgrade head)
	$(UVDIR) alembic upgrade head

revision:         ## Autogenerate a migration: make revision m="add x table"
	$(UVDIR) alembic revision --autogenerate -m "$(m)"

prompts-sync:     ## Validate all prompts (and push to Langfuse once configured)
	$(UVDIR) python -m app.prompts.sync

test-int:         ## Integration tests (requires `make up`)
	$(UVDIR) pytest -m integration

dev:              ## Run the API with reload on :8000 (docs at /docs)
	$(UVDIR) uvicorn app.main:app --reload --port 8000

worker:
	@echo "make worker: arq worker lands in a later milestone"

ingest:           ## Build the knowledge base from content/ (needs `make up`)
	$(UVDIR) python -m app.rag.ingest

eval-retrieval:   ## Retrieval eval (recall@k, MRR) -> evals/reports/
	$(UVPROJ) python evals/retrieval_eval.py

eval-fast:        ## PR-sized eval subset (Ragas on a few golden items)
	$(UVEVAL) python evals/ragas_run.py --limit 5

eval-full:        ## Full eval suite (all answerable golden items)
	$(UVEVAL) python evals/ragas_run.py --limit 0
