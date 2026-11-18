"""Skill model: Elo/IRT-style mastery updates.

Mastery is stored in [0,1] but updated on the logit scale against the question's
difficulty, so a correct answer on a hard question moves mastery more than on an
easy one (and a wrong answer on an easy question hurts more). Confidence grows
with the number of attempts and decays with time since the last evidence.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.skill import SkillEvent, SkillState

K = 0.3  # learning rate on the logit scale
CONFIDENCE_HALFLIFE_DAYS = 30.0
# Map question difficulty 1..5 to a logit: higher difficulty = higher threshold.
_DIFFICULTY_LOGIT = {1: -2.0, 2: -1.0, 3: 0.0, 4: 1.0, 5: 2.0}


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass(frozen=True)
class MasteryUpdate:
    mastery: float
    confidence: float
    delta: float


def update_mastery(
    *,
    mastery: float,
    attempts: int,
    difficulty: int,
    outcome: float,
    days_since_last: float = 0.0,
    k: float = K,
) -> MasteryUpdate:
    """Return the new mastery/confidence after one graded answer.

    ``outcome`` is in [0,1] (1 = fully correct). Mastery moves by
    ``k * (outcome - expected)`` on the logit scale, where ``expected`` is the
    probability of a correct answer given mastery and difficulty.
    """
    difficulty_logit = _DIFFICULTY_LOGIT.get(difficulty, 0.0)
    mastery_logit = _logit(mastery)
    expected = _sigmoid(mastery_logit - difficulty_logit)
    new_mastery = _sigmoid(mastery_logit + k * (outcome - expected))

    new_attempts = attempts + 1
    growth = 1.0 - 1.0 / (1.0 + new_attempts)  # more evidence -> higher confidence
    decay = 0.5 ** (days_since_last / CONFIDENCE_HALFLIFE_DAYS)
    new_confidence = max(0.0, min(1.0, growth * decay))

    return MasteryUpdate(
        mastery=new_mastery, confidence=new_confidence, delta=new_mastery - mastery
    )


class SkillsService:
    """Persists mastery updates and an audit event per graded answer."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_outcome(
        self,
        *,
        user_id: uuid.UUID,
        topic_ids: list[str],
        source: str,
        outcome: float,
        difficulty: int,
        evidence_ref: str | None = None,
    ) -> list[SkillState]:
        now = datetime.now(UTC)
        updated: list[SkillState] = []
        for topic_id in topic_ids:
            state = await self._session.get(SkillState, (user_id, topic_id))
            if state is None:
                # Column defaults are DB-side (applied on flush); set them here so
                # the transient row has usable values before the first update.
                state = SkillState(
                    user_id=user_id, topic_id=topic_id, mastery=0.5, confidence=0.0, attempts=0
                )
                self._session.add(state)

            days_since = (
                (now - state.last_evidence_at).total_seconds() / 86400.0
                if state.last_evidence_at is not None
                else 0.0
            )
            result = update_mastery(
                mastery=state.mastery,
                attempts=state.attempts,
                difficulty=difficulty,
                outcome=outcome,
                days_since_last=days_since,
            )
            state.mastery = result.mastery
            state.confidence = result.confidence
            state.attempts += 1
            state.last_evidence_at = now

            self._session.add(
                SkillEvent(
                    user_id=user_id,
                    topic_id=topic_id,
                    source=source,
                    delta=result.delta,
                    evidence_ref=evidence_ref,
                )
            )
            updated.append(state)

        await self._session.flush()
        return updated
