"""Request-scoped context shared by logging and middleware.

A ``ContextVar`` carries the current request id through the async call stack so
we do not have to thread it through every function signature. The middleware
sets it per request; the logging processor reads it for every log line.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str) -> Token[str | None]:
    """Bind ``request_id`` to the current context; return a reset token."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the previous request id using the token from :func:`set_request_id`."""
    _request_id.reset(token)


def get_request_id() -> str | None:
    """Return the request id bound to the current context, if any."""
    return _request_id.get()
