"""Tests for structured logging: JSON output carrying the request id."""

import contextvars
import json

import pytest

from app.core.context import reset_request_id, set_request_id
from app.core.logging import add_request_id, get_logger, setup_logging


def test_add_request_id_includes_id_when_set() -> None:
    token = set_request_id("req-123")
    try:
        out = add_request_id(None, "info", {"event": "hello"})
    finally:
        reset_request_id(token)
    assert out["request_id"] == "req-123"


def test_add_request_id_omitted_when_unset() -> None:
    # Run in a fresh context so the contextvar is guaranteed at its default.
    out = contextvars.Context().run(add_request_id, None, "info", {"event": "hello"})
    assert "request_id" not in out


def test_setup_logging_emits_json_with_request_id(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging("INFO")
    token = set_request_id("req-abc")
    try:
        get_logger("test").info("something_happened", foo="bar")
    finally:
        reset_request_id(token)

    line = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(line)
    assert data["request_id"] == "req-abc"
    assert data["event"] == "something_happened"
    assert data["foo"] == "bar"
    assert data["level"] == "info"
