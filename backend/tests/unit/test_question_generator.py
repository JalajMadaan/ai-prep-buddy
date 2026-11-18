"""Tests for the question generator's validators and accept/reject flow."""

import uuid
from types import SimpleNamespace
from typing import Any

from app.adapters.vector_store import SearchHit
from app.quiz.generator import (
    AnswerableVerdict,
    GeneratedQuestion,
    QuestionGenerator,
    validate_structure,
)
from app.rag.retriever import RetrievedChunk

GOOD = GeneratedQuestion(
    text="Why scale by sqrt(d_k)?",
    options=["dropout", "stabilise softmax", "normalise embeddings", "mask tokens"],
    correct_index=1,
    explanation="keeps softmax stable",
    difficulty=2,
)


def test_validate_structure_accepts_good() -> None:
    assert validate_structure(GOOD) == []


def test_validate_structure_flags_duplicate_options() -> None:
    q = GOOD.model_copy(update={"options": ["a", "a", "b", "c"]})
    assert "duplicate_options" in validate_structure(q)


def test_validate_structure_flags_bad_index() -> None:
    q = GOOD.model_copy(update={"correct_index": 9})
    assert "correct_index_out_of_range" in validate_structure(q)


def test_validate_structure_flags_too_few_options() -> None:
    q = GOOD.model_copy(update={"options": ["a", "b"]})
    assert "too_few_options" in validate_structure(q)


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        score=1.0,
        source_key="notes/llm_attention.md",
        text="Attention scales by 1/sqrt(d_k) to keep softmax stable.",
        title="Attention",
        url=None,
        section_path="",
        topic_ids=["llm.attention"],
    )


class _FakeRetriever:
    async def retrieve(
        self, query: str, *, top_k: int | None = None, topic_ids: list[str] | None = None
    ) -> list[RetrievedChunk]:
        return [_chunk()]


class _FakeIndex:
    def __init__(self, sim_score: float | None = None) -> None:
        self._sim = sim_score
        self.upserted: list[Any] = []

    async def ensure_collection(self) -> None:
        return None

    async def search_similar(self, text: str, *, limit: int = 5) -> list[SearchHit]:
        if self._sim is None:
            return []
        return [SearchHit(chunk_id=uuid.uuid4(), score=self._sim, payload={})]

    async def upsert(self, items: Any) -> None:
        self.upserted.extend(items)


class _FakeRepo:
    def __init__(self) -> None:
        self.saved: list[Any] = []

    async def upsert(self, **fields: Any) -> Any:
        obj = SimpleNamespace(id=uuid.uuid4(), **fields)
        self.saved.append(obj)
        return obj


class _FakeGateway:
    def __init__(self, gq: GeneratedQuestion, answerable: bool = True) -> None:
        self._gq = gq
        self._answerable = answerable

    async def structured(self, messages: Any, schema: Any, *, alias: str, **kw: Any) -> Any:
        if schema is GeneratedQuestion:
            return self._gq
        return AnswerableVerdict(answerable=self._answerable, reason="")


def _generator(gateway: Any, index: _FakeIndex, repo: _FakeRepo) -> QuestionGenerator:
    return QuestionGenerator(_FakeRetriever(), gateway, repo, index)  # type: ignore[arg-type]


async def test_accepts_valid_question() -> None:
    repo, index = _FakeRepo(), _FakeIndex()
    report = await _generator(_FakeGateway(GOOD), index, repo).generate_for_topic(
        "llm.attention", count=1
    )
    assert report.accepted == 1
    assert len(repo.saved) == 1
    assert repo.saved[0].status == "draft"
    assert len(index.upserted) == 1


async def test_rejects_duplicate() -> None:
    repo, index = _FakeRepo(), _FakeIndex(sim_score=0.95)
    report = await _generator(_FakeGateway(GOOD), index, repo).generate_for_topic(
        "llm.attention", count=1
    )
    assert report.accepted == 0
    assert report.rejected.get("duplicate") == 1


async def test_rejects_not_answerable() -> None:
    repo, index = _FakeRepo(), _FakeIndex()
    report = await _generator(_FakeGateway(GOOD, answerable=False), index, repo).generate_for_topic(
        "llm.attention", count=1
    )
    assert report.accepted == 0
    assert report.rejected.get("not_answerable") == 1
