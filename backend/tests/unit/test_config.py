"""Tests for typed settings and env overrides."""

import pytest

from app.config import Settings, get_settings


def test_defaults_load() -> None:
    s = Settings(_env_file=None)  # ignore any local .env for a deterministic check
    assert s.app_env == "local"
    assert s.log_level == "INFO"
    assert s.rate_limit_per_min == 30
    assert s.is_prod is False


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "99")
    s = Settings(_env_file=None)
    assert s.app_env == "prod"
    assert s.is_prod is True
    assert s.rate_limit_per_min == 99


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
