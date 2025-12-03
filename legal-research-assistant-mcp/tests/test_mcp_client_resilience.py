"""Resilience behavior tests for the CourtListener client."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Awaitable, TypeVar
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import Settings
from app.cache import CacheType
from app.mcp_client import (
    CircuitBreakerOpenError,
    CitingCasesResult,
    CourtListenerClient,
)


T = TypeVar("T")


def make_http_error(status_code: int) -> httpx.HTTPStatusError:
    response = httpx.Response(status_code, request=httpx.Request("GET", "https://example.com"))
    return httpx.HTTPStatusError("error", request=response.request, response=response)


def run(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)


def test_retry_on_retryable_status(monkeypatch):
    """Requests should retry on retryable status codes with exponential backoff."""

    settings = Settings(courtlistener_api_key="token", courtlistener_retry_attempts=3)
    client = CourtListenerClient(settings)

    responses = [
        AsyncMock(side_effect=make_http_error(503)),
        AsyncMock(side_effect=make_http_error(429)),
        AsyncMock(
            return_value=httpx.Response(
                200, json={"ok": True}, request=httpx.Request("GET", "https://example.com")
            )
        ),
    ]

    call_sequence = responses.copy()

    async def side_effect(*args, **kwargs):
        call = call_sequence.pop(0)
        return await call(*args, **kwargs)

    client.client.request = AsyncMock(side_effect=side_effect)

    # Avoid real sleep from tenacity
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    response = run(client._request("GET", "search/"))

    assert response.status_code == 200
    assert client.client.request.await_count == 3


def test_no_retry_on_client_error(monkeypatch):
    """Client errors should not trigger retries."""

    settings = Settings(courtlistener_api_key="token", courtlistener_retry_attempts=3)
    client = CourtListenerClient(settings)

    error = make_http_error(400)
    client.client.request = AsyncMock(side_effect=error)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    with pytest.raises(httpx.HTTPStatusError):
        run(client._request("GET", "search/"))

    assert client.client.request.await_count == 1


def test_timeout_configuration():
    """Client should honor configured connect/read timeouts."""

    settings = Settings(
        courtlistener_api_key="token",
        courtlistener_timeout=120,
        courtlistener_connect_timeout=5,
        courtlistener_read_timeout=25,
    )
    client = CourtListenerClient(settings)

    timeout = client.client.timeout
    assert timeout.connect == 5
    assert timeout.read == 25
    assert timeout.write == 120
    assert timeout.pool == 120


def test_partial_results_and_confidence(monkeypatch):
    """Failed requests should be reported while returning successful results."""

    settings = Settings(courtlistener_api_key="token")
    client = CourtListenerClient(settings)

    class DummyCache:
        def __init__(self) -> None:
            self.store: dict[tuple[CacheType, tuple[tuple[str, Any], ...]], Any] = {}

        def get(self, cache_type: CacheType, key_params: dict[str, Any] | str) -> list[dict[str, Any]] | None:
            if isinstance(key_params, str):
                key = (cache_type, ("__key__", key_params))
            else:
                key = (cache_type, tuple(sorted(key_params.items())))
            return self.store.get(key)

        def set(self, cache_type: CacheType, key_params: dict[str, Any] | str, data: Any) -> None:
            if isinstance(key_params, str):
                key = (cache_type, ("__key__", key_params))
            else:
                key = (cache_type, tuple(sorted(key_params.items())))
            self.store[key] = data

    client.cache_manager = DummyCache()

    success_response = httpx.Response(
        200,
        json={"results": [{"caseName": "Citing Case"}]},
        request=httpx.Request("GET", "https://example.com"),
    )

    async def request_side_effect(*args, **kwargs):
        if request_side_effect.failed_once:
            return success_response
        request_side_effect.failed_once = True
        raise make_http_error(503)

    request_side_effect.failed_once = False
    client._request = AsyncMock(side_effect=request_side_effect)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    result = run(client.find_citing_cases("410 U.S. 113"))

    assert isinstance(result, CitingCasesResult)
    assert len(result) == 1
    assert result.failed_requests
    assert result.confidence < 1.0


def test_circuit_breaker_opens(monkeypatch):
    """Circuit breaker should open after consecutive failures and short-circuit calls."""

    settings = Settings(
        courtlistener_api_key="token",
        courtlistener_retry_attempts=1,
    )
    client = CourtListenerClient(settings)

    failing_request = AsyncMock(side_effect=httpx.RequestError("boom"))
    client.client.request = failing_request
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    # Trigger five consecutive failures
    for _ in range(5):
        with pytest.raises(httpx.RequestError):
            run(client._request("GET", "search/"))

    assert client._circuit_open()

    with pytest.raises(CircuitBreakerOpenError):
        run(client._request("GET", "search/"))

    # Verify short-circuiting: no additional request attempts when open
    assert failing_request.await_count == 5

    # Manually move time forward to half-open
    client.circuit_open_until = datetime.utcnow() - timedelta(seconds=1)
    with pytest.raises(httpx.RequestError):
        run(client._request("GET", "search/"))

    assert failing_request.await_count == 6
