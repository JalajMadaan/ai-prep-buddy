"""Tests for FSRS scheduling."""

from app.services.scheduler import rating_from_outcome, schedule


def test_rating_from_outcome() -> None:
    assert rating_from_outcome(True) == "good"
    assert rating_from_outcome(False) == "again"


def test_again_is_sooner_than_good_which_is_sooner_than_easy() -> None:
    _, again_due, _ = schedule(None, "again")
    _, good_due, _ = schedule(None, "good")
    _, easy_due, _ = schedule(None, "easy")
    assert again_due < good_due
    assert good_due <= easy_due


def test_repeated_good_pushes_due_further_out() -> None:
    first_state, _, _ = schedule(None, "good")
    _, second_due, _ = schedule(first_state, "good")
    _, fresh_due, _ = schedule(None, "good")
    assert second_due >= fresh_due
