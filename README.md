# AI Prep Buddy spec kit

Everything Claude Code needs to build AI Prep Buddy with you, one milestone at a time, while you learn the system design and AI engineering behind each part.

## What's in the kit

| File | Purpose |
|---|---|
| `CLAUDE.md` | Rules Claude Code follows in every session: learning mode, layering, conventions, definition of done |
| `docs/01_PRODUCT.md` | What AI Prep Buddy does, for whom, and how we measure success |
| `docs/02_ARCHITECTURE.md` | Components, flows, latency budgets, decisions and failure modes |
| `docs/03_DATA_MODEL_AND_API.md` | Database tables and API contract |
| `docs/04_BUILD_PLAN.md` | Milestones M0–M9, every ticket, acceptance criteria |
| `docs/05_EVALS.md` | How every module is evaluated, offline and online |
| `docs/06_MODELS_AND_TRAINING.md` | Model routing, BERT tagger, distilled scorer, DPO, serving |
| `docs/07_DEPLOYMENT_AND_OPS.md` | Local setup, Azure, CI/CD, monitoring, runbooks, free tiers |
| `docs/08_INTERVIEW_PREP.md` | What to study and which questions you can answer after each milestone |
| `docs/LEARNING_LOG.md` | Filled in as you build: concept, decision, tradeoff, interview answer |
| `docs/adr/0000-template.md` | Template for architecture decision records |
| `.env.example` | Every environment variable the project uses |

## How to start

1. Create an empty GitHub repo called `ai-prep-buddy` (public, so GitHub Actions is free).
2. Copy everything in this kit into the repo root and commit it.
3. Open the repo in Claude Code and send:

   > Read CLAUDE.md and every file in docs/. Then summarise the architecture back to me in 10 bullet points and list the tickets in milestone M0. Don't write code yet.

4. Check its summary against the docs. Then send:

   > Start ticket M0-T1 in learning mode.

5. Work ticket by ticket. At the end of each milestone, ask:

   > Quiz me on milestone M<n> using docs/08_INTERVIEW_PREP.md. Ask one question at a time and grade my answers.

## Timeline

About 16 weeks at 15–20 hours a week. AI Prep Buddy becomes useful to you after M1 (week 3), and is a complete product with evals after M4 (week 7). Voice, deployment and fine-tuning follow.

| Milestone | Weeks | You can use it for |
|---|---|---|
| M0 Foundations | 1 | Nothing yet; the base everything sits on |
| M1 Study assistant (RAG) | 2–3 | Asking AI questions with cited answers |
| M2 Quiz and skill map | 4 | Daily drills |
| M3 Interview bot (chat) | 5–6 | Text mock interviews with reports |
| M4 Evaluation system | 7 | Trusting the scores |
| M5 Voice | 8–9 | Spoken mock interviews |
| M6 Prep planner | 10 | Resume and job-post based plans |
| M7 Production and deploy | 11–12 | Sharing it with friends on a live URL |
| M8 Fine-tuning and alignment | 13–15 | Cheaper, better models you trained |
| M9 Launch and packaging | 16 | Resume, blog post, demo |
