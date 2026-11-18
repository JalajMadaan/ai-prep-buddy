"""Tests for the Elo-style mastery update (the M2-T4 acceptance criteria)."""

from app.services.skills import update_mastery


def test_correct_on_hard_raises_mastery_more_than_on_easy() -> None:
    hard = update_mastery(mastery=0.5, attempts=0, difficulty=5, outcome=1.0)
    easy = update_mastery(mastery=0.5, attempts=0, difficulty=1, outcome=1.0)
    assert hard.delta > easy.delta > 0


def test_wrong_on_easy_lowers_mastery_more_than_on_hard() -> None:
    easy = update_mastery(mastery=0.5, attempts=0, difficulty=1, outcome=0.0)
    hard = update_mastery(mastery=0.5, attempts=0, difficulty=5, outcome=0.0)
    assert easy.delta < hard.delta < 0


def test_mastery_stays_within_unit_interval() -> None:
    result = update_mastery(mastery=0.99, attempts=10, difficulty=1, outcome=1.0)
    assert 0.0 <= result.mastery <= 1.0


def test_confidence_grows_with_attempts() -> None:
    few = update_mastery(mastery=0.5, attempts=0, difficulty=3, outcome=1.0).confidence
    many = update_mastery(mastery=0.5, attempts=5, difficulty=3, outcome=1.0).confidence
    assert many > few


def test_confidence_decays_with_time_since_last_evidence() -> None:
    fresh = update_mastery(
        mastery=0.5, attempts=5, difficulty=3, outcome=1.0, days_since_last=0.0
    ).confidence
    stale = update_mastery(
        mastery=0.5, attempts=5, difficulty=3, outcome=1.0, days_since_last=60.0
    ).confidence
    assert stale < fresh
