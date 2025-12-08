"""Tests for the MCP Client."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.cache import CacheManager, CacheType
from app.config import Settings
from app.mcp_client import CircuitBreakerOpenError, CourtListenerClient


@pytest.fixture
def client_instance():
    """Create a client instance for testing."""
    # Use settings with dummy key to trigger auth headers logic
    settings = Settings(courtlistener_api_key="dummy_key")
    # Reset singleton
    with patch("app.mcp_client._client", None):
        client = CourtListenerClient(settings)
        # Mock the CacheManager to avoid disk I/O
        client.cache_manager = MagicMock(spec=CacheManager)
        # Default behavior: cache miss
        client.cache_manager.get.return_value = None
        yield client
        # Clean up
        if hasattr(client, 'client'):
            # It's an async client, we can't easily close it in a sync fixture
            # but we can suppress the warning or ignore it.
            pass


@pytest.mark.asyncio
async def test_search_opinions(client_instance):
    """Test searching for opinions."""
    # Mock the HTTP response
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"caseName": "Test Case"}]}
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    client_instance.client.request = MagicMock(return_value=mock_response)

    # We need to mock the coroutine return
    async def mock_request(*args, **kwargs):
        return mock_response

    client_instance.client.request = mock_request

    result = await client_instance.search_opinions(q="test query")

    assert result["results"][0]["caseName"] == "Test Case"

    # Verify cache interaction
    client_instance.cache_manager.get.assert_called_with(
        CacheType.SEARCH,
        {'q': 'test query', 'type': 'o', 'order_by': 'score desc', 'hit': 20}
    )
    client_instance.cache_manager.set.assert_called()


@pytest.mark.asyncio
async def test_search_opinions_error(client_instance):
    """Test error handling in search."""

    async def mock_request(*args, **kwargs):
        raise httpx.HTTPStatusError("Error", request=None, response=MagicMock(status_code=500))

    client_instance.client.request = mock_request

    with pytest.raises(httpx.HTTPStatusError):
        await client_instance.search_opinions(q="error query")


@pytest.mark.asyncio
async def test_get_opinion(client_instance):
    """Test getting a specific opinion."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 123, "plain_text": "Opinion text"}
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    async def mock_request(*args, **kwargs):
        return mock_response

    client_instance.client.request = mock_request

    result = await client_instance.get_opinion(123)
    assert result["id"] == 123

    # Verify cache
    client_instance.cache_manager.get.assert_called_with(
        CacheType.METADATA, {"opinion_id": 123}
    )
    client_instance.cache_manager.set.assert_called()


@pytest.mark.asyncio
async def test_get_opinion_full_text(client_instance):
    """Test getting full text with fallback fields."""

    # Mock get_opinion response
    mock_opinion = {
        "id": 123,
        "plain_text": "Full text content",
        "html": "<html>...</html>"
    }

    # Mock get_opinion method on the client itself to avoid nested HTTP calls
    with patch.object(client_instance, 'get_opinion', return_value=mock_opinion):
        text = await client_instance.get_opinion_full_text(123)
        assert text == "Full text content"

    # Verify cache
    client_instance.cache_manager.get.assert_called_with(
        CacheType.TEXT, {"opinion_id": 123, "field": "full_text"}
    )
    client_instance.cache_manager.set.assert_called()


@pytest.mark.asyncio
async def test_lookup_citation(client_instance):
    """Test looking up a citation."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"caseName": "Cited Case", "citation": ["410 U.S. 113"]}
        ]
    }
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    async def mock_request(*args, **kwargs):
        return mock_response

    client_instance.client.request = mock_request

    result = await client_instance.lookup_citation("410 U.S. 113")
    assert result["caseName"] == "Cited Case"


@pytest.mark.asyncio
async def test_lookup_citation_no_results(client_instance):
    """Test lookup with no results."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    async def mock_request(*args, **kwargs):
        return mock_response

    client_instance.client.request = mock_request

    result = await client_instance.lookup_citation("Invalid Citation")
    assert "error" in result


@pytest.mark.asyncio
async def test_find_citing_cases(client_instance):
    """Test finding citing cases."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"caseName": "Citing Case"}]}
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    async def mock_request(*args, **kwargs):
        return mock_response

    client_instance.client.request = mock_request

    result = await client_instance.find_citing_cases("410 U.S. 113")
    assert len(result["results"]) == 1
    assert result["results"][0]["caseName"] == "Citing Case"
    assert result["failed_requests"] == []

    # Verify cache
    client_instance.cache_manager.get.assert_called_with(
        CacheType.SEARCH, {"citing_cases": "410 U.S. 113", "limit": 100}
    )


@pytest.mark.asyncio
async def test_find_citing_cases_retry(client_instance):
    """Test finding citing cases with retry logic."""
    # First attempt (quoted query) fails to return results (returns empty list), second (unquoted) succeeds

    async def mock_request(method, url, params=None, **kwargs):
        if params and '"410 U.S. 113"' in params.get('q', ''):
             mock_empty = MagicMock()
             mock_empty.json.return_value = {"results": []}
             mock_empty.status_code = 200
             mock_empty.raise_for_status = MagicMock()
             return mock_empty
        else:
             mock_success = MagicMock()
             mock_success.json.return_value = {"results": [{"caseName": "Success"}]}
             mock_success.status_code = 200
             mock_success.raise_for_status = MagicMock()
             return mock_success

    client_instance.client.request = mock_request

    result = await client_instance.find_citing_cases("410 U.S. 113")

    assert len(result["results"]) == 1
    assert result["results"][0]["caseName"] == "Success"
    assert result["warnings"]


@pytest.mark.asyncio
async def test_close(client_instance):
    """Test closing the client."""
    client_instance.client.aclose = MagicMock()

    # We need to mock aclose as an async function
    async def mock_aclose():
        pass
    client_instance.client.aclose = mock_aclose

    await client_instance.close()


@pytest.mark.asyncio
async def test_retry_and_backoff_for_rate_limits(monkeypatch):
    """429/503 responses should be retried with capped exponential backoff."""

    settings = Settings(
        courtlistener_api_key="token",
        courtlistener_retry_attempts=4,
        courtlistener_retry_backoff=15,
    )
    client = CourtListenerClient(settings)

    responses = [
        httpx.HTTPStatusError(
            "error",
            request=httpx.Request("GET", "search/"),
            response=httpx.Response(503, request=httpx.Request("GET", "search/")),
        ),
        httpx.HTTPStatusError(
            "error",
            request=httpx.Request("GET", "search/"),
            response=httpx.Response(429, request=httpx.Request("GET", "search/")),
        ),
        httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", "search/")),
    ]

    request_mock = AsyncMock(side_effect=responses)
    client.client.request = request_mock

    sleep_mock = AsyncMock()
    monkeypatch.setattr("asyncio.sleep", sleep_mock)

    response = await client._request("GET", "search/")

    assert response.json()["ok"] is True
    assert request_mock.await_count == 3

    sleep_durations = [call.args[0] for call in sleep_mock.await_args_list]
    assert sleep_durations  # ensure backoff invoked
    assert max(sleep_durations) <= 30
    assert sleep_durations[0] >= settings.courtlistener_retry_backoff


@pytest.mark.parametrize("status_code", [400, 401, 404])
def test_client_errors_not_retried(status_code, monkeypatch):
    """Client errors should not trigger retries."""

    async def _run_test():
        settings = Settings(courtlistener_api_key="token", courtlistener_retry_attempts=5)
        client = CourtListenerClient(settings)

        error = httpx.HTTPStatusError(
            "client error",
            request=httpx.Request("GET", "search/"),
            response=httpx.Response(status_code, request=httpx.Request("GET", "search/")),
        )

        request_mock = AsyncMock(side_effect=error)
        client.client.request = request_mock

        sleep_mock = AsyncMock()
        monkeypatch.setattr("asyncio.sleep", sleep_mock)

        with pytest.raises(httpx.HTTPStatusError):
            await client._request("GET", "search/")

        assert request_mock.await_count == 1
        sleep_mock.assert_not_awaited()

    asyncio.run(_run_test())


def test_timeout_configuration_applied():
    """Configured connect/read timeouts should be passed to httpx."""

    settings = Settings(
        courtlistener_api_key="token",
        courtlistener_timeout=120,
        courtlistener_connect_timeout=5,
        courtlistener_read_timeout=25,
    )

    with patch("app.mcp_client.httpx.AsyncClient") as mock_async_client:
        mock_instance = AsyncMock()
        mock_async_client.return_value = mock_instance

        client = CourtListenerClient(settings)

    assert client.client is mock_instance
    timeout = mock_async_client.call_args.kwargs["timeout"]
    assert timeout.connect == 5
    assert timeout.read == 25
    assert timeout.write == 120
    assert timeout.pool == 120


@pytest.mark.asyncio
async def test_partial_results_track_failures(monkeypatch):
    """Failed query attempts should be surfaced alongside results with reduced confidence."""

    settings = Settings(
        courtlistener_api_key="token",
        courtlistener_retry_attempts=1,
        courtlistener_retry_backoff=0,
    )
    client = CourtListenerClient(settings)
    client.cache_manager = MagicMock()
    client.cache_manager.get.return_value = None

    error = httpx.HTTPStatusError(
        "temporary error",
        request=httpx.Request("GET", "search/"),
        response=httpx.Response(503, request=httpx.Request("GET", "search/")),
    )

    success_response = httpx.Response(
        200,
        json={"results": [{"id": 1, "caseName": "Recovered"}]},
        request=httpx.Request("GET", "search/"),
    )

    async def request_side_effect(*args, **kwargs):
        if not request_side_effect.failed_once:
            request_side_effect.failed_once = True
            raise error
        return success_response

    request_side_effect.failed_once = False

    client.client.request = AsyncMock(side_effect=request_side_effect)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    result = await client.find_citing_cases("410 U.S. 113", limit=10)

    assert result["results"] == [{"id": 1, "caseName": "Recovered"}]
    assert result["failed_requests"]
    assert result["incomplete_data"] is True
    assert result["confidence"] < 1.0


@pytest.mark.asyncio
async def test_circuit_breaker_transitions(monkeypatch):
    """Circuit breaker should open after failures, allow half-open, and reset after success."""

    settings = Settings(
        courtlistener_api_key="token",
        courtlistener_retry_attempts=1,
        courtlistener_retry_backoff=0,
    )
    client = CourtListenerClient(settings)

    success_response = httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", "search/"))

    async def request_side_effect(*args, **kwargs):
        request_side_effect.call_count += 1
        if request_side_effect.call_count <= 5:
            raise httpx.RequestError("boom")
        if request_side_effect.call_count == 6:
            return success_response
        raise httpx.RequestError("boom-again")

    request_side_effect.call_count = 0

    client.client.request = AsyncMock(side_effect=request_side_effect)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    for _ in range(5):
        with pytest.raises(httpx.RequestError):
            await client._request("GET", "search/")

    assert client._circuit_open()

    with pytest.raises(CircuitBreakerOpenError):
        await client._request("GET", "search/")

    assert client.client.request.await_count == 5

    client.circuit_open_until = client.circuit_open_until - timedelta(seconds=61)

    response = await client._request("GET", "search/")
    assert response.status_code == 200
    assert not client._circuit_open()
    assert client.failure_count == 0

    with pytest.raises(httpx.RequestError):
        await client._request("GET", "search/")

    assert client.failure_count == 1
