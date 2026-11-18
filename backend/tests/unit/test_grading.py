"""Tests for the grading service (MCQ / flashcard / short)."""

from typing import Any

from app.db.models.question import Question
from app.quiz.grading import GradingService, ShortAnswerGrade


def _mcq(correct_index: int = 1) -> Question:
    return Question(
        ext_key="k-mcq",
        kind="mcq",
        text="Which option is right?",
        options=["alpha", "beta", "gamma", "delta"],
        answer={"correct_index": correct_index},
        explanation="beta is correct",
        topic_ids=[],
        difficulty=2,
        status="approved",
    )


def _short() -> Question:
    return Question(
        ext_key="k-short",
        kind="short",
        text="Why RRF?",
        options=[],
        answer={"reference": "scores are on different scales"},
        topic_ids=[],
        difficulty=3,
        status="approved",
    )


def _flashcard() -> Question:
    return Question(
        ext_key="k-fc",
        kind="flashcard",
        text="Define LoRA",
        options=[],
        answer={"back": "low-rank adapters"},
        topic_ids=[],
        difficulty=1,
        status="approved",
    )


class _FakeGateway:
    def __init__(self, score: float) -> None:
        self._score = score

    async def structured(self, messages: Any, schema: Any, *, alias: str, **kw: Any) -> Any:
        return ShortAnswerGrade(score=self._score, feedback="ok")


async def test_mcq_correct_by_index() -> None:
    result = await GradingService(None).grade(_mcq(1), answer="1")  # type: ignore[arg-type]
    assert result.correct
    assert result.score == 1.0


async def test_mcq_wrong_by_index() -> None:
    result = await GradingService(None).grade(_mcq(1), answer="3")  # type: ignore[arg-type]
    assert not result.correct
    assert result.score == 0.0


async def test_mcq_correct_by_option_text() -> None:
    result = await GradingService(None).grade(_mcq(2), answer="Gamma")  # type: ignore[arg-type]
    assert result.correct


async def test_flashcard_self_rating() -> None:
    svc = GradingService(None)  # type: ignore[arg-type]
    assert (await svc.grade(_flashcard(), self_rating="easy")).score == 1.0
    assert not (await svc.grade(_flashcard(), self_rating="again")).correct


async def test_short_passes_above_threshold() -> None:
    result = await GradingService(_FakeGateway(0.8)).grade(_short(), answer="because scales differ")
    assert result.correct
    assert result.score == 0.8


async def test_short_fails_below_threshold() -> None:
    result = await GradingService(_FakeGateway(0.3)).grade(_short(), answer="dunno")
    assert not result.correct
