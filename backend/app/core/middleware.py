"""HTTP middleware: assign and propagate a request id.

Reads an inbound ``X-Request-ID`` (so a client or gateway can supply one) or
generates a fresh id, binds it to the request context for logging, and echoes it
on the response. Wired onto the app in M0-T5.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response

from app.core.context import reset_request_id, set_request_id

REQUEST_ID_HEADER = "X-Request-ID"


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Ensure every request has a request id, in context and on the response."""
    request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
    finally:
        reset_request_id(token)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
