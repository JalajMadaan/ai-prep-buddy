"""Quiz session/answer repository + the data a drill needs (due, mastery, seen)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.quiz_session import QuizAnswer, QuizSession
from app.db.models.review_card import ReviewCard
from app.db.models.skill import SkillState


class QuizRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(
        self, *, user_id: uuid.UUID, question_ids: list[uuid.UUID]
    ) -> QuizSession:
        quiz = QuizSession(user_id=user_id, question_ids=question_ids)
        self._session.add(quiz)
        await self._session.flush()
        return quiz

    async def get_session(self, session_id: uuid.UUID) -> QuizSession | None:
        return await self._session.get(QuizSession, session_id)

    async def record_answer(
        self,
        *,
        quiz_session_id: uuid.UUID,
        question_id: uuid.UUID,
        user_id: uuid.UUID,
        answer: str,
        correct: bool,
        score: float,
    ) -> QuizAnswer:
        row = QuizAnswer(
            quiz_session_id=quiz_session_id,
            question_id=question_id,
            user_id=user_id,
            answer_masked=answer,
            correct=correct,
            score=score,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def recently_seen(self, user_id: uuid.UUID, *, days: int = 14) -> set[uuid.UUID]:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        rows = await self._session.execute(
            select(QuizAnswer.question_id).where(
                QuizAnswer.user_id == user_id, QuizAnswer.created_at >= cutoff
            )
        )
        return set(rows.scalars().all())

    async def due_question_ids(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        rows = await self._session.execute(
            select(ReviewCard.question_id).where(
                ReviewCard.user_id == user_id, ReviewCard.due_at <= datetime.now(UTC)
            )
        )
        return set(rows.scalars().all())

    async def mastery_by_topic(self, user_id: uuid.UUID) -> dict[str, float]:
        rows = await self._session.execute(
            select(SkillState.topic_id, SkillState.mastery).where(SkillState.user_id == user_id)
        )
        return dict(rows.all())

    async def answers_for_session(self, session_id: uuid.UUID) -> list[QuizAnswer]:
        rows = await self._session.execute(
            select(QuizAnswer).where(QuizAnswer.quiz_session_id == session_id)
        )
        return list(rows.scalars().all())
