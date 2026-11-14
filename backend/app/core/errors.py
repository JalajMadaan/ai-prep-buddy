"""Domain errors and their HTTP mapping.

Services raise :class:`AppError` subclasses — transport-agnostic, each with a
stable machine-readable ``code``. One exception handler maps them to a consistent
JSON body ``{"error": {"code", "message", "request_id"}}`` so clients can branch
on ``code`` rather than on brittle message text. Keeping these out of the service
layer is what lets services avoid importing FastAPI (see CLAUDE.md §5 layering).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.context import get_request_id


class AppError(Exception):
    """Base class for all domain errors.

    Subclasses set a stable ``code`` and an HTTP ``status_code``. The ``message``
    is human-readable and safe to return to clients (never put secrets/PII here).
    """

    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.__name__
        super().__init__(self.message)


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 422


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"
    status_code = 401


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    status_code = 403


class RateLimitedError(AppError):
    code = "RATE_LIMITED"
    status_code = 429


class QuotaExceededError(AppError):
    code = "QUOTA_EXCEEDED"
    status_code = 429


class BudgetExceededError(AppError):
    code = "BUDGET_EXCEEDED"
    status_code = 429


class UpstreamError(AppError):
    code = "UPSTREAM_ERROR"
    status_code = 502


def _error_body(code: str, message: str) -> dict[str, dict[str, str | None]]:
    return {"error": {"code": code, "message": message, "request_id": get_request_id()}}


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Map a domain error to the stable error JSON shape."""
    return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message))


async def unhandled_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Last-resort handler: return a generic 500 without leaking internals."""
    return JSONResponse(
        status_code=500, content=_error_body("INTERNAL_ERROR", "Internal server error")
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire the domain and catch-all exception handlers onto the app."""
    # Handler takes the narrower AppError; Starlette types it as Exception.
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)
