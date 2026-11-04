# 04 — Build plan

Ten milestones, about 16 weeks at 15–20 hours a week. Each milestone ends with something Jalaj can use, a demo, an eval report and a quiz on the concepts (`08_INTERVIEW_PREP.md`).

**Ticket format:** Goal · Build · Acceptance criteria (AC) · Learn (concepts Claude explains before coding).
**`[YOU-WRITE]`** = Jalaj implements; Claude writes tests, signatures and explanation, then reviews.

---

## M0 · Foundations (week 1)

**Outcome:** a clean, tested, observable skeleton that every later ticket builds on.

### M0-T1 Repo scaffold
- **Build:** `backend/` as a `uv` project (Python 3.12); ruff, mypy (strict on `app/`), pytest + pytest-asyncio, pre-commit; `Makefile` with the commands in CLAUDE.md; `.gitignore`; `.env.example`.
- **AC:** `make setup && make check` passes on a fresh clone.
- **Learn:** why lockfiles matter; what strict typing buys in a large codebase.

### M0-T2 Settings, logging, errors
- **Build:** `config.py` with pydantic-settings (all tunables with defaults); structlog JSON logging; request-ID middleware; `core/errors.py` domain errors and one exception handler returning `{error: {code, message, request_id}}`.
- **AC:** unit tests for error mapping; every log line has `request_id`.
- **Learn:** 12-factor config; structured logging; why stable error codes matter for clients.

### M0-T3 Local infrastructure
- **Build:** `docker-compose.yml` with Postgres 16, Redis 7, Qdrant (with health checks and named volumes); `make up`.
- **AC:** all three healthy; `make up` is idempotent.
- **Learn:** containers vs VMs; health checks; volumes.

### M0-T4 Database layer
- **Build:** async SQLAlchemy 2.0 engine and session dependency; Alembic; base model with UUIDv7 id and timestamps; `users` table; repository pattern (`db/repositories/users.py`).
- **AC:** `make migrate` creates tables; integration test creates and reads a user.
- **Learn:** connection pooling and pool sizing; migrations; why repositories keep SQL out of services.

### M0-T5 FastAPI app
- **Build:** app factory; routers; `/healthz`, `/readyz` (checks Postgres, Redis, Qdrant), `/metrics` (Prometheus); CORS; dev auth dependency returning a fixed local user.
- **AC:** readiness fails when Redis is stopped; metrics show request histograms.
- **Learn:** liveness vs readiness; how the event loop handles concurrent I/O.

### M0-T6 LLM gateway v0
- **Build:** `llm/gateway.py` with `complete()`, `stream()`, `structured(schema)` on LiteLLM. Model aliases from config (`fast`, `strong`, `judge`, `embed_rewrite`). Per-call timeout, retries with exponential backoff and jitter, fallback chain, cost and latency computed, a row in `llm_calls`, a Langfuse trace with prompt name and version.
- **[YOU-WRITE]** `retry_with_backoff(fn, attempts, base, max_delay, jitter)`.
- **AC:** unit tests with a mocked LiteLLM: timeout triggers fallback; 429 retries then succeeds; cost recorded; structured output validates against the Pydantic schema or raises.
- **Learn:** retries vs idempotency; why jitter prevents thundering herds; structured outputs.

### M0-T7 Prompt registry
- **Build:** `prompts/<name>/v<N>.md` with Jinja2 variables and front matter (model alias, temperature, description); loader by name and version; sync command to Langfuse prompt management.
- **AC:** test loads and renders a prompt; changing a prompt requires a new version file.
- **Learn:** prompts as versioned artifacts; how a prompt change is a deploy.

### M0-T8 CI
- **Build:** `.github/workflows/ci.yml`: uv sync, ruff, mypy, unit tests; a second job runs integration tests with service containers.
- **AC:** green on a pull request.

### M0-T9 Docs
- **Build:** ADR 0001 (modular monolith), first LEARNING_LOG entries.

---

## M1 · Study assistant: RAG (weeks 2–3)

**Outcome:** ask AI questions and get cited, interview-ready answers. Jalaj starts using it daily.

### M1-T1 Knowledge-base content
- **Build:** `content/notes/*.md` with front matter (`title`, `topic_ids`, `source_url?`); `content/sources.yaml` listing external documents with URL and licence. Seed 20 notes covering the taxonomy (Claude drafts outlines; Jalaj writes or edits them) plus 15–30 permissively licensed documents or arXiv papers.
- **[YOU-WRITE]** at least 10 of the notes, in your own words.
- **AC:** every document has a licence and URL recorded.

### M1-T2 Ingestion pipeline
- **Build:** LlamaIndex readers (markdown, PDF, HTML); normalisation; `MarkdownNodeParser` then `SentenceSplitter` (max 512 tokens, overlap 64) keeping code blocks whole; metadata (title, URL, section path, topic_ids, licence, kb_version); content-hash skip; atomic replace of changed documents; arq task `ingest_source`; `make ingest`.
- **AC:** re-running ingest on unchanged content does no work; a changed document's old chunks are gone and new ones searchable (integration test).
- **Learn:** chunking tradeoffs (size, overlap, structure); why atomic swaps avoid serving half-updated content.

### M1-T3 Embeddings and Qdrant
- **Build:** `adapters/vector_store.py` interface; Qdrant implementation; collection `kb_chunks` with named dense (384, cosine) and sparse (BM25) vectors and payload indexes; fastembed for `BAAI/bge-small-en-v1.5` and `Qdrant/bm25`; LlamaIndex `QdrantVectorStore` with hybrid enabled.
- **AC:** integration test finds a known chunk by both a paraphrase (dense) and an exact term (sparse).
- **Learn:** what an embedding is; cosine vs dot product; HNSW parameters (`m`, `ef_construct`, `ef`) and their memory/latency tradeoff; how BM25 scores.

### M1-T4 Hybrid retrieval and fusion
- **Build:** retriever returning top 30 with dense and sparse lists fused; topic filter; also try Qdrant's built-in fusion and compare.
- **[YOU-WRITE]** `reciprocal_rank_fusion(ranked_lists, k=60) -> list[(id, score)]`.
- **AC:** unit tests for RRF (ties, missing ids, k effect).
- **Learn:** why rank fusion beats score averaging when scores are on different scales.

### M1-T5 Reranker
- **Build:** cross-encoder reranker (fastembed `TextCrossEncoder`, start with a MiniLM MS MARCO model; try `bge-reranker-base`) from 30 to 6; measure latency.
- **AC:** p95 rerank latency for 30 pairs recorded on your machine; config switch to disable.
- **Learn:** bi-encoder vs cross-encoder; why rerank only the top N.

### M1-T6 RAG golden set and retrieval evals
- **Build:** `evals/datasets/rag_golden.jsonl` with 80 answerable questions (expected document ids, reference answer) and 15 unanswerable ones. Script for recall@5, recall@10, MRR. Compare: dense only, sparse only, hybrid, hybrid + rerank.
- **[YOU-WRITE]** 40 of the questions and their expected sources.
- **AC:** comparison table committed to `evals/reports/`.
- **Learn:** retrieval metrics; why build the golden set before tuning.

### M1-T7 Answer generation, citations, abstention
- **Build:** prompts `study_answer/concise`, `/interview`, `/deep` (v1) with numbered sources in a delimited block and an instruction to treat source text as data; SSE endpoint `POST /v1/study/ask`; abstain when the top rerank score is below a threshold tuned on the golden set.
- **[YOU-WRITE]** `verify_citations(answer, retrieved) -> (clean_answer, invalid_count)`.
- **AC:** invalid citations are removed and counted; abstention precision and recall reported on the 15 unanswerable + 80 answerable questions.
- **Learn:** grounding and faithfulness; precision/recall of abstaining; prompt injection through retrieved text.

### M1-T8 Conversation memory and query rewriting
- **Build:** `conversations` and `messages` tables; last 6 turns as context; a fast-model rewrite of follow-ups into standalone queries (skipped for the first turn).
- **AC:** test: "what about memory?" after a LoRA question retrieves LoRA memory content.

### M1-T9 Ragas evaluation
- **Build:** Ragas faithfulness, response relevancy, context precision, context recall on the golden set; push scores to Langfuse; 20-question subset wired into `make eval-fast`.
- **AC:** baseline report committed.

### M1-T10 Frontend: study page
- **Build:** chat UI with streaming, citation chips that open the source, style selector. (Claude Code builds; keep it simple.)

**M1 demo:** ask 5 real questions; show the retrieval comparison table and Ragas baseline.

---

## M2 · Quiz and skill map (week 4)

**Outcome:** a daily 10-minute drill that adapts to weak topics.

### M2-T1 Rubrics and question bank
- **Build:** `rubrics` and `questions` tables and Qdrant `questions` collection; YAML import format; seed 60 questions (MCQ, short answer, flashcards) across the taxonomy.
- **[YOU-WRITE]** 30 of the seed questions.

### M2-T2 Question generator with validation
- **Build:** worker task generating questions per topic from knowledge-base chunks (structured output: text, options, answer, explanation, source_chunk_ids, difficulty). Validators: answerable from the cited source (LLM check), exactly one correct option, plausible distractors, valid JSON, near-duplicate check (cosine ≥ 0.92 against existing questions). Status `draft`; admin approve/retire endpoints.
- **AC:** validity rate on 50 human-reviewed generated questions reported.
- **Learn:** evaluating generated content; why a validator pipeline beats "generate and hope".

### M2-T3 Grading
- **Build:** MCQ exact match; short answers graded by the fast model against the question rubric (structured); flashcards self-rated.
- **AC:** agreement between short-answer grading and Jalaj's grades on 40 answers reported.

### M2-T4 Skill model
- **Build:** `skill_states` and `skill_events`; mastery update per answer.
- **[YOU-WRITE]** Elo-style update: `expected = 1 / (1 + exp(-(mastery_logit - difficulty_logit)))`, `mastery_logit += K * (outcome - expected)`, confidence grows with attempts and decays with time.
- **AC:** tests: a correct answer on a hard question raises mastery more than on an easy one; a wrong answer on an easy question lowers it more.
- **Learn:** Elo and item response theory basics; why difficulty matters.

### M2-T5 Spaced repetition
- **Build:** `review_cards` using the `fsrs` Python package; map outcomes to FSRS ratings; due dates.
- **AC:** tests for scheduling after again/good/easy.
- **Learn:** forgetting curves; FSRS vs fixed intervals.

### M2-T6 Daily drill builder
- **Build:** selection: due cards first, then lowest-mastery topics with low confidence, mixed types and difficulty, nothing seen in 14 days; endpoints `GET /v1/quiz/today`, `POST /v1/quiz/answer`, `POST /v1/quiz/sessions/{id}/finish`.
- **AC:** deterministic with a seed; unit tests for each selection rule.

### M2-T7 "Make cards" from study answers
- **Build:** `POST /v1/study/messages/{id}/to-cards` creates draft flashcards from an answer.

### M2-T8 Frontend: quiz page and skill map view

**M2 demo:** a week of real drills; skill map changes; generator validity report.

---

## M3 · Interview bot, chat (weeks 5–6)

**Outcome:** full text mock interviews with follow-ups and a scored report.

### M3-T1 Rubrics for the four round types
- **Build:** YAML rubrics with dimensions, weights and anchor answers for scores 1, 3 and 5 (see `01_PRODUCT.md` §3.3).
- **[YOU-WRITE]** anchors for the GenAI system design rubric.

### M3-T2 Interview question bank
- **Build:** 40 interview questions, each with `required_points` (for example, for "design a RAG assistant for 10M users": clarify requirements, estimate load, chunking/retrieval choice, caching and invalidation, evaluation plan, failure modes, cost).
- **[YOU-WRITE]** 20 of them.

### M3-T3 Session planner
- **Build:** picks 4–6 questions by round: about 60% from weak topics, the rest coverage; weights job-post topics when given; avoids questions seen in 30 days. Project round uses `resume_facts` (manual JSON until M6).
- **AC:** unit tests for selection rules.

### M3-T4 Interview engine (LangGraph)
- **Build:** `agents/interview/graph.py` with a typed state and nodes `plan`, `ask`, `await_answer` (LangGraph `interrupt` for human input), `assess`, `decide`, `follow_up`, `hint`, `wrap_up`; Postgres checkpointer with `thread_id = session_id`.
- **[YOU-WRITE]** `decide(state) -> Literal["follow_up","hint","next","wrap_up"]` using the rules in `02_ARCHITECTURE.md` §3.4.
- **AC:** graph tests with a fake LLM cover every transition, the 2-follow-up cap, time-based wrap-up, and resume after a restart.
- **Learn:** agents as state machines; human-in-the-loop interrupts; checkpointing; why deterministic rules wrap the LLM.

### M3-T5 Personas and interviewer prompts
- **Build:** `interviewer/strict`, `/cto`, `/friendly` (v1). Rules: one question at a time, never reveal the answer, under 80 words per turn, stay in persona.
- **AC:** promptfoo behaviour suite (see `05_EVALS.md`) passes on 20 scripted conversations.

### M3-T6 Live assessor
- **Build:** fast-model structured `AssessorResult` (covered points, missing points, quality) per answer; latency logged.
- **AC:** agreement with Jalaj's labels on 30 answers reported.

### M3-T7 Chat interview API
- **Build:** create session, `POST /turns` (SSE, `Idempotency-Key`), end, get session.
- **AC:** integration test runs a 3-question interview with a fake LLM; a retried turn with the same key returns the same reply and does not advance state.
- **Learn:** idempotency keys; exactly-once effects over at-least-once delivery.

### M3-T8 Scoring worker and report
- **Build:** `score_session` arq task: split transcript per question; judge (strong model) returns `JudgeResult`; verify evidence quotes; idempotent upsert by `judge_version`; report builder (summary, weakest dimension, model answer grounded in the knowledge base).
- **[YOU-WRITE]** `evidence_is_valid(quote, transcript) -> bool` (normalised substring or fuzzy ratio ≥ 90 with `rapidfuzz`).
- **AC:** re-running scoring does not duplicate rows; a fabricated quote is detected.

### M3-T9 Skill updates and feedback
- **Build:** interview scores update topic mastery; `POST /v1/feedback` for "fair/unfair" and follow-up ratings (stored for DPO in M8).

### M3-T10 Frontend: interview chat and report pages

**M3 demo:** a full system design mock with report; the follow-up behaviour suite passing.

---

## M4 · Evaluation system (week 7)

**Outcome:** you can prove the scores are right and catch regressions automatically. This is the milestone interviewers will ask about most.

### M4-T1 Eval data layout
- **Build:** `evals/datasets/` with versioned JSONL files; `evals/tools/dedupe.py` (embedding similarity) to keep eval items out of training data; dataset README.

### M4-T2 Human grading
- **Build:** admin review queue and a simple grading page (blind: grader doesn't see the judge's score); collect 100+ answers graded by Jalaj and two friends.

### M4-T3 Agreement statistics
- **[YOU-WRITE]** `evals/stats.py`: Cohen's kappa, quadratic-weighted kappa for 1–5 scores, Spearman correlation, confusion matrix per dimension, bootstrap confidence intervals.
- **AC:** human-vs-human agreement reported before judge-vs-human.
- **Learn:** why weighted kappa fits ordinal scores; what to do when humans disagree.

### M4-T4 Simulated candidates
- **Build:** candidate personas with planted flaws (at least 8 types: skips estimation, no eval plan, factual error, no failure modes, rambling, overconfident wrong numbers, ignores the follow-up, strong control). A runner conducts full interviews bot-vs-engine with fixed seeds and scores them.
- **AC:** metrics: planted-flaw recall, rank-order accuracy (strong > weak), score separation; report committed.

### M4-T5 promptfoo suites
- **Build:** `evals/promptfoo/interviewer.yaml`, `study.yaml`, `redteam.yaml` (see `05_EVALS.md`).
- **AC:** all suites run with `make eval-fast`.

### M4-T6 DSPy optimisation
- **Build:** `evals/dspy/judge_program.py`: a DSPy module for the judge, metric = weighted-kappa agreement with human grades; split train/dev/test; optimise with `BootstrapFewShot`, then `MIPROv2`; export the best prompt as a new `prompts/judge/vN.md`. Same approach for the quiz generator (metric = validator pass rate).
- **AC:** before/after on the held-out test split reported; the new judge version only activates if it beats the old one.
- **Learn:** what DSPy optimisers change (instructions and few-shot examples); overfitting to the dev set.

### M4-T7 Eval runner and reports
- **Build:** `make eval-fast` (PR subset) and `make eval-full` (nightly); each run writes an `eval_runs` row and a markdown report with deltas against the last `main` run.
- **[YOU-WRITE]** paired bootstrap comparison of two runs on the same items.
- **Learn:** paired tests vs independent comparisons; noise in small eval sets.

### M4-T8 CI eval gates
- **Build:** a GitHub Actions job on pull requests that touch `prompts/`, `rag/`, `agents/`, `evals/` or `llm/`; thresholds in `evals/thresholds.yaml`; a nightly workflow for the full suite.
- **AC:** a deliberately bad prompt change fails the gate.

### M4-T9 Online quality monitoring
- **Build:** Langfuse scores from user feedback and sampled judge runs; 10% of sessions sampled into the human review queue; quality panel in the dashboard.

**M4 demo:** the agreement report, the simulated-candidate report, and a failing PR caught by the gate.

---

## M5 · Voice (weeks 8–9)

**Outcome:** spoken mock interviews that feel natural.

### M5-T1 LiveKit setup
- **Build:** LiveKit Cloud project (free plan); `POST /v1/voice/token`; one room per session; `voice_agent/` package with LiveKit Agents; local dev instructions.

### M5-T2 Voice pipeline
- **Build:** agent session with Silero VAD, Deepgram streaming STT (keyterms from a glossary generated from the topic taxonomy and question bank), Azure Neural TTS (selectable voice including Indian English), LiveKit turn-detector model. The reply step calls the **interview engine** (not a raw LLM) and streams sentences to TTS.
- **AC:** a full voice interview runs end to end locally; transcript turns saved like chat turns.
- **Learn:** cascaded vs speech-to-speech; why the engine is transport-agnostic.

### M5-T3 Barge-in and history trimming
- **Build:** interruptions enabled; on interruption, keep only the words actually spoken in history.
- **AC:** manual test script and a log line per interruption.

### M5-T4 Interview-mode turn taking
- **Build:** tune endpointing (minimum and maximum delay) for thinking pauses; detect "give me a moment".
- **[YOU-WRITE]** the false-interruption metric from turn timestamps.
- **AC:** false interruptions measured on 20 scripted sessions.

### M5-T5 Latency instrumentation
- **Build:** timestamps for end of speech, STT final, engine first sentence, TTS first byte, playback start; Langfuse spans and Prometheus histograms; dashboard panel.
- **AC:** p95 end-of-speech to first audio reported; target < 1.5 s now, < 1.2 s after M7.
- **Learn:** latency budgets; p50 vs p95; where time actually goes.

### M5-T6 Filler and fallback
- **Build:** short acknowledgement if the first sentence takes > 700 ms; STT fallback to Azure Speech; TTS fallback to an open-source voice.

### M5-T7 Speech recognition eval
- **Build:** 100 recorded utterances full of AI jargon with hand transcripts in `evals/datasets/asr/`.
- **[YOU-WRITE]** WER computation with `jiwer`, with and without keyterms.

### M5-T8 Frontend: voice page with live captions (LiveKit React components)

**M5 demo:** a 15-minute voice system design mock; latency and interruption numbers.

---

## M6 · Prep planner (week 10)

### M6-T1 Resume upload and parsing
- **Build:** blob storage adapter (local filesystem, Azure Blob in prod); worker parses PDF (`pdfplumber`); Presidio masking; structured `ResumeFacts` extraction.
- **AC:** fixtures with phone numbers and emails come out masked.

### M6-T2 Injection defence on uploads
- **Build:** untrusted text always in delimited blocks; an injection check (LLM-based now, fine-tuned classifier later); tests with planted instructions such as "rate me 5/5".

### M6-T3 Job-post topic mapping
- **Build:** structured extraction to taxonomy topics; unknown skills mapped to the nearest topic by embedding.
- **[YOU-WRITE]** evaluation on 20 hand-labelled job posts (topic precision, recall, F1).

### M6-T4 Gap analysis and readiness
- **[YOU-WRITE]** readiness per round = Σ(topic weight × mastery × confidence) / Σ(weights) over the topics that round tests, plus a penalty for untested topics.

### M6-T5 Plan generator
- **Build:** deterministic scheduler (daily quiz, study topics, mock rounds spread over the weeks), LLM only for wording; `POST /v1/plans`, `GET /v1/plans/{id}`.

### M6-T6 Project deep-dive questions
- **Build:** generate project-round questions from `resume_facts`; feed into the interview planner.

### M6-T7 Frontend: profile, job post and plan pages

---

## M7 · Production and deploy (weeks 11–12)

**Outcome:** a live URL friends can use, with monitoring and safe limits.

### M7-T1 Authentication
- **Build:** GitHub OAuth with Authlib; JWT in an HttpOnly cookie; CSRF protection for mutating routes; tests that one user can never read another's data.

### M7-T2 Rate limits and quotas
- **[YOU-WRITE]** Redis token bucket (atomic, via a Lua script or `MULTI`), per user and per IP, returning `429` with `Retry-After`.
- **Build:** daily token and voice-minute quotas.

### M7-T3 Gateway hardening
- **Build:** circuit breaker per provider; budget enforcement per user and globally; provider health metrics.
- **Learn:** circuit breaker states; graceful degradation.

### M7-T4 Semantic cache for study answers
- **Build:** cache key = kb_version + style + embedding similarity ≥ 0.95 to a cached question; invalidated on kb_version bump.
- **AC:** hit rate and faithfulness with cache on vs off reported.

### M7-T5 Containers
- **Build:** multi-stage Dockerfiles (API, worker, voice agent), non-root, slim base; image size reported.

### M7-T6 Terraform for Azure
- **Build:** resource group, Container Apps environment and apps (api, worker, voice-agent), Key Vault, Log Analytics, Storage account, managed identities, budget alert. External free services: Neon, Qdrant Cloud, Upstash, Langfuse Cloud, LiveKit Cloud.
- **AC:** `terraform plan` clean; apply only after Jalaj approves.

### M7-T7 CD pipeline
- **Build:** build and push images to GHCR; deploy to staging on merge to `main`, to production on a version tag; migration job before rollout; smoke tests after.

### M7-T8 Production observability
- **Build:** OpenTelemetry export (Azure Monitor or Grafana Cloud free); dashboards (latency, errors, cost, quality, voice); alerts (p95, error rate, daily cost, judge drift); runbooks in `docs/runbooks/`.

### M7-T9 Load tests
- **Build:** Locust for study and chat interview routes; LiveKit load testing for concurrent voice rooms; capacity note in DESIGN.md (requests per second per replica, rooms per voice worker).

### M7-T10 Frontend on Vercel; privacy page; "delete my data" endpoint

### M7-T11 (Optional) AWS track
- **Build:** deploy the API container to AWS (App Runner or ECS Fargate) with Terraform, to learn the AWS equivalents. Check costs and free credits first and ask before creating resources.

---

## M8 · Fine-tuning and alignment (weeks 13–15)

**Outcome:** models you trained run in production, with measured cost and quality impact. Details in `06_MODELS_AND_TRAINING.md`.

### M8-T1 Training data pipelines
- **Build:** exporters from logs (masked) for each training set; dedupe against all eval sets; dataset cards.

### M8-T2 BERT topic tagger
- **Build:** fine-tune an encoder (DeBERTa-v3-small or ModernBERT-base) as a multi-label topic classifier on chunks and questions labelled by the LLM, with 200 human-checked labels as the test set; export to ONNX; serve on CPU; use it in ingestion and job-post mapping.
- **AC:** F1, latency and cost vs LLM tagging reported.
- **Learn:** encoder vs decoder models; multi-label classification; distilling an LLM into BERT.

### M8-T3 (Optional) Reranker fine-tuning
- **Build:** fine-tune the cross-encoder on (question, cited chunk) pairs with hard negatives; MRR before and after.

### M8-T4 Distilled scorer
- **Build:** QLoRA SFT of a small instruct model on judge outputs that agree with human grades; evaluate on the human set (weighted kappa) and simulated candidates.
- **AC:** agreement within 0.05 kappa of the frontier judge, cost per session reported.

### M8-T5 DPO for follow-up questions
- **Build:** preference pairs from follow-up ratings, judge pairwise picks and built rejects; DPO with TRL; beta sweep (0.05, 0.1, 0.3).
- **AC:** pairwise win rate vs the SFT model and promptfoo behaviour pass rate reported.

### M8-T6 (Stretch) Reward model, PPO and GRPO
- **Build:** train a small reward model on the same pairs and run PPO on a tiny model to compare with DPO; or GRPO on quiz-question generation with a programmatic reward (validators pass).
- **Learn:** RLHF pipeline end to end; reward hacking in practice.

### M8-T7 Serving and rollout
- **Build:** vLLM on Modal (OpenAI-compatible endpoint) with LoRA adapters; try AWQ quantisation; gateway alias `scorer` routes to the small model with fallback; shadow mode, then an A/B test behind a feature flag.

### M8-T8 Model cards on Hugging Face

---

## M9 · Launch and packaging (week 16)

- **M9-T1** README: one-line pitch, live link, demo GIF, architecture diagram, eval results table.
- **M9-T2** `DESIGN.md` consolidating these docs, plus an ADR index.
- **M9-T3** Public read-only metrics page (quality, latency, cost).
- **M9-T4** Blog post: "How I checked my LLM judge against human graders".
- **M9-T5** 3-minute demo video.
- **M9-T6** Resume bullets and LinkedIn launch post.
- **M9-T7** Run a project-deep-dive mock about AI Prep Buddy on AI Prep Buddy itself.
