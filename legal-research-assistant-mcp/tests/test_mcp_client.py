"""Tests for the MCP Client."""

import logging
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.mcp_client import CourtListenerClient, get_client
from app.config import Settings
from app.cache import CacheManager, CacheType


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
    assert len(result) == 1
    assert result[0]["caseName"] == "Citing Case"

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

    assert len(result) == 1
    assert result[0]["caseName"] == "Success"


@pytest.mark.asyncio
async def test_close(client_instance):
    """Test closing the client."""
    client_instance.client.aclose = MagicMock()

    # We need to mock aclose as an async function
    async def mock_aclose():
        pass
    client_instance.client.aclose = mock_aclose

    await client_instance.close()
