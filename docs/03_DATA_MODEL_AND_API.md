# 03 — Data model and API

All primary keys are UUIDv7. All timestamps are `timestamptz` in UTC. Every user-owned table has `user_id` and every query filters by it. Text that may contain personal data is stored masked (`*_masked` columns).

## 1. PostgreSQL tables

### Users and profiles

| Table | Columns | Notes |
|---|---|---|
| `users` | id, github_id (unique), display_name, email_hash, created_at, settings jsonb | `settings`: preferred persona, daily quiz size, voice enabled, audio retention opt-in |
| `profiles` | user_id (PK, FK), resume_blob_key, resume_facts jsonb, target_roles text[], updated_at | `resume_facts`: masked, structured (skills, projects[{name, tech, decisions, impact}]) |
| `job_posts` | id, user_id, company, title, text_masked, required_topics jsonb, seniority, created_at | `required_topics`: list of {topic_id, weight} |

### Knowledge base

| Table | Columns | Notes |
|---|---|---|
| `documents` | id, source_url, title, licence, source_type (note, doc, paper), content_hash, kb_version, created_at, updated_at | Unique (source_url) |
| `chunks` | id, document_id, ordinal, section_path, text, token_count, topic_ids text[], kb_version | Vectors live in Qdrant under the same id |
| `content_gaps` | id, user_id, question_masked, nearest_topic_id, created_at | Logged when the study assistant abstains |

### Study assistant

| Table | Columns | Notes |
|---|---|---|
| `conversations` | id, user_id, title, created_at | |
| `messages` | id, conversation_id, role (user, assistant), text_masked, style, citations jsonb, model, prompt_version, tokens_in, tokens_out, cost_usd, latency_ms, abstained bool, created_at | `citations`: [{n, chunk_id, document_id, url}] |

### Question bank and quizzes

| Table | Columns | Notes |
|---|---|---|
| `questions` | id, kind (mcq, short, flashcard, interview), round (null for quiz), text, options jsonb, answer jsonb, explanation, rubric_id, topic_ids text[], difficulty (1–5), source_chunk_ids uuid[], company_tag, company_source_url, status (draft, approved, retired), created_by (human, generator), generator_version, created_at | Index on (status, kind), GIN on topic_ids |
| `rubrics` | id, name, version, dimensions jsonb, anchors jsonb, created_at | `dimensions`: [{key, description, weight}]; `anchors`: example answers for scores 1, 3, 5 |
| `quiz_sessions` | id, user_id, started_at, finished_at, question_ids uuid[] | |
| `quiz_answers` | id, quiz_session_id, question_id, user_id, answer_masked, correct bool, score float, judge_version, latency_ms, created_at | |
| `review_cards` | user_id, question_id, fsrs_state jsonb, due_at, last_review_at | PK (user_id, question_id); index (user_id, due_at) |

### Interviews

| Table | Columns | Notes |
|---|---|---|
| `interview_sessions` | id, user_id, round, persona, planned_minutes, mode (chat, voice), job_post_id, status (planned, active, ended, scored, failed), plan jsonb, started_at, ended_at, audio_blob_key | `plan`: [{question_id, rubric_id, required_points[]}] |
| `turns` | id, session_id, idx, speaker (interviewer, candidate), text_masked, question_id, start_ms, end_ms, stage_latency jsonb, idempotency_key, created_at | Unique (session_id, idx); unique (session_id, idempotency_key) |
| `scores` | id, session_id, question_id, dimension, score (1–5), evidence_quote, rationale, judge_version, evidence_valid bool, created_at | Unique (session_id, question_id, dimension, judge_version) for idempotency |
| `reports` | session_id (PK), judge_version, summary, weakest_dimension, model_answer, overall jsonb, created_at | |

LangGraph's Postgres checkpointer creates its own tables (`checkpoints`, `checkpoint_writes`, …). Use the session id as the graph `thread_id`.

### Skills and planning

| Table | Columns | Notes |
|---|---|---|
| `skill_states` | user_id, topic_id, mastery (0–1), confidence (0–1), attempts, last_evidence_at | PK (user_id, topic_id) |
| `skill_events` | id, user_id, topic_id, source (quiz, interview, study), delta, evidence_ref, created_at | Audit trail for every mastery change |
| `plans` | id, user_id, job_post_id, weeks, items jsonb, readiness jsonb, created_at | `items`: [{day, kind (study, quiz, mock), topic_ids, round}] |

### Feedback, evals, costs

| Table | Columns | Notes |
|---|---|---|
| `feedback` | id, user_id, target_type (message, report, turn, question), target_id, kind (fair, unfair, good_followup, bad_followup, thumbs_up, thumbs_down, wrong_answer), comment_masked, created_at | |
| `human_grades` | id, grader, session_id, question_id, dimension, score, notes, created_at | For judge calibration |
| `eval_runs` | id, suite, git_sha, prompt_versions jsonb, models jsonb, dataset_version, metrics jsonb, report_blob_key, created_at | One row per eval run |
| `llm_calls` | id, user_id_hash, purpose, model, provider, prompt_name, prompt_version, tokens_in, tokens_out, cost_usd, latency_ms, status, trace_id, created_at | Written by the gateway; partition by month later |

## 2. Qdrant collections

| Collection | Vectors | Payload | Used by |
|---|---|---|---|
| `kb_chunks` | `dense`: 384-dim cosine (bge-small); `sparse`: BM25 | chunk_id, document_id, title, url, section_path, topic_ids, kb_version, licence | Study assistant, model answers, quiz generation |
| `questions` | `dense` only | question_id, kind, round, topic_ids, difficulty, status | Avoiding near-duplicate questions, picking related questions |

Create payload indexes on `topic_ids`, `kb_version`, `status`, `kind`.

## 3. Redis keys

| Key | Type | TTL | Purpose |
|---|---|---|---|
| `rl:{user_id}:{route}` | token bucket (hash) | 1 min | Per-user rate limit |
| `rl:ip:{ip}` | token bucket | 1 min | Per-IP rate limit for anonymous routes |
| `quota:{user_id}:{yyyymmdd}` | hash: tokens, voice_seconds, cost_usd | 2 days | Daily quotas |
| `idem:{key}` | string (response id) | 24 h | Idempotency for turn submission |
| `cache:study:{kb_version}:{hash}` | string (answer json) | 7 days | Semantic cache (M7) keyed by normalised question embedding bucket |
| `voice:{session_id}` | hash | 2 h | Live voice state: speaking flag, last partial transcript |
| `arq:*` | | | Job queue (managed by arq) |

## 4. API conventions

- Base path `/v1`. JSON in and out. Auth via session cookie (JWT); dev mode injects a local user.
- Errors: `{ "error": { "code": "QUOTA_EXCEEDED", "message": "...", "request_id": "..." } }` with a fitting HTTP status.
- Streaming endpoints use Server-Sent Events with these event types: `token` (`{"text": "..."}`), `citation` (`{"n": 1, "chunk_id": "...", "url": "..."}`), `meta` (`{"message_id": "...", "abstained": false}`), `done` (`{"cost_usd": 0.0004, "latency_ms": 1320}`), `error`.
- Mutating endpoints that a client may retry accept an `Idempotency-Key` header.
- Pagination: `?limit=&cursor=` (cursor = last id).

## 5. Endpoints

### Health and meta
| Method and path | Description |
|---|---|
| `GET /healthz` | Liveness: process up |
| `GET /readyz` | Readiness: Postgres, Redis, Qdrant reachable |
| `GET /metrics` | Prometheus metrics (internal only) |

### Auth (M7)
| Method and path | Description |
|---|---|
| `GET /v1/auth/github/login` | Redirect to GitHub OAuth |
| `GET /v1/auth/github/callback` | Create or fetch user, set session cookie |
| `POST /v1/auth/logout` | Clear session |
| `GET /v1/me` | Current user and settings |

### Study assistant
| Method and path | Request | Response |
|---|---|---|
| `POST /v1/study/conversations` | `{title?}` | `{id}` |
| `POST /v1/study/ask` | `{conversation_id, question, style: "concise"\|"interview"\|"deep", topic_filter?: [topic_id]}` | SSE stream |
| `GET /v1/study/conversations/{id}` | | `{id, messages: [...]}` |
| `POST /v1/study/messages/{id}/to-cards` | | `{question_ids: [...]}` (draft cards for review) |

### Quiz
| Method and path | Request | Response |
|---|---|---|
| `GET /v1/quiz/today` | | `{quiz_session_id, questions: [{id, kind, text, options?}]}` |
| `POST /v1/quiz/answer` | `{quiz_session_id, question_id, answer, self_rating?: "again"\|"hard"\|"good"\|"easy"}` | `{correct, score, explanation, source: {url, title}, next_due_at}` |
| `POST /v1/quiz/sessions/{id}/finish` | | `{summary: {correct, total, topics_updated: [...]}}` |

### Interviews
| Method and path | Request | Response |
|---|---|---|
| `POST /v1/interviews` | `{round, persona, planned_minutes, mode: "chat"\|"voice", job_post_id?}` | `{session_id, first_message, livekit_token? (voice)}` |
| `POST /v1/interviews/{id}/turns` | `{text}` + `Idempotency-Key` | SSE stream of interviewer reply |
| `POST /v1/interviews/{id}/end` | | `{status: "ended"}` (scoring enqueued) |
| `GET /v1/interviews/{id}` | | Session with transcript |
| `GET /v1/interviews/{id}/report` | | `{status, scores: [{question_id, dimension, score, evidence_quote, rationale}], summary, weakest_dimension, model_answer}` or `202` while scoring |
| `POST /v1/interviews/{id}/questions/{qid}/replay` | | New mini-session for one question (v1.1) |
| `GET /v1/interviews` | | List of past sessions |

### Planner and profile
| Method and path | Request | Response |
|---|---|---|
| `POST /v1/profile/resume` | multipart PDF | `{status: "processing"}` then poll `GET /v1/profile` |
| `GET /v1/profile` | | `{resume_facts, target_roles}` |
| `POST /v1/job-posts` | `{company, title, text}` | `{id, required_topics, seniority}` |
| `POST /v1/plans` | `{job_post_id, weeks}` | `{plan_id, items, readiness}` |
| `GET /v1/plans/{id}` | | Plan with progress |

### Skills
| Method and path | Response |
|---|---|
| `GET /v1/skills` | `{topics: [{topic_id, mastery, confidence, due_count}], readiness: {round: score}}` |
| `GET /v1/skills/history?topic_id=` | Mastery over time |

### Feedback
| Method and path | Request |
|---|---|
| `POST /v1/feedback` | `{target_type, target_id, kind, comment?}` |

### Admin (protected, owner only)
| Method and path | Description |
|---|---|
| `POST /v1/admin/ingest` | Enqueue knowledge-base ingestion |
| `GET /v1/admin/questions?status=draft` | Review generated questions |
| `POST /v1/admin/questions/{id}/approve` and `/retire` | Moderate the bank |
| `GET /v1/admin/review-queue` | Sessions sampled for human grading |
| `POST /v1/admin/human-grades` | Submit human grades |
| `GET /v1/admin/eval-runs` | Eval history |

### Eval-only (enabled when `EVAL_MODE=true`, never in production)
| Method and path | Description |
|---|---|
| `POST /v1/evals/interviewer-step` | `{script_id, persona}` → runs one interview-engine step on a scripted state; used by promptfoo |
| `POST /v1/evals/study-answer` | `{question, style}` → answer with citations and retrieved chunk ids, no persistence |
| `POST /v1/evals/judge` | `{question_id, transcript_segment, judge_version}` → `JudgeResult` |

### Voice (M5)
| Method and path | Description |
|---|---|
| `POST /v1/voice/token` | `{session_id}` → LiveKit access token for that room |
| `POST /v1/livekit/webhook` | Room events (participant joined/left), signature verified |

## 6. Pydantic schema examples

```python
class AskRequest(BaseModel):
    conversation_id: UUID
    question: str = Field(min_length=3, max_length=2000)
    style: Literal["concise", "interview", "deep"] = "interview"
    topic_filter: list[str] | None = None

class DimensionScore(BaseModel):
    dimension: str
    score: int = Field(ge=1, le=5)
    evidence_quote: str = Field(max_length=400)  # must be copied verbatim from the transcript
    rationale: str = Field(max_length=600)

class JudgeResult(BaseModel):
    question_id: UUID
    scores: list[DimensionScore]
    missing_points: list[str]

class AssessorResult(BaseModel):  # live, during a turn
    covered_points: list[str]
    missing_points: list[str]
    answer_quality: Literal["strong", "partial", "weak", "stuck"]
```
