"""Question bank + rubric repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.question import Question, Rubric


class RubricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self, *, name: str, version: int, dimensions: list[dict[str, Any]], anchors: dict[str, Any]
    ) -> Rubric:
        result = await self._session.execute(
            select(Rubric).where(Rubric.name == name, Rubric.version == version)
        )
        rubric = result.scalars().one_or_none()
        if rubric is None:
            rubric = Rubric(name=name, version=version, dimensions=dimensions, anchors=anchors)
            self._session.add(rubric)
        else:
            rubric.dimensions = dimensions
            rubric.anchors = anchors
        await self._session.flush()
        return rubric


class QuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_ext_key(self, ext_key: str) -> Question | None:
        result = await self._session.execute(select(Question).where(Question.ext_key == ext_key))
        return result.scalars().one_or_none()

    async def upsert(self, *, ext_key: str, **fields: Any) -> Question:
        question = await self.get_by_ext_key(ext_key)
        if question is None:
            question = Question(ext_key=ext_key, **fields)
            self._session.add(question)
        else:
            for key, value in fields.items():
                setattr(question, key, value)
        await self._session.flush()
        return question

    async def list(
        self, *, status: str | None = None, kind: str | None = None, limit: int = 100
    ) -> Sequence[Question]:
        stmt = select(Question)
        if status is not None:
            stmt = stmt.where(Question.status == status)
        if kind is not None:
            stmt = stmt.where(Question.kind == kind)
        stmt = stmt.order_by(Question.id).limit(limit)
        return (await self._session.execute(stmt)).scalars().all()

    async def get(self, question_id: uuid.UUID) -> Question | None:
        return await self._session.get(Question, question_id)
