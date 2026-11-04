# AI Prep Buddy — task runner. See CLAUDE.md §7 for the full command surface.
# The backend is a uv project under backend/. Two run styles:
#   UVDIR  : run WITH cwd = backend/   (ruff, mypy, pytest read backend config)
#   UVPROJ : run WITH cwd = repo root  (pre-commit needs .git + config at root)
UVDIR  := uv run --directory backend
UVPROJ := uv run --project backend

.PHONY: setup fmt lint type test check \
        up migrate dev worker test-int ingest eval-fast eval-full

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

test:             ## Unit tests
	$(UVDIR) pytest

check: lint type test   ## Lint + type-check + unit tests

# ---------- Stubs (land in later tickets) ----------
up:
	@echo "make up: docker compose (postgres, redis, qdrant) lands in M0-T3"

migrate:
	@echo "make migrate: alembic migrations land in M0-T4"

dev:
	@echo "make dev: uvicorn app lands in M0-T5"

worker:
	@echo "make worker: arq worker lands in a later milestone"

test-int:
	@echo "make test-int: integration tests land in M0-T4 and later"

ingest:
	@echo "make ingest: knowledge-base ingestion lands in M1"

eval-fast:
	@echo "make eval-fast: evals land in M1/M4"

eval-full:
	@echo "make eval-full: evals land in M1/M4"
