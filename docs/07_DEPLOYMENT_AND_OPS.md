# 07 — Deployment and operations

## 1. Local development

```
git clone … && cd ai-prep-buddy
cp .env.example .env            # fill in free-tier keys
make setup                      # uv sync, pre-commit install
make up                         # Postgres, Redis, Qdrant in Docker
make migrate                    # Alembic migrations
make ingest                     # build the knowledge base from content/
make dev                        # API on http://localhost:8000 (docs at /docs)
make worker                     # arq worker in another terminal
cd frontend && npm install && npm run dev   # http://localhost:3000
```

Voice (M5): run the LiveKit agent with `uv run python -m voice_agent dev` against LiveKit Cloud; see `voice_agent/README.md`.

### docker-compose services
| Service | Image | Port | Notes |
|---|---|---|---|
| postgres | `postgres:16` | 5432 | Volume `pgdata`; init creates `app` and `app_test` databases |
| redis | `redis:7` | 6379 | AOF off locally |
| qdrant | `qdrant/qdrant` | 6333, 6334 | Volume `qdrant_data` |

Langfuse uses Langfuse Cloud (free Hobby plan) even locally, to avoid running its heavier stack.

## 2. Environment variables

See `.env.example`. Groups: app (`APP_ENV`, `LOG_LEVEL`, `EVAL_MODE`), database (`DATABASE_URL`), Redis (`REDIS_URL`), Qdrant (`QDRANT_URL`, `QDRANT_API_KEY`), LLM providers and aliases, Langfuse, speech (Deepgram, Azure Speech, LiveKit), auth (GitHub OAuth, JWT secret), storage, budgets and quotas.

## 3. Free tiers (checked October 2026; recheck when signing up)

| Service | Free allowance | Used for |
|---|---|---|
| Gemini API | Flash models on the free tier, roughly 10 requests/min and 1,500/day per project (check AI Studio) | `fast`, `strong`, `judge` |
| Groq | Sample limits ~30 requests/min, ~1,000/day | Fallback |
| Deepgram | $200 credit (~43,000 minutes), no card | Streaming STT |
| Azure AI Speech (F0) | 5 audio hours STT and 0.5M neural TTS characters per month | TTS, STT fallback |
| LiveKit Cloud | 1,000 agent minutes, 5,000 participant minutes, 5 concurrent sessions per month | Voice rooms |
| Qdrant Cloud | 1 GB RAM, 4 GB disk; suspended after 1 week idle | Vectors in prod |
| Neon Postgres | 1 GB per project, 100 compute hours/month; suspends after 5 min idle | Prod database |
| Upstash Redis | 500K commands/month, 250 MB | Prod Redis |
| Langfuse Cloud Hobby | 50K units/month, 30 days retention | Tracing |
| Azure Container Apps | 180K vCPU-s, 360K GiB-s, 2M requests per month per subscription | API, worker, voice agent |
| Azure free account | $200 for 30 days; card needed for verification | Key Vault, Storage, Log Analytics |
| Modal | $30 credit/month | vLLM serving |
| Kaggle | ~30 GPU hours/week | Training |
| Vercel Hobby | Free, non-commercial | Frontend |
| GitHub Actions | Free for public repos | CI, evals, deploys |

**Where free runs out first:** LiveKit agent minutes (about 50 twenty-minute voice sessions a month) and Azure TTS characters (about 70 sessions). Fallbacks: self-host LiveKit server (open source) on a small VM; open-source TTS on CPU.

## 4. Production architecture on Azure

| Resource | Purpose |
|---|---|
| Resource group `rg-aiprepbuddy-prod` (and `-staging`) | Everything below |
| Container Apps environment | Hosts three apps |
| Container App `api` | FastAPI; min replicas 0 (staging) / 1 (prod); scale on HTTP concurrency |
| Container App `worker` | arq worker; scale on Redis queue length (KEDA scaler) |
| Container App `voice-agent` | LiveKit worker; scale on CPU; min replicas 0 outside demo hours |
| Key Vault | Secrets; apps read them via managed identity |
| Storage account (Blob) | Resumes, opt-in audio (lifecycle rule: delete after 7 days), eval reports |
| Log Analytics workspace | Container logs |
| Budget + alert | Email at 50%, 80%, 100% of a small monthly budget |
| External | Neon, Qdrant Cloud, Upstash, Langfuse, LiveKit Cloud, Vercel |

**Cost rule:** with `min replicas = 0`, 180K vCPU-seconds covers about 100 active hours a month at 0.5 vCPU. Keep staging scaled to zero.

### Terraform layout
```
infra/terraform/
  modules/container_app/     reusable app module (image, env, secrets, scale rules)
  modules/observability/     Log Analytics, alerts, budget
  envs/staging/main.tf
  envs/prod/main.tf
  backend.tf                 remote state in an Azure Storage container
```

## 5. CI/CD

| Workflow | Trigger | Steps |
|---|---|---|
| `ci.yml` | Every PR and push | uv sync → ruff → mypy → unit tests → integration tests (service containers) → build images (no push) |
| `evals.yml` | PRs touching AI code; nightly | `make eval-fast` on PRs with a summary comment; `make eval-full` nightly |
| `deploy.yml` | Merge to `main` → staging; tag `v*` → prod | Build and push to GHCR → run Alembic migration job → update Container Apps revisions → smoke tests (`/readyz`, one study question, one quiz) → rollback to previous revision on failure |
| `terraform.yml` | Changes in `infra/` | `terraform fmt`, `validate`, `plan` as a PR comment; `apply` only by manual approval |

Secrets: GitHub Actions secrets for CI; Azure federated credentials (OIDC) for deploys, no long-lived cloud keys.

## 6. Observability

### Dashboards
1. **API:** requests/s, p50/p95/p99 latency per route, error rate, 429s.
2. **LLM:** calls/s per alias and model, latency, error and fallback rate, tokens, cost per hour and per user.
3. **RAG:** retrieval and rerank latency, abstain rate, citation-invalid rate, cache hit rate.
4. **Interview:** active sessions, turns/min, assessor latency, scoring queue depth and job duration.
5. **Voice:** concurrent rooms, p95 end-of-speech → first audio, stage breakdown, false interruptions, STT/TTS errors.
6. **Quality:** fairness rate, follow-up ratings, sampled faithfulness, judge calibration trend.
7. **Cost:** daily spend by provider vs budget.

### Alerts
| Alert | Condition |
|---|---|
| API latency | p95 > 2 s for 10 min |
| Error rate | 5xx > 2% for 5 min |
| LLM fallback storm | fallback rate > 20% for 10 min |
| Voice latency | p95 first audio > 1.5 s for 15 min |
| Queue backlog | scoring queue > 50 jobs for 15 min |
| Daily cost | > 120% of daily budget |
| Judge drift | weekly calibration agreement drops > 0.05 |

### Runbooks (`docs/runbooks/`)
One page per alert: what it means, dashboards to check, likely causes, mitigation (switch alias to fallback model, scale workers, enable degraded mode), follow-up.

## 7. Reliability practices

- Health and readiness probes on every app; graceful shutdown drains in-flight SSE streams and voice rooms.
- Database: Neon point-in-time restore; weekly logical backup to Blob via a scheduled job.
- Degraded modes: study answers fall back to "top passages only"; interviews pause with state saved; voice falls back to chat.
- Feature flags (env-based to start): new judge version, semantic cache, small-model routing, voice.

## 8. AWS equivalents (know these for interviews)

| Azure | AWS | Google Cloud |
|---|---|---|
| Container Apps | App Runner / ECS on Fargate | Cloud Run |
| Container Apps jobs / KEDA scaling | ECS scheduled tasks / Application Auto Scaling | Cloud Run jobs |
| Key Vault | Secrets Manager / KMS | Secret Manager |
| Blob Storage | S3 | Cloud Storage |
| Log Analytics / Azure Monitor | CloudWatch | Cloud Logging / Monitoring |
| Service Bus | SQS / SNS | Pub/Sub |
| Azure OpenAI / AI Foundry | Bedrock | Vertex AI |
| Azure AI Search | OpenSearch / Kendra | Vertex AI Search |
| Entra ID managed identity | IAM roles for tasks | Service accounts |
| Bicep / ARM | CloudFormation / CDK | Deployment Manager |

Optional M7-T11 deploys the API to AWS as well. Check AWS free-plan credits and ask before creating resources.
