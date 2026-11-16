"""Unit tests for reciprocal rank fusion."""

import pytest

from app.rag.fusion import reciprocal_rank_fusion


def test_single_list_preserves_order_with_decreasing_scores() -> None:
    out = reciprocal_rank_fusion([["a", "b", "c"]], k=60)
    assert [item for item, _ in out] == ["a", "b", "c"]
    assert out[0][1] > out[1][1] > out[2][1]


def test_item_in_both_lists_ranks_highest() -> None:
    # "b" appears in both lists, so it should beat items that appear once.
    out = reciprocal_rank_fusion([["a", "b"], ["b", "c"]], k=60)
    assert out[0][0] == "b"


def test_missing_ids_contribute_nothing() -> None:
    scores = dict(reciprocal_rank_fusion([["a", "b"], ["a"]], k=60))
    assert scores["a"] == pytest.approx(1 / 61 + 1 / 61)  # rank 1 in both lists
    assert scores["b"] == pytest.approx(1 / 62)  # rank 2 in list 1 only


def test_larger_k_flattens_differences() -> None:
    small_k = reciprocal_rank_fusion([["a", "b"]], k=1)
    large_k = reciprocal_rank_fusion([["a", "b"]], k=1000)
    gap_small = small_k[0][1] - small_k[1][1]
    gap_large = large_k[0][1] - large_k[1][1]
    assert gap_small > gap_large


def test_ties_keep_first_seen_order() -> None:
    out = reciprocal_rank_fusion([["x"], ["y"]], k=60)
    assert {item for item, _ in out} == {"x", "y"}
    assert out[0][1] == out[1][1]  # equal score (both rank 1 in one list)
    assert [item for item, _ in out] == ["x", "y"]  # x was seen first
