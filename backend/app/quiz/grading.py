"""Grading: MCQ by exact match, short answers by the fast model, flashcards self-rated."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from app.db.models.question import Question, Rubric
from app.llm.gateway import Gateway
from app.prompts.registry import render_prompt

# Flashcards are self-rated; map the rating to a 0..1 score.
_RATING_SCORE: dict[str, float] = {"again": 0.0, "hard": 0.4, "good": 0.8, "easy": 1.0}
SHORT_PASS = 0.6  # score at/above which a short answer counts as "correct"


class ShortAnswerGrade(BaseModel):
    score: float
    feedback: str = ""


@dataclass(frozen=True)
class GradeResult:
    correct: bool
    score: float
    explanation: str


class GradingService:
    def __init__(self, gateway: Gateway) -> None:
        self._gateway = gateway

    async def grade(
        self,
        question: Question,
        *,
        answer: str = "",
        self_rating: str | None = None,
        rubric: Rubric | None = None,
    ) -> GradeResult:
        if question.kind == "mcq":
            return self._grade_mcq(question, answer)
        if question.kind == "flashcard":
            return self._grade_flashcard(self_rating)
        if question.kind == "short":
            return await self._grade_short(question, answer, rubric)
        raise ValueError(f"Cannot grade question kind: {question.kind}")

    def _grade_mcq(self, question: Question, answer: str) -> GradeResult:
        correct_index = question.answer.get("correct_index")
        chosen: int | None = None
        value = answer.strip()
        if value.isdigit():
            chosen = int(value)
        else:
            options = [str(o).strip().lower() for o in question.options]
            if value.lower() in options:
                chosen = options.index(value.lower())
        correct = chosen is not None and chosen == correct_index
        return GradeResult(
            correct=correct, score=1.0 if correct else 0.0, explanation=question.explanation or ""
        )

    def _grade_flashcard(self, self_rating: str | None) -> GradeResult:
        score = _RATING_SCORE.get((self_rating or "").lower(), 0.0)
        return GradeResult(correct=score >= 0.8, score=score, explanation="")

    async def _grade_short(
        self, question: Question, answer: str, rubric: Rubric | None
    ) -> GradeResult:
        dims = rubric.dimensions if rubric else []
        rubric_text = "\n".join(
            f"- {d.get('key')} (weight {d.get('weight', 1)}): {d.get('description', '')}"
            for d in dims
        )
        prompt = render_prompt(
            "short_grade",
            1,
            question=question.text,
            reference=str(question.answer.get("reference", "")),
            rubric=rubric_text or "(no rubric; judge correctness)",
            answer=answer,
        )
        grade = await self._gateway.structured(
            [{"role": "user", "content": prompt}], ShortAnswerGrade, alias="fast"
        )
        score = max(0.0, min(1.0, grade.score))
        return GradeResult(
            correct=score >= SHORT_PASS,
            score=score,
            explanation=grade.feedback or question.explanation or "",
        )
