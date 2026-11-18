"""Skills API: the current user's mastery per topic (backs the skill-map view)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, get_current_user
from app.db.models.skill import SkillState
from app.db.session import get_session

router = APIRouter(prefix="/v1", tags=["skills"])


@router.get("/skills")
async def get_skills(
    user: Annotated[Principal, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    rows = await session.execute(
        select(SkillState).where(SkillState.user_id == user.id).order_by(SkillState.mastery)
    )
    topics = [
        {
            "topic_id": s.topic_id,
            "mastery": round(s.mastery, 3),
            "confidence": round(s.confidence, 3),
            "attempts": s.attempts,
        }
        for s in rows.scalars().all()
    ]
    return {"topics": topics}
