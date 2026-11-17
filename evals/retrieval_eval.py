"""Retrieval eval: recall@5, recall@10, MRR for dense / sparse / hybrid / +rerank.

Runs against the ingested `kb_chunks` collection (run `make ingest` first). Writes
a markdown comparison table to evals/reports/.

    uv run --project backend python evals/retrieval_eval.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "backend"))

from app.adapters.vector_store import QdrantVectorStore  # noqa: E402
from app.rag.reranker import Reranker  # noqa: E402
from app.rag.retriever import HybridRetriever  # noqa: E402

DATASET = _ROOT / "evals" / "datasets" / "rag_golden.jsonl"
REPORTS = _ROOT / "evals" / "reports"


def _dedup(keys: list[str]) -> list[str]:
    seen: list[str] = []
    for k in keys:
        if k and k not in seen:
            seen.append(k)
    return seen


def load_golden() -> list[dict]:
    items = []
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("answerable"):  # skip the header + unanswerable rows
            items.append(row)
    return items


def recall_at(expected: set[str], ranked: list[str], k: int) -> float:
    if not expected:
        return 0.0
    return len(expected & set(ranked[:k])) / len(expected)


def mrr(expected: set[str], ranked: list[str]) -> float:
    for i, key in enumerate(ranked, start=1):
        if key in expected:
            return 1.0 / i
    return 0.0


Retriever = Callable[[str], Awaitable[list[str]]]


def build_configs(store: QdrantVectorStore) -> dict[str, Retriever]:
    hybrid = HybridRetriever(store)
    reranker = Reranker()

    async def dense(q: str) -> list[str]:
        hits = await store.search_dense(q, limit=10)
        return _dedup([str(h.payload.get("source_key", "")) for h in hits])

    async def sparse(q: str) -> list[str]:
        hits = await store.search_sparse(q, limit=10)
        return _dedup([str(h.payload.get("source_key", "")) for h in hits])

    async def hybrid_only(q: str) -> list[str]:
        chunks = await hybrid.retrieve(q, top_k=10)
        return _dedup([c.source_key for c in chunks])

    async def hybrid_rerank(q: str) -> list[str]:
        chunks = await hybrid.retrieve(q, top_k=30)
        reranked = reranker.rerank(q, chunks, top_n=10)
        return _dedup([c.source_key for c in reranked])

    return {
        "dense": dense,
        "sparse": sparse,
        "hybrid": hybrid_only,
        "hybrid+rerank": hybrid_rerank,
    }


async def evaluate(store: QdrantVectorStore) -> dict[str, dict[str, float]]:
    golden = load_golden()
    results: dict[str, dict[str, float]] = {}
    for name, retriever in build_configs(store).items():
        r5 = r10 = mrr_sum = 0.0
        for item in golden:
            expected = set(item["expected_doc_ids"])
            ranked = await retriever(item["question"])
            r5 += recall_at(expected, ranked, 5)
            r10 += recall_at(expected, ranked, 10)
            mrr_sum += mrr(expected, ranked)
        n = len(golden)
        results[name] = {"recall@5": r5 / n, "recall@10": r10 / n, "mrr": mrr_sum / n}
    return results


def write_report(results: dict[str, dict[str, float]], n: int) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M")
    path = REPORTS / f"retrieval_{stamp}.md"
    lines = [
        f"# Retrieval eval — {stamp}",
        "",
        f"Golden answerable questions: {n}",
        "",
        "| Config | recall@5 | recall@10 | MRR |",
        "|---|---|---|---|",
    ]
    for name, m in results.items():
        lines.append(
            f"| {name} | {m['recall@5']:.3f} | {m['recall@10']:.3f} | {m['mrr']:.3f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


async def main() -> None:
    store = QdrantVectorStore()
    results = await evaluate(store)
    path = write_report(results, len(load_golden()))
    print(f"Wrote {path}\n")
    print("| Config | recall@5 | recall@10 | MRR |")
    print("|---|---|---|---|")
    for name, m in results.items():
        print(f"| {name} | {m['recall@5']:.3f} | {m['recall@10']:.3f} | {m['mrr']:.3f} |")


if __name__ == "__main__":
    asyncio.run(main())
