"""Quiz service: build the daily drill, grade answers, update skills + schedule."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models.question import Question, Rubric
from app.db.models.quiz_session import QuizSession
from app.db.repositories.questions import QuestionRepository
from app.db.repositories.quiz import QuizRepository
from app.llm.gateway import Gateway
from app.quiz.grading import GradingService
from app.quiz.selection import DrillCandidate, select_drill
from app.services.scheduler import SchedulerService, rating_from_outcome
from app.services.skills import SkillsService

DEFAULT_DRILL_SIZE = 10


class QuizService:
    def __init__(self, session: AsyncSession, gateway: Gateway) -> None:
        self._session = session
        self._gateway = gateway

    async def build_today(
        self, user_id: uuid.UUID, *, size: int = DEFAULT_DRILL_SIZE, seed: int = 0
    ) -> tuple[QuizSession, list[Question]]:
        quiz_repo = QuizRepository(self._session)
        approved = list(await QuestionRepository(self._session).list(status="approved", limit=500))
        candidates = [
            DrillCandidate(
                id=q.id, kind=q.kind, difficulty=q.difficulty, topic_ids=list(q.topic_ids)
            )
            for q in approved
        ]
        ids = select_drill(
            candidates,
            due_ids=await quiz_repo.due_question_ids(user_id),
            mastery_by_topic=await quiz_repo.mastery_by_topic(user_id),
            seen_ids=await quiz_repo.recently_seen(user_id),
            size=size,
            seed=seed,
        )
        quiz = await quiz_repo.create_session(user_id=user_id, question_ids=ids)
        by_id = {q.id: q for q in approved}
        return quiz, [by_id[i] for i in ids]

    async def answer(
        self,
        user_id: uuid.UUID,
        *,
        quiz_session_id: uuid.UUID,
        question_id: uuid.UUID,
        answer: str = "",
        self_rating: str | None = None,
    ) -> dict[str, Any]:
        question = await QuestionRepository(self._session).get(question_id)
        if question is None:
            raise NotFoundError(f"Question {question_id} not found")
        rubric = await self._session.get(Rubric, question.rubric_id) if question.rubric_id else None

        grade = await GradingService(self._gateway).grade(
            question, answer=answer, self_rating=self_rating, rubric=rubric
        )
        await QuizRepository(self._session).record_answer(
            quiz_session_id=quiz_session_id,
            question_id=question_id,
            user_id=user_id,
            answer=answer,
            correct=grade.correct,
            score=grade.score,
        )
        await SkillsService(self._session).record_outcome(
            user_id=user_id,
            topic_ids=list(question.topic_ids),
            source="quiz",
            outcome=grade.score,
            difficulty=question.difficulty,
            evidence_ref=str(question_id),
        )
        rating = (
            self_rating
            if question.kind == "flashcard" and self_rating
            else rating_from_outcome(grade.correct)
        )
        card = await SchedulerService(self._session).review(
            user_id=user_id, question_id=question_id, rating=rating
        )
        return {
            "correct": grade.correct,
            "score": grade.score,
            "explanation": grade.explanation,
            "next_due_at": card.due_at.isoformat(),
        }

    async def finish(self, session_id: uuid.UUID) -> dict[str, Any]:
        quiz_repo = QuizRepository(self._session)
        quiz = await quiz_repo.get_session(session_id)
        if quiz is None:
            raise NotFoundError(f"Quiz session {session_id} not found")
        quiz.finished_at = datetime.now(UTC)
        answers = await quiz_repo.answers_for_session(session_id)
        await self._session.flush()
        return {
            "total": len(answers),
            "correct": sum(1 for a in answers if a.correct),
        }
