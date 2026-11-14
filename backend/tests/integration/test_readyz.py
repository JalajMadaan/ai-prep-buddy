"""Integration test: /readyz against real infra (requires `make up`)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.integration
def test_readyz_reports_all_services_up() -> None:
    with TestClient(app) as client:
        r = client.get("/readyz")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "ok"
    assert body["checks"] == {"postgres": True, "redis": True, "qdrant": True}
