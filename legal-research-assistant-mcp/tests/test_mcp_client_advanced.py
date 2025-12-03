"""Advanced tests for CourtListener client covering caching and retries."""

import json
import time
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import httpx
import pytest

from app.mcp_client import CourtListenerClient, get_client
from app.config import Settings


pytestmark = pytest.mark.integration


@pytest.fixture
def mock_settings(tmp_path):
    return Settings(
        courtlistener_api_key="test_key",
        courtlistener_cache_dir=tmp_path / "cache",
        courtlistener_retry_attempts=3,
        courtlistener_retry_backoff=0.01,
    )


@pytest.fixture
def client(mock_settings):
    # Don't autospec AsyncClient, just patch it to avoid complex spec issues
    with patch("httpx.AsyncClient") as mock_client_cls:
        # Create a mock instance for the client
        mock_instance = AsyncMock()
        mock_client_cls.return_value = mock_instance

        client = CourtListenerClient(mock_settings)
        # Explicitly set the client to our mock instance
        client.client = mock_instance
        yield client


@pytest.mark.asyncio
async def test_request_retry_logic(client):
    """Test that _request retries on failure."""
    # Setup the mock to fail twice then succeed
    error_response = httpx.Response(500, request=httpx.Request("GET", "url"))
    success_response = httpx.Response(200, json={"data": "success"}, request=httpx.Request("GET", "url"))

    # We need to mock the client.request method
    client.client.request.side_effect = [
        httpx.HTTPStatusError("Server Error", request=error_response.request, response=error_response),
        httpx.HTTPStatusError("Server Error", request=error_response.request, response=error_response),
        success_response
    ]

    response = await client._request("GET", "url")
    assert response.json() == {"data": "success"}
    assert client.client.request.call_count == 3


@pytest.mark.asyncio
async def test_request_retry_failure(client):
    """Test that _request raises exception after max retries."""
    error_response = httpx.Response(500, request=httpx.Request("GET", "url"))

    client.client.request.side_effect = httpx.HTTPStatusError(
        "Server Error", request=error_response.request, response=error_response
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client._request("GET", "url")

    assert client.client.request.call_count == client.retry_attempts


@pytest.mark.asyncio
async def test_cache_read_hit(client):
    """Test reading from cache."""
    cache_key = "test_key"
    cache_data = {"foo": "bar"}

    # Write to cache first (using actual FS since we used tmp_path)
    client._write_cache(cache_key, cache_data)

    # Read back
    result = client._read_cache(cache_key)
    assert result == cache_data


@pytest.mark.asyncio
async def test_cache_read_miss(client):
    """Test reading from cache when file missing."""
    result = client._read_cache("non_existent")
    assert result is None


@pytest.mark.asyncio
async def test_cache_read_expired(client):
    """Test reading expired cache."""
    cache_key = "expired_key"
    cache_data = {"foo": "bar"}
    client._write_cache(cache_key, cache_data)

    # Mock time to be in the future
    # We need to mock time.time()
    with patch("time.time") as mock_time:
        # Get actual mtime of file
        p = client._cache_path(cache_key)
        mtime = p.stat().st_mtime

        mock_time.return_value = mtime + client.cache_ttl + 100

        result = client._read_cache(cache_key)
        assert result is None
        # Should be deleted
        assert not client._cache_path(cache_key).exists()


@pytest.mark.asyncio
async def test_cache_read_error(client):
    """Test error handling during cache read."""
    # Create an invalid json file
    path = client._cache_path("bad_json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write("{invalid")

    result = client._read_cache("bad_json")
    assert result is None


@pytest.mark.asyncio
async def test_write_cache_error(client):
    """Test error handling during cache write."""
    with patch.object(Path, "open", side_effect=OSError("Disk full")):
        client._write_cache("key", {"data": 1})
        # Should not raise


def test_get_client_singleton():
    """Test get_client returns singleton."""
    # Reset global
    import app.mcp_client
    app.mcp_client._client = None

    c1 = get_client()
    c2 = get_client()
    assert c1 is c2
    assert isinstance(c1, CourtListenerClient)


@pytest.mark.asyncio
async def test_get_opinion_caching(client):
    """Test that get_opinion uses cache."""
    opinion_id = 999
    data = {"id": opinion_id, "foo": "bar"}

    # Ensure no cache exists
    cache_path = client._cache_path(f"opinion_{opinion_id}")
    if cache_path.exists():
        cache_path.unlink()

    # First call: network request
    mock_response = MagicMock()
    mock_response.json.return_value = data
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    client.client.request.return_value = mock_response

    result1 = await client.get_opinion(opinion_id)
    assert result1 == data
    assert client.client.request.call_count == 1

    # Verify it was cached
    assert client._read_cache(f"opinion_{opinion_id}") == data

    # Second call: should hit cache and NOT call request
    client.client.request.reset_mock()
    result2 = await client.get_opinion(opinion_id)
    assert result2 == data
    client.client.request.assert_not_called()

@pytest.mark.asyncio
async def test_find_citing_cases_all_fail(client):
    """Test find_citing_cases when all attempts fail."""
    # Mock requests to fail (return empty or error)

    # Attempt 1: Empty results
    r1 = MagicMock()
    r1.status_code = 200
    r1.json.return_value = {"results": []}
    r1.raise_for_status = MagicMock()

    # Attempt 2: Error
    r2 = MagicMock()
    r2.status_code = 404

    # Mocking _request isn't enough because find_citing_cases calls client.get directly for the first check?
    # No, find_citing_cases in my refactored code (if I recall) calls _request?
    # Let's check mcp_client.py content.
    # Ah, in find_citing_cases, I saw `response = await self.client.get(...)` then `response = await self._request(...)` in the original code?
    # Wait, I refactored it to use `_request`.
    # Let's double check `app/mcp_client.py` content via `grep`.

    # In the refactored `mcp_client.py`, `find_citing_cases` calls `_request`.

    client.client.request.side_effect = [r1, httpx.HTTPError("Fail")]

    result = await client.find_citing_cases("123 U.S. 456")
    assert result == []

@pytest.mark.asyncio
async def test_init_no_api_key(tmp_path, caplog):
    """Test initialization without API key logs warning."""
    settings_no_key = Settings(
        courtlistener_api_key="",
        courtlistener_cache_dir=tmp_path / "cache"
    )
    with caplog.at_level(logging.WARNING):
        CourtListenerClient(settings_no_key)
        assert "No CourtListener API key found" in caplog.text

@pytest.mark.asyncio
async def test_lookup_citation_fallback(client):
    """Test lookup_citation fallback logic when no exact match."""
    # Mock response with results but no exact citation match
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"citation": ["Other Citation"], "caseName": "Oldest Case"},
            {"citation": ["Another Citation"], "caseName": "Newer Case"}
        ]
    }
    mock_response.raise_for_status = MagicMock()
    client.client.request.return_value = mock_response

    result = await client.lookup_citation("Target Citation")
    # Should return the first result (oldest)
    assert result["caseName"] == "Oldest Case"
