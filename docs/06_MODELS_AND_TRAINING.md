# 06 — Models and training

## 1. Model aliases and routing

Services never name a model directly. They ask the gateway for an alias; config maps aliases to providers and models, with a fallback chain. Model names change often: set them in `.env`, not in code.

| Alias | Used for | Latency need | Default (free) | Fallback | After M8 |
|---|---|---|---|---|---|
| `fast` | Query rewrite, live assessor, short-answer grading, interviewer wording | First token < 400 ms | Gemini Flash-class model (free tier) | Groq-hosted open model | Distilled scorer for assessor |
| `strong` | Study answers (deep), report writing, model answers | Quality first | Gemini's strongest free-tier model | Groq larger model | — |
| `judge` | Final scoring, eval judging | Consistency first | Fixed model + version pinned per judge version | None: a judge never silently changes model | Distilled scorer (if it passes calibration) |
| `followup` | Generating follow-up questions | < 400 ms | Same as `fast` | Groq | DPO-tuned small model |
| `generator` | Quiz question generation (batch) | None | `strong` | `fast` | — |

**Gateway behaviour:**
- Timeouts per alias (`fast` 4 s, `strong` 20 s, `judge` 30 s); 2 retries with exponential backoff and jitter on 429/5xx; then next model in the chain.
- Circuit breaker per provider: open after 5 failures in 30 s, half-open after 60 s.
- Budgets: per user per day, per eval run, and global per day; exceeding a budget raises `BudgetExceeded`.
- Every call logs model, prompt name and version, tokens, cost, latency and status, and creates a Langfuse span.
- Free-tier note: prompts sent on free tiers may be used by the provider to improve their products. Only masked text and public content go to free-tier models.

## 2. Embeddings and reranking (CPU, free)

| Component | Model | Why |
|---|---|---|
| Dense embeddings | `BAAI/bge-small-en-v1.5` via fastembed (384-dim) | Fast on CPU, strong for its size, no API limits |
| Sparse | `Qdrant/bm25` via fastembed | Exact technical terms |
| Reranker | MiniLM MS MARCO cross-encoder via fastembed; compare with `bge-reranker-base` | Accuracy on top 30 within ~250 ms on CPU |

Upgrade path to discuss in interviews: larger embedding model, int8 quantisation in Qdrant, a fine-tuned reranker (M8-T3).

## 3. Encoder model: BERT topic tagger (M8-T2)

- **Task:** multi-label classification of a chunk, question or job-post sentence into taxonomy topic IDs (~70 labels).
- **Base model:** `microsoft/deberta-v3-small` (or `answerdotai/ModernBERT-base` if available and stable).
- **Data:** 5,000+ items labelled by the `strong` LLM (silver labels) + 200 human-checked items as the test set. Deduped against eval sets.
- **Training:** Hugging Face `Trainer`, sigmoid outputs with binary cross-entropy, class-weighting for rare topics, threshold per label tuned on dev; 3–5 epochs; Kaggle T4.
- **Serving:** export to ONNX, run on CPU inside the worker and API (`onnxruntime`).
- **Report:** micro and macro F1 vs the LLM tagger on the human test set; latency per item; cost per 10,000 items.
- **Interview point:** "I distilled an LLM labeller into a BERT classifier: similar F1, ~100× cheaper and ~20 ms on CPU."

## 4. Distilled scorer (M8-T4)

- **Why:** the live assessor runs every turn and must be fast; the final judge is the largest cost at scale.
- **Base model:** an open instruct model of 3–8B parameters with a permissive licence.
- **Data:** (rubric, anchors, question, transcript segment) → judge JSON output, only where the judge agreed with human grades (within 1 point) or from simulated sessions where the planted flaw was caught. 3,000–10,000 examples. Deduped against eval sets.
- **Method:** QLoRA SFT with Unsloth and TRL `SFTTrainer`: 4-bit base, LoRA rank 16, alpha 32, dropout 0.05, learning rate 2e-4, 1–3 epochs, max sequence length 2,048. On a T4, use fp16 (no bf16).
- **Eval:** weighted kappa vs humans on the held-out test split, planted-flaw recall, JSON validity rate, latency, cost per session. Must be within 0.05 kappa of the frontier judge to replace it for live assessment; for final scoring it must pass the full activation rule in `05_EVALS.md` §4.

## 5. DPO for follow-up questions (M8-T5)

- **Pairs (prompt = interview state + last answer; chosen vs rejected follow-up):**
  - Jalaj's and users' ratings: "good follow-up" vs "bad follow-up" for the same state (regenerate an alternative to pair with a rated one).
  - Judge pairwise picks with position swapping (only keep pairs where both orders agree).
  - Built rejects: follow-ups that reveal the answer, ask two questions at once, repeat a covered point, or go off-topic.
- **Size:** 1,000–3,000 pairs.
- **Method:** start from the SFT model; TRL `DPOTrainer`; beta sweep 0.05, 0.1, 0.3; LoRA.
- **Eval:** pairwise win rate vs the SFT model (judge with position swap, plus a 50-pair human check), promptfoo behaviour pass rate, length drift (DPO models often get longer; check it).

## 6. Stretch: reward model, PPO and GRPO (M8-T6)

- **Reward model + PPO:** train a small reward model (Bradley–Terry loss) on the same pairs; run PPO with a KL penalty on a 0.5–1.5B model; compare with DPO on the same eval. Purpose: to have actually seen the classic RLHF loop and its instability.
- **GRPO with a programmatic reward:** train the quiz generator with reward = validators pass (valid JSON, exactly one correct option, answerable from the source, not a duplicate). Watch for reward hacking (for example, trivially easy questions that always pass) and add a difficulty term.

## 7. Serving (M8-T7)

- **vLLM on Modal:** OpenAI-compatible endpoint, scale to zero, LoRA adapters loaded per alias; compare fp16 vs AWQ 4-bit on latency, throughput and kappa.
- **Gateway integration:** alias `scorer` → small model, fallback → `judge`. Cold start is handled by falling back while the container warms.
- **Rollout:** shadow mode (small model runs alongside, results logged, not shown) for 1 week → A/B test by user (50/50) with guardrail metrics (fairness rate, latency, cost) → full rollout or rollback.
- **Concepts to explain:** KV cache, PagedAttention, continuous batching, quantisation tradeoffs, why scale-to-zero means cold starts.

## 8. Free compute for training

| Resource | Use |
|---|---|
| Kaggle notebooks (about 30 GPU hours a week on 2×T4 or P100, 12-hour sessions) | All SFT, DPO, BERT runs. Save checkpoints to Hugging Face Hub every epoch. |
| Google Colab free | Quick experiments |
| Modal ($30 monthly credit) | vLLM serving; short evaluation jobs |

## 9. Training data rules

- Only masked text; no raw resumes or audio in training sets.
- Every training set has a dataset card: source, size, filters, dedupe result against eval sets, licence.
- Users who delete their data are removed from future training exports.
