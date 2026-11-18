"""Ragas evaluation of the study pipeline on the RAG golden set.

For each answerable golden question we run retrieve -> rerank -> generate to get
an answer + contexts, then score with Ragas (faithfulness, response relevancy,
context precision/recall). The judge LLM is Groq; embeddings are our local
fastembed (Groq has no embeddings API). Writes a markdown report to evals/reports/.

    uv run --project backend --group evals python evals/ragas_run.py --limit 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "backend"))

from langchain_core.embeddings import Embeddings  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402
from ragas import EvaluationDataset, evaluate  # noqa: E402
from ragas.embeddings import LangchainEmbeddingsWrapper  # noqa: E402
from ragas.llms import LangchainLLMWrapper  # noqa: E402
from ragas.metrics import (  # noqa: E402
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)
from ragas.run_config import RunConfig  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.adapters.vector_store import QdrantVectorStore  # noqa: E402
from app.llm.gateway import Gateway  # noqa: E402
from app.prompts.registry import render_prompt  # noqa: E402
from app.rag.citations import verify_citations  # noqa: E402
from app.rag.embeddings import embed_dense, embed_query_dense  # noqa: E402
from app.rag.reranker import Reranker  # noqa: E402
from app.rag.retriever import HybridRetriever  # noqa: E402

DATASET = _ROOT / "evals" / "datasets" / "rag_golden.jsonl"
REPORTS = _ROOT / "evals" / "reports"
CONTEXTS_PER_Q = 3


class _FastEmbed(Embeddings):
    """Langchain Embeddings backed by our local fastembed (bge-small)."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embed_dense(list(texts))

    def embed_query(self, text: str) -> list[float]:
        return embed_query_dense(text)


def load_answerable(limit: int) -> list[dict]:
    items = []
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("answerable"):
            items.append(row)
    return items if limit <= 0 else items[:limit]


async def build_samples(items: list[dict]) -> list[dict]:
    retriever = HybridRetriever(QdrantVectorStore())
    reranker = Reranker()
    gateway = Gateway()
    samples = []
    for item in items:
        question = item["question"]
        retrieved = await retriever.retrieve(question, top_k=get_settings().retrieve_top_k)
        reranked = reranker.rerank(question, retrieved, top_n=CONTEXTS_PER_Q)
        sources = "\n\n".join(f"[{i}] {c.title}: {c.text}" for i, c in enumerate(reranked, 1))
        prompt = render_prompt("study_answer/concise", 1, question=question, sources=sources)
        result = await gateway.complete([{"role": "user", "content": prompt}], alias="fast")
        answer, _ = verify_citations(result.text, reranked)
        samples.append(
            {
                "user_input": question,
                "response": answer,
                "retrieved_contexts": [c.text for c in reranked],
                "reference": item["reference_answer"],
            }
        )
    return samples


def write_report(means: dict[str, float], n: int) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M")
    path = REPORTS / f"ragas_{stamp}.md"
    lines = [f"# Ragas eval — {stamp}", "", f"Answerable questions scored: {n}", "", "| Metric | Score |", "|---|---|"]
    lines += [f"| {k} | {v:.3f} |" for k, v in means.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5, help="questions to score (0 = all)")
    args = parser.parse_args()

    settings = get_settings()
    items = load_answerable(args.limit)
    samples = asyncio.run(build_samples(items))

    llm = LangchainLLMWrapper(
        ChatOpenAI(
            model=settings.llm_judge_model.removeprefix("groq/"),
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key,
            temperature=0.0,
        )
    )
    embeddings = LangchainEmbeddingsWrapper(_FastEmbed())
    metrics = [
        Faithfulness(),
        # strictness=1 -> n=1, since Groq's API rejects n>1 (OpenAI-style multi-sample).
        ResponseRelevancy(strictness=1),
        LLMContextPrecisionWithReference(),
        LLMContextRecall(),
    ]

    result = evaluate(
        dataset=EvaluationDataset.from_list(samples),
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(max_workers=2, timeout=90, max_retries=5),
    )

    df = result.to_pandas()
    means = {col: float(df[col].mean()) for col in df.select_dtypes(include="number").columns}
    path = write_report(means, len(samples))
    print(f"Wrote {path}\n")
    for k, v in means.items():
        print(f"{k}: {v:.3f}")


if __name__ == "__main__":
    main()
