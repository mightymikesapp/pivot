"""Shared logging utilities with structured JSON output."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any, Mapping

from app.logging_config import JsonFormatter, correlation_id_ctx, request_metadata_ctx


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

    correlation_id = correlation_id_ctx.get()
    metadata = request_metadata_ctx.get()
    context: dict[str, Any] = {
        "tool_name": tool_name or metadata.get("tool_name"),
        "request_id": request_id or correlation_id,
        "query_params": dict(query_params) if query_params else None,
        "citation_count": citation_count,
        "event": event,
    }

    if correlation_id:
        context["correlation_id"] = correlation_id
    if metadata.get("citation"):
        context["citation"] = metadata.get("citation")

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
) -> Iterator[None]:
    """Log the start/end of an operation with elapsed time."""

    correlation_id = correlation_id_ctx.get()
    metadata = request_metadata_ctx.get()
    context: dict[str, Any] = {
        "tool_name": tool_name or metadata.get("tool_name"),
        "request_id": request_id or correlation_id,
        "query_params": dict(query_params) if query_params else None,
        "event": event,
    }

    if correlation_id:
        context["correlation_id"] = correlation_id
    if metadata.get("citation"):
        context["citation"] = metadata.get("citation")

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
