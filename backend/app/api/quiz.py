"""Quiz API: daily drill, answer grading, finish."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, get_current_user
from app.db.models.question import Question
from app.db.repositories.users import UserRepository
from app.db.session import get_session
from app.llm.gateway import Gateway
from app.services.quiz import QuizService

router = APIRouter(prefix="/v1/quiz", tags=["quiz"])


class AnswerRequest(BaseModel):
    quiz_session_id: UUID
    question_id: UUID
    answer: str = ""
    self_rating: Literal["again", "hard", "good", "easy"] | None = None


def _question_public(q: Question) -> dict[str, Any]:
    # Never leak the answer/explanation to the client when serving a drill.
    return {
        "id": str(q.id),
        "kind": q.kind,
        "text": q.text,
        "options": q.options if q.kind == "mcq" else [],
        "topic_ids": q.topic_ids,
    }


@router.get("/today")
async def today(
    user: Annotated[Principal, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    await UserRepository(session).ensure(user.id, display_name=user.display_name)
    quiz, questions = await QuizService(session, Gateway()).build_today(user.id)
    await session.commit()
    return {"quiz_session_id": str(quiz.id), "questions": [_question_public(q) for q in questions]}


@router.post("/answer")
async def answer(
    req: AnswerRequest,
    user: Annotated[Principal, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    result = await QuizService(session, Gateway()).answer(
        user.id,
        quiz_session_id=req.quiz_session_id,
        question_id=req.question_id,
        answer=req.answer,
        self_rating=req.self_rating,
    )
    await session.commit()
    return result


@router.post("/sessions/{session_id}/finish")
async def finish(
    session_id: UUID,
    _user: Annotated[Principal, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    summary = await QuizService(session, Gateway()).finish(session_id)
    await session.commit()
    return {"summary": summary}
