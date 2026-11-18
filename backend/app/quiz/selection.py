"""Daily-drill selection: due cards first, then weakest topics, mixed kinds.

Pure and deterministic (seeded) so it is easy to unit-test each rule.
"""

from __future__ import annotations

import random
import uuid
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class DrillCandidate:
    id: uuid.UUID
    kind: str
    difficulty: int
    topic_ids: list[str]


def select_drill(
    candidates: Sequence[DrillCandidate],
    *,
    due_ids: set[uuid.UUID],
    mastery_by_topic: dict[str, float],
    seen_ids: set[uuid.UUID],
    size: int,
    seed: int = 0,
) -> list[uuid.UUID]:
    """Pick up to ``size`` question ids for a drill.

    Order: due-for-review first, then weakest topic (lowest mastery), with a
    seeded tie-breaker. Questions seen recently (``seen_ids``) are excluded, and
    no single kind exceeds ~60% of the drill unless there's nothing else to fill it.
    """
    rng = random.Random(seed)
    pool = [c for c in candidates if c.id not in seen_ids]

    def weakness(c: DrillCandidate) -> float:
        return min((mastery_by_topic.get(t, 0.5) for t in c.topic_ids), default=0.5)

    pool.sort(key=lambda c: (0 if c.id in due_ids else 1, weakness(c), rng.random()))

    cap = max(1, (size * 3) // 5)
    chosen: list[uuid.UUID] = []
    taken: set[uuid.UUID] = set()
    counts: dict[str, int] = {}
    for c in pool:
        if len(chosen) >= size:
            break
        if counts.get(c.kind, 0) < cap:
            chosen.append(c.id)
            taken.add(c.id)
            counts[c.kind] = counts.get(c.kind, 0) + 1

    # Fill any remaining slots ignoring the per-kind cap.
    for c in pool:
        if len(chosen) >= size:
            break
        if c.id not in taken:
            chosen.append(c.id)
            taken.add(c.id)

    return chosen
