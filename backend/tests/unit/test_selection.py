"""Tests for the daily-drill selection rules."""

import uuid

from app.quiz.selection import DrillCandidate, select_drill


def _c(kind: str = "mcq", difficulty: int = 3, topics: list[str] | None = None) -> DrillCandidate:
    return DrillCandidate(
        id=uuid.uuid4(), kind=kind, difficulty=difficulty, topic_ids=topics or ["t"]
    )


def test_excludes_seen() -> None:
    a, b = _c(), _c()
    ids = select_drill([a, b], due_ids=set(), mastery_by_topic={}, seen_ids={a.id}, size=10, seed=1)
    assert a.id not in ids
    assert b.id in ids


def test_due_cards_come_first() -> None:
    due, other = _c(topics=["x"]), _c(topics=["x"])
    ids = select_drill(
        [other, due],
        due_ids={due.id},
        mastery_by_topic={"x": 0.5},
        seen_ids=set(),
        size=10,
        seed=1,
    )
    assert ids[0] == due.id


def test_weaker_topic_prioritised() -> None:
    weak = _c(topics=["weak"])
    strong = _c(topics=["strong"])
    ids = select_drill(
        [strong, weak],
        due_ids=set(),
        mastery_by_topic={"weak": 0.1, "strong": 0.9},
        seen_ids=set(),
        size=10,
        seed=1,
    )
    assert ids[0] == weak.id


def test_respects_size_and_is_deterministic() -> None:
    pool = [_c(topics=[f"t{i}"]) for i in range(20)]
    first = select_drill(pool, due_ids=set(), mastery_by_topic={}, seen_ids=set(), size=8, seed=42)
    again = select_drill(pool, due_ids=set(), mastery_by_topic={}, seen_ids=set(), size=8, seed=42)
    assert len(first) == 8
    assert first == again  # same seed -> same drill


def test_kind_cap_mixes_types() -> None:
    mcqs = [_c(kind="mcq", topics=[f"m{i}"]) for i in range(10)]
    shorts = [_c(kind="short", topics=[f"s{i}"]) for i in range(10)]
    ids = select_drill(
        mcqs + shorts, due_ids=set(), mastery_by_topic={}, seen_ids=set(), size=10, seed=1
    )
    by_id = {c.id: c for c in mcqs + shorts}
    kinds = {by_id[i].kind for i in ids}
    assert kinds == {"mcq", "short"}  # not all one kind
