"""Admin API (owner-only in prod; dev auth for now): moderate the question bank."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.question_index import QdrantQuestionIndex
from app.adapters.vector_store import QdrantVectorStore
from app.api.deps import Principal, get_current_user
from app.core.errors import NotFoundError
from app.db.repositories.questions import QuestionRepository
from app.db.session import get_session
from app.llm.gateway import Gateway
from app.quiz.generator import QuestionGenerator
from app.rag.retriever import HybridRetriever

router = APIRouter(prefix="/v1/admin", tags=["admin"])


class GenerateRequest(BaseModel):
    topic_id: str
    count: int = Field(default=3, ge=1, le=20)


def _question_dict(q: object) -> dict[str, object]:
    return {
        "id": str(q.id),  # type: ignore[attr-defined]
        "kind": q.kind,  # type: ignore[attr-defined]
        "text": q.text,  # type: ignore[attr-defined]
        "options": q.options,  # type: ignore[attr-defined]
        "topic_ids": q.topic_ids,  # type: ignore[attr-defined]
        "difficulty": q.difficulty,  # type: ignore[attr-defined]
        "status": q.status,  # type: ignore[attr-defined]
        "created_by": q.created_by,  # type: ignore[attr-defined]
    }


@router.get("/questions")
async def list_questions(
    _user: Annotated[Principal, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    status: Annotated[str, Query()] = "draft",
) -> list[dict[str, object]]:
    questions = await QuestionRepository(session).list(status=status, limit=200)
    return [_question_dict(q) for q in questions]


@router.post("/questions/{qid}/{action}")
async def moderate(
    qid: UUID,
    action: Literal["approve", "retire"],
    _user: Annotated[Principal, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    new_status = "approved" if action == "approve" else "retired"
    question = await QuestionRepository(session).set_status(qid, new_status)
    if question is None:
        raise NotFoundError(f"Question {qid} not found")
    await session.commit()
    return {"id": str(qid), "status": new_status}


@router.post("/questions/generate")
async def generate_questions(
    req: GenerateRequest,
    _user: Annotated[Principal, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    index = QdrantQuestionIndex()
    generator = QuestionGenerator(
        HybridRetriever(QdrantVectorStore()), Gateway(), QuestionRepository(session), index
    )
    report = await generator.generate_for_topic(req.topic_id, count=req.count)
    await session.commit()
    return {"accepted": report.accepted, "rejected": report.rejected}
