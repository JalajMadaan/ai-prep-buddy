"""Citation verification: strip any [n] that doesn't map to a retrieved source.

The answer prompt numbers sources 1..N; a model can still emit a citation outside
that range (or hallucinate one), so we remove those and count them for the
``citation_invalid_rate`` metric.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.rag.retriever import RetrievedChunk

_CITATION = re.compile(r"\[(\d+)\]")


def verify_citations(answer: str, retrieved: Sequence[RetrievedChunk]) -> tuple[str, int]:
    """Return (answer with invalid [n] removed, count of invalid citations)."""
    valid_max = len(retrieved)
    invalid = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal invalid
        n = int(match.group(1))
        if 1 <= n <= valid_max:
            return match.group(0)
        invalid += 1
        return ""

    cleaned = _CITATION.sub(_replace, answer)
    return cleaned, invalid
