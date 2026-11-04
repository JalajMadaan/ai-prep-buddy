# 01 — Product

## 1. One-line pitch

AI Prep Buddy is an AI prep coach for AI engineering interviews: it interviews you, quizzes you, answers your questions with sources, and plans your preparation, all driven by one map of what you know and don't know.

## 2. Users

| User | Need | When they arrive |
|---|---|---|
| Jalaj (first user) | Daily preparation for AI engineer / GenAI / NLP roles at top companies | M1 onwards |
| Friends and peers job hunting | Realistic mocks, honest scores, a study companion | M7 (public URL) |
| Bootcamps, placement cells (later, paid) | Assign mocks, see cohort readiness | Not in this build; design should not block it |

## 3. Modules and user stories

### 3.1 Study assistant (RAG)
- As a learner, I ask "Explain LoRA vs QLoRA" and get a clear answer with numbered citations to the sources it used.
- I can choose an answer style: **concise**, **interview answer** (2-minute spoken-style answer with structure), or **deep dive**.
- I can ask follow-up questions in the same conversation; the assistant understands "and how does that affect memory?"
- When the knowledge base does not cover a question, it says so and suggests the closest topics instead of inventing an answer.
- I can turn any answer into quiz cards with one click.

### 3.2 Quiz
- Every day I get a 10-minute drill of 8–12 questions chosen from my weakest and most overdue topics.
- Question types: multiple choice, short answer (graded by rubric), and flashcards (self-rated).
- After each answer I see whether I was right, a short explanation, and the source.
- Topics I get wrong come back sooner; topics I know well come back later (spaced repetition).

### 3.3 Interview bot
- I pick a round type, persona and length, then do a mock interview by chat (M3) or voice (M5).
- The interviewer asks one question at a time, follows up when I miss something, gives a hint if I'm stuck, and moves on when a point is covered.
- At the end I get a report: score per rubric dimension (1–5), a quote from my answer as evidence for each score, my weakest area, and a model answer for it.
- I can rate the report "fair / unfair" and rate individual follow-up questions "good / bad".
- I can replay one question and compare my new score with the old one (v1.1).

**Round types in v1**

| Round | What it covers | Rubric dimensions |
|---|---|---|
| GenAI system design | Design an LLM/RAG/agent system for given scale | Requirements, estimation, architecture, deep dive, tradeoffs, failure modes, evaluation, communication |
| ML / NLP / GenAI fundamentals | Theory questions with probing follow-ups | Correctness, depth, intuition, examples, communication |
| Project deep dive | Questions generated from my resume projects | Ownership, technical depth, decisions and tradeoffs, impact with numbers, honesty about limits |
| Behavioural | STAR questions | Situation clarity, actions owned, result with numbers, reflection |

**Personas:** strict big-tech interviewer (probes hard, little encouragement), startup CTO (pragmatic, cares about shipping and cost), friendly hiring manager (supportive, broad).

### 3.4 Prep planner
- I upload my resume (PDF) and paste a job post. AI Prep Buddy extracts my skills and projects and the job's required topics.
- It shows a gap analysis against my skill map: strong, weak, untested.
- It proposes a 1–4 week plan: which topics to study, how many quizzes, which mock rounds.
- It shows a readiness score per round type and how it changed over time.

### 3.5 Skill map (shared core)
- Mastery per topic between 0 and 1, with a confidence value, updated by quizzes, mocks and (lightly) study questions.
- Every module reads it; quizzes and mocks write it.

## 4. Topic taxonomy (v1)

Topic IDs are used across the question bank, knowledge base, skill map and planner.

| Area | Topics (IDs) |
|---|---|
| LLM foundations | `llm.tokenization`, `llm.attention`, `llm.transformer_arch`, `llm.decoding`, `llm.context_windows`, `llm.scaling` |
| NLP and encoders | `nlp.embeddings`, `nlp.bert`, `nlp.classification_ner`, `nlp.cross_vs_bi_encoders`, `nlp.classic_metrics` |
| Retrieval | `ret.bm25_sparse`, `ret.dense`, `ret.ann_hnsw_ivf_pq`, `ret.hybrid_fusion`, `ret.reranking`, `ret.metrics` |
| RAG | `rag.chunking`, `rag.query_rewriting`, `rag.citations_grounding`, `rag.eval`, `rag.advanced` (graph RAG, agentic RAG) |
| Agents | `agent.tool_calling`, `agent.react_planning`, `agent.memory`, `agent.multi_agent`, `agent.mcp`, `agent.reliability` |
| Evaluation | `eval.llm_judge`, `eval.golden_sets`, `eval.stats`, `eval.online_ab`, `eval.red_teaming` |
| Fine-tuning | `ft.sft`, `ft.lora_qlora`, `ft.distillation`, `ft.data_quality` |
| Alignment | `align.rlhf_ppo`, `align.reward_models`, `align.dpo`, `align.grpo_rlvr`, `align.reward_hacking` |
| Serving and performance | `serve.kv_cache`, `serve.batching_vllm`, `serve.quantization`, `serve.speculative`, `serve.latency_cost` |
| Voice | `voice.asr`, `voice.tts`, `voice.vad_turns`, `voice.streaming_latency` |
| System design | `sd.estimation`, `sd.caching`, `sd.queues`, `sd.multitenancy`, `sd.reliability`, `sd.observability` |
| Safety and security | `sec.prompt_injection`, `sec.pii`, `sec.guardrails` |
| Cloud and MLOps | `ops.containers`, `ops.azure`, `ops.aws`, `ops.cicd`, `ops.iac`, `ops.monitoring` |
| Behavioural | `beh.ownership`, `beh.conflict`, `beh.failure`, `beh.ambiguity` |

## 5. Scope

**In v1:** the four modules above, chat and voice, one user account per person, a web frontend, deployment on Azure.

**Later (do not build, but don't block):** whiteboard input for system design, cohort dashboards for institutions, mobile app, coding rounds with code execution, languages other than English.

**Non-goals:** coding interview practice with code execution (use LeetCode), non-AI roles, claims that a specific company asks a question unless a public source is linked.

## 6. Content policy for the knowledge base

- Sources: Jalaj's own notes (markdown), documentation and papers under licences that allow reuse (MIT, Apache-2.0, CC-BY), and arXiv papers. Store the source URL and licence for every document.
- Answers quote at most short excerpts and always link to the source.
- Questions in the bank are written in our own words.

## 7. Success metrics

| Metric | Target | Measured from |
|---|---|---|
| Jalaj's usage | 5+ sessions a week for 8 weeks | Product analytics |
| Weekly active users | 50 by end of M9 | Product analytics |
| Study answer faithfulness | ≥ 0.90 | Ragas on RAG golden set |
| Retrieval recall@5 | ≥ 0.85 | RAG golden set |
| Generated quiz questions valid | ≥ 95% | Validator + human sample |
| Judge agreement with humans | Cohen's κ ≥ 0.70 per dimension | Human-graded set |
| Planted-flaw recall | ≥ 0.85 | Simulated candidates |
| Voice: end of speech to first audio | p95 < 1.2 s | Traces |
| Voice: false interruptions | < 5% of turns | Traces |
| "Was this report fair?" | ≥ 80% yes | Feedback |
| Cost per 20-minute voice mock | Reported; target < ₹10 at scale | Gateway cost logs |
