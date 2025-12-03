"""Shared logging utilities with structured JSON output."""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Mapping


class JsonFormatter(logging.Formatter):
    """Format log records as JSON with common context fields."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting logic
        log_record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in (
            "tool_name",
            "request_id",
            "query_params",
            "citation_count",
            "elapsed_ms",
            "event",
        ):
            value = getattr(record, field, None)
            if value is not None:
                log_record[field] = value

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)


def log_event(
    logger: logging.Logger,
    message: str,
    *,
    level: int = logging.INFO,
    tool_name: str | None = None,
    request_id: str | None = None,
    query_params: Mapping[str, Any] | None = None,
    citation_count: int | None = None,
    event: str | None = None,
    extra_context: Mapping[str, Any] | None = None,
) -> None:
    """Log a single structured event."""

    context: dict[str, Any] = {
        "tool_name": tool_name,
        "request_id": request_id,
        "query_params": dict(query_params) if query_params else None,
        "citation_count": citation_count,
        "event": event,
    }

    if extra_context:
        context.update(extra_context)

    logger.log(level, message, extra=context)


@contextmanager
def log_operation(
    logger: logging.Logger,
    *,
    tool_name: str,
    request_id: str | None,
    query_params: Mapping[str, Any] | None,
    event: str,
    extra_context: Mapping[str, Any] | None = None,
):
    """Log the start/end of an operation with elapsed time."""

    context: dict[str, Any] = {
        "tool_name": tool_name,
        "request_id": request_id,
        "query_params": dict(query_params) if query_params else None,
        "event": event,
    }

    if extra_context:
        context.update(extra_context)

    logger.info("Starting %s", event, extra=context)
    start = time.perf_counter()

    try:
        yield
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000
        failure_context = {**context, "elapsed_ms": round(elapsed_ms, 2)}
        logger.exception("%s failed", event, extra=failure_context)
        raise
    else:
        elapsed_ms = (time.perf_counter() - start) * 1000
        success_context = {**context, "elapsed_ms": round(elapsed_ms, 2)}
        logger.info("Finished %s", event, extra=success_context)
