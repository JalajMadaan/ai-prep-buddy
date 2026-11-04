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
