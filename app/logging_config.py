"""Application-wide structured logging configuration and helpers."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from functools import wraps
from inspect import Signature, signature
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar, cast

correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)
request_metadata_ctx: ContextVar[dict[str, Any]] = ContextVar("request_metadata", default={})

P = ParamSpec("P")
R = TypeVar("R")


class JsonFormatter(logging.Formatter):
    """Format log records as structured JSON with contextual metadata."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting logic
        log_record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        correlation_id = correlation_id_ctx.get()
        if correlation_id:
            log_record["correlation_id"] = correlation_id

        metadata = request_metadata_ctx.get()
        if metadata:
            tool_name = metadata.get("tool_name")
            if tool_name:
                log_record["tool_name"] = tool_name
            citation = metadata.get("citation")
            if citation:
                log_record["citation"] = citation

        for field in (
            "elapsed_ms",
            "event",
            "query_params",
            "citation_count",
        ):
            value = getattr(record, field, None)
            if value is not None:
                log_record[field] = value

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)


def configure_logging(log_level: str, log_format: str, date_format: str | None = None) -> None:
    """Configure root logging with context-aware JSON output by default."""

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    handler = logging.StreamHandler()
    if log_format.lower() == "json":
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    handler.setFormatter(formatter)

    root_logger.handlers = [handler]


def _bind_context(tool_name: str, call_signature: Signature, args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Token[Any], Token[Any]]:
    correlation_token = correlation_id_ctx.set(str(uuid.uuid4()))

    bound = call_signature.bind_partial(*args, **kwargs)
    bound.apply_defaults()

    citation = bound.arguments.get("citation") or bound.arguments.get("citation_id") or bound.arguments.get("citation_text")
    metadata: dict[str, Any] = {"tool_name": tool_name}
    if citation is not None:
        metadata["citation"] = citation

    metadata_token = request_metadata_ctx.set(metadata)
    return correlation_token, metadata_token


def tool_logging(tool_name: str) -> Callable[[Callable[P, object]], Callable[P, object | Awaitable[object]]]:
    """Decorator to add correlation IDs and structured entry/exit logging for MCP tools."""

    def decorator(func: Callable[P, object]) -> Callable[P, object | Awaitable[object]]:
        call_signature = signature(func)
        logger = logging.getLogger(func.__module__)

        if asyncio.iscoroutinefunction(func):
            async_func = cast(Callable[P, Awaitable[object]], func)

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> object:
                correlation_token, metadata_token = _bind_context(tool_name, call_signature, args, kwargs)
                start = time.perf_counter()
                logger.info("Tool call started", extra={"event": "tool_start"})
                try:
                    result = await async_func(*args, **kwargs)
                    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                    logger.info("Tool call completed", extra={"event": "tool_end", "elapsed_ms": elapsed_ms})
                    return result
                except Exception:
                    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                    logger.exception(
                        "Tool call failed",
                        extra={"event": "tool_error", "elapsed_ms": elapsed_ms},
                    )
                    raise
                finally:
                    request_metadata_ctx.reset(metadata_token)
                    correlation_id_ctx.reset(correlation_token)

            return async_wrapper

        sync_func = func

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> object:
            correlation_token, metadata_token = _bind_context(tool_name, call_signature, args, kwargs)
            start = time.perf_counter()
            logger.info("Tool call started", extra={"event": "tool_start"})
            try:
                result = sync_func(*args, **kwargs)
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.info("Tool call completed", extra={"event": "tool_end", "elapsed_ms": elapsed_ms})
                return result
            except Exception:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.exception(
                    "Tool call failed",
                    extra={"event": "tool_error", "elapsed_ms": elapsed_ms},
                )
                raise
            finally:
                request_metadata_ctx.reset(metadata_token)
                correlation_id_ctx.reset(correlation_token)

        return sync_wrapper

    return decorator
