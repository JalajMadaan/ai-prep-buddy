"""Structured JSON logging via structlog.

Every log line is JSON and carries the current ``request_id`` (from the request
context) so all logs for one request correlate. Call :func:`setup_logging` once
at startup; obtain loggers via :func:`get_logger`.
"""

from __future__ import annotations

import logging
from typing import Any, cast

import structlog
from structlog.types import EventDict, Processor

from app.config import get_settings
from app.core.context import get_request_id


def add_request_id(_logger: Any, _method: str, event_dict: EventDict) -> EventDict:
    """structlog processor: attach the current request id to every event."""
    request_id = get_request_id()
    if request_id is not None:
        event_dict["request_id"] = request_id
    return event_dict


def setup_logging(log_level: str | None = None) -> None:
    """Configure structlog to emit JSON with a request id on every line."""
    level_name = log_level or get_settings().log_level
    level = logging.getLevelNamesMapping().get(level_name, logging.INFO)

    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(*names: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger (optionally named)."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(*names))
