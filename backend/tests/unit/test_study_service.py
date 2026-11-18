"""Study service tests with fake retriever/reranker/gateway (no network)."""

import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any

from app.rag.retriever import RetrievedChunk
from app.services.study import StudyEvent, StudyService


def _chunk(score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        score=score,
        source_key="notes/llm_attention.md",
        text="Attention scales scores by 1/sqrt(d_k).",
        title="Attention",
        url=None,
        section_path="",
        topic_ids=["llm.attention"],
    )


class _FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = chunks

    async def retrieve(
        self, question: str, *, top_k: int | None = None, topic_ids: list[str] | None = None
    ) -> list[RetrievedChunk]:
        return self._chunks


class _FakeReranker:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = chunks

    def rerank(
        self, query: str, chunks: Sequence[RetrievedChunk], *, top_n: int | None = None
    ) -> list[RetrievedChunk]:
        return self._chunks


class _FakeResult:
    def __init__(self, text: str) -> None:
        self.text = text
        self.cost_usd = 0.0001
        self.latency_ms = 12.0


class _FakeGateway:
    def __init__(self, text: str) -> None:
        self._text = text

    async def complete(self, messages: Any, *, alias: str, **kw: Any) -> _FakeResult:
        return _FakeResult(self._text)


async def _collect(agen: AsyncIterator[StudyEvent]) -> list[StudyEvent]:
    return [event async for event in agen]


def _service(chunks: list[RetrievedChunk], answer: str) -> StudyService:
    return StudyService(_FakeRetriever(chunks), _FakeReranker(chunks), _FakeGateway(answer))  # type: ignore[arg-type]


async def test_answer_path_emits_meta_citation_done() -> None:
    svc = _service([_chunk(5.0)], "Attention divides by 1/sqrt(d_k) to stabilise softmax [1].")
    events = await _collect(svc.ask("why sqrt dk?", style="interview"))
    kinds = [kind for kind, _ in events]
    assert kinds[0] == "meta"
    assert events[0][1]["abstained"] is False
    assert any(kind == "citation" and data["n"] == 1 for kind, data in events)
    assert kinds[-1] == "done"


async def test_abstains_when_top_score_below_threshold() -> None:
    svc = _service([_chunk(-5.0)], "unused")
    events = await _collect(svc.ask("something off topic"))
    assert events[0] == ("meta", {"abstained": True})
    assert events[-1][0] == "done"
    assert events[-1][1]["abstained"] is True
