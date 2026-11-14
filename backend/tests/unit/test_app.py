"""Unit tests for the app factory: health, metrics, readiness logic."""

import pytest
from fastapi.testclient import TestClient

import app.api.health as health
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_metrics_exposes_request_histogram(client: TestClient) -> None:
    client.get("/healthz")  # record one observation first
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "http_request" in r.text


async def _ok() -> bool:
    return True


async def _down() -> bool:
    return False


def test_readyz_ok_when_all_up(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "_check_postgres", _ok)
    monkeypatch.setattr(health, "_check_redis", _ok)
    monkeypatch.setattr(health, "_check_qdrant", _ok)
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readyz_503_when_redis_down(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "_check_postgres", _ok)
    monkeypatch.setattr(health, "_check_redis", _down)
    monkeypatch.setattr(health, "_check_qdrant", _ok)
    r = client.get("/readyz")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["checks"]["redis"] is False
