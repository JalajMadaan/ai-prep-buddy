"""Tests for the prompt registry: load, render, versioning, validation."""

import pytest
from jinja2 import UndefinedError

from app.prompts.registry import (
    PromptNotFoundError,
    load_prompt,
    render_prompt,
)
from app.prompts.sync import validate_all


def test_load_parses_front_matter() -> None:
    p = load_prompt("study_rewrite", 1)
    assert p.meta.model == "fast"
    assert p.meta.temperature == 0.0
    assert p.meta.description


def test_render_substitutes_variables() -> None:
    out = render_prompt("study_rewrite", 1, history="We discussed LoRA.", question="and memory?")
    assert "and memory?" in out
    assert "We discussed LoRA." in out


def test_missing_version_raises() -> None:
    # Bumping a prompt requires adding a new vN file; v2 does not exist yet.
    with pytest.raises(PromptNotFoundError):
        load_prompt("study_rewrite", 2)


def test_unknown_prompt_raises() -> None:
    with pytest.raises(PromptNotFoundError):
        load_prompt("does_not_exist", 1)


def test_missing_variable_fails_loudly() -> None:
    with pytest.raises(UndefinedError):
        render_prompt("study_rewrite", 1, history="only history, no question")


def test_validate_all_passes() -> None:
    assert validate_all() >= 1
