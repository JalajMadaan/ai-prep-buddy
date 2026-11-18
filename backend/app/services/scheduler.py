"""Spaced repetition via FSRS.

Maps a quiz outcome to an FSRS rating and schedules the next review. FSRS models
the forgetting curve (stability + difficulty per card) and picks the interval that
lands near a target recall probability — far better than fixed doubling intervals.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, cast

from fsrs import Card, Rating, Scheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.review_card import ReviewCard

_scheduler = Scheduler()
_RATING: dict[str, Rating] = {
    "again": Rating.Again,
    "hard": Rating.Hard,
    "good": Rating.Good,
    "easy": Rating.Easy,
}


def rating_from_outcome(correct: bool) -> str:
    """Map a graded MCQ/short outcome to an FSRS rating."""
    return "good" if correct else "again"


def schedule(
    fsrs_state: dict[str, Any] | None, rating: str
) -> tuple[dict[str, Any], datetime, datetime]:
    """Advance a card by one review. Returns (new fsrs_state, due_at, reviewed_at)."""
    # fsrs types the dict as a CardDict TypedDict; we store/return a plain dict.
    card = Card.from_dict(cast(Any, fsrs_state)) if fsrs_state else Card()
    reviewed, _log = _scheduler.review_card(card, _RATING[rating])
    state = cast("dict[str, Any]", reviewed.to_dict())
    last_review = reviewed.last_review
    assert last_review is not None  # set by review_card
    return state, reviewed.due, last_review


class SchedulerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def review(
        self, *, user_id: uuid.UUID, question_id: uuid.UUID, rating: str
    ) -> ReviewCard:
        card = await self._session.get(ReviewCard, (user_id, question_id))
        state, due_at, reviewed_at = schedule(card.fsrs_state if card else None, rating)
        if card is None:
            card = ReviewCard(
                user_id=user_id,
                question_id=question_id,
                fsrs_state=state,
                due_at=due_at,
                last_review_at=reviewed_at,
            )
            self._session.add(card)
        else:
            card.fsrs_state = state
            card.due_at = due_at
            card.last_review_at = reviewed_at
        await self._session.flush()
        return card
