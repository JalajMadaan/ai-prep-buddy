"""Study assistant API: ask a question, stream a cited answer over SSE."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import Principal, get_current_user
from app.services.study import build_study_service

router = APIRouter(prefix="/v1/study", tags=["study"])


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    style: Literal["concise", "interview", "deep"] = "interview"
    topic_filter: list[str] | None = None


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/ask")
async def ask(
    req: AskRequest, _user: Annotated[Principal, Depends(get_current_user)]
) -> StreamingResponse:
    service = build_study_service()

    async def stream() -> AsyncIterator[str]:
        async for event, data in service.ask(
            req.question, style=req.style, topic_ids=req.topic_filter
        ):
            yield _sse(event, data)

    return StreamingResponse(stream(), media_type="text/event-stream")
