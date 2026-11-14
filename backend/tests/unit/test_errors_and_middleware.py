"""Tests for domain-error mapping and the request-id middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import NotFoundError, register_exception_handlers
from app.core.middleware import REQUEST_ID_HEADER, request_id_middleware


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.middleware("http")(request_id_middleware)
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> dict[str, str]:
        raise NotFoundError("no such thing")

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    return TestClient(app, raise_server_exceptions=False)


def test_domain_error_maps_to_stable_json(client: TestClient) -> None:
    r = client.get("/boom")
    assert r.status_code == 404
    error = r.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["message"] == "no such thing"
    assert error["request_id"]  # populated from the middleware-set context


def test_request_id_header_present_and_matches_body(client: TestClient) -> None:
    r = client.get("/boom")
    header_id = r.headers[REQUEST_ID_HEADER]
    assert header_id
    assert r.json()["error"]["request_id"] == header_id


def test_incoming_request_id_is_propagated(client: TestClient) -> None:
    r = client.get("/ok", headers={REQUEST_ID_HEADER: "my-fixed-id"})
    assert r.headers[REQUEST_ID_HEADER] == "my-fixed-id"


def test_ok_route_still_works(client: TestClient) -> None:
    r = client.get("/ok")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
