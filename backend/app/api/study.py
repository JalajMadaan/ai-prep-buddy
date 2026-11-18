"""Study assistant API: conversations + ask (streamed cited answer over SSE)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, get_current_user
from app.db.repositories.conversations import ConversationRepository
from app.db.repositories.users import UserRepository
from app.db.session import get_session
from app.services.study import build_study_service

router = APIRouter(prefix="/v1/study", tags=["study"])


class CreateConversationRequest(BaseModel):
    title: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    conversation_id: UUID | None = None
    style: Literal["concise", "interview", "deep"] = "interview"
    topic_filter: list[str] | None = None


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/conversations")
async def create_conversation(
    req: CreateConversationRequest,
    user: Annotated[Principal, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    # Ensure the (dev) user row exists so the FK holds; real users exist via OAuth (M7).
    await UserRepository(session).ensure(user.id, display_name=user.display_name)
    conv = await ConversationRepository(session).create(user_id=user.id, title=req.title)
    await session.commit()
    return {"id": str(conv.id)}


@router.post("/ask")
async def ask(
    req: AskRequest, _user: Annotated[Principal, Depends(get_current_user)]
) -> StreamingResponse:
    service = build_study_service()

    async def stream() -> AsyncIterator[str]:
        async for event, data in service.ask(
            req.question,
            conversation_id=req.conversation_id,
            style=req.style,
            topic_ids=req.topic_filter,
        ):
            yield _sse(event, data)

    return StreamingResponse(stream(), media_type="text/event-stream")
