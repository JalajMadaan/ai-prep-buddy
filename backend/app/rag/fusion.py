"""Reciprocal rank fusion (RRF): combine ranked lists by rank, not raw score.

Dense (cosine) and sparse (BM25) scores live on different scales, so adding or
averaging them is meaningless. RRF ignores the scores and uses only each item's
*rank* in each list, which makes it scale-free and robust.
"""

from __future__ import annotations

from collections.abc import Sequence


def reciprocal_rank_fusion[T](
    ranked_lists: Sequence[Sequence[T]], k: int = 60
) -> list[tuple[T, float]]:
    """Fuse several ranked lists into one ranking.

    Each inner list is items in rank order (best first). An item's fused score is
    the sum over all lists of ``1 / (k + rank)`` with ``rank`` 1-based; an item
    missing from a list contributes nothing from that list. Larger ``k`` flattens
    the gap between ranks.

    Returns ``(item, score)`` pairs sorted by score descending; ties keep
    first-seen order (stable).
    """
    scores: dict[T, float] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
