"""Tests for CourtListener client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.mcp_client import CourtListenerClient


@pytest.fixture
def client_instance():
    """Create a client instance with mocked httpx client."""
    # We patch httpx.AsyncClient so when CourtListenerClient calls it, it gets a mock
    with patch("httpx.AsyncClient") as mock_client_cls:
        # The mock_client_cls is the class constructor.
        # Its return value (the instance) should be an AsyncMock.
        mock_client_instance = AsyncMock()
        mock_client_cls.return_value = mock_client_instance

        # Create client
        client = CourtListenerClient()

        yield client


@pytest.mark.asyncio
async def test_search_opinions(client_instance):
    """Test searching for opinions."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"count": 1, "results": [{"caseName": "Test Case"}]}
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock() # Should not raise

    # Mock the client.request method which is called by _request
    client_instance.client.request.return_value = mock_response

    result = await client_instance.search_opinions(
        q="test",
        court="scotus",
        limit=5
    )

    assert result["count"] == 1
    assert result["results"][0]["caseName"] == "Test Case"

    # Verify params
    client_instance.client.request.assert_called_once()
    call_args = client_instance.client.request.call_args
    assert call_args[0][0] == "GET" # method
    assert call_args[0][1] == "search/" # url
    assert call_args[1]["params"]["q"] == "test"
    assert call_args[1]["params"]["court"] == "scotus"
    assert call_args[1]["params"]["hit"] == 5


@pytest.mark.asyncio
async def test_search_opinions_error(client_instance):
    """Test error handling in search_opinions."""
    # Mock request to raise HTTPError
    client_instance.client.request.side_effect = httpx.HTTPError("API Error")

    with pytest.raises(httpx.HTTPError):
        await client_instance.search_opinions(q="test")


@pytest.mark.asyncio
async def test_get_opinion(client_instance):
    """Test getting a specific opinion."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 123, "plain_text": "Opinion text"}
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    client_instance.client.request.return_value = mock_response

    # Mock cache so it misses
    with patch.object(client_instance, '_read_cache', return_value=None), \
         patch.object(client_instance, '_write_cache'):

        result = await client_instance.get_opinion(123)

        assert result["id"] == 123
        client_instance.client.request.assert_called_with(
            "GET",
            "opinions/123/",
            headers=client_instance._get_headers()
        )


@pytest.mark.asyncio
async def test_get_opinion_full_text(client_instance):
    """Test getting full text with fallback fields."""

    # Mock cache methods
    with patch.object(client_instance, '_read_cache', return_value=None), \
         patch.object(client_instance, '_write_cache'):

        # Case 1: plain_text
        mock_response1 = MagicMock()
        mock_response1.json.return_value = {"id": 1, "plain_text": "Plain text"}
        mock_response1.status_code = 200
        mock_response1.raise_for_status = MagicMock()

        client_instance.client.request.return_value = mock_response1
        text = await client_instance.get_opinion_full_text(1)
        assert text == "Plain text"

        # Case 2: html_lawbox fallback
        mock_response2 = MagicMock()
        mock_response2.json.return_value = {"id": 2, "html_lawbox": "HTML text"}
        mock_response2.status_code = 200
        mock_response2.raise_for_status = MagicMock()

        client_instance.client.request.return_value = mock_response2
        text = await client_instance.get_opinion_full_text(2)
        assert text == "HTML text"

        # Case 3: no text
        mock_response3 = MagicMock()
        mock_response3.json.return_value = {"id": 3}
        mock_response3.status_code = 200
        mock_response3.raise_for_status = MagicMock()

        client_instance.client.request.return_value = mock_response3
        text = await client_instance.get_opinion_full_text(3)
        assert text == ""


@pytest.mark.asyncio
async def test_lookup_citation(client_instance):
    """Test citation lookup."""
    # Mock successful search
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"citation": ["410 U.S. 113"], "caseName": "Roe v. Wade"}
        ]
    }
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    client_instance.client.request.return_value = mock_response

    result = await client_instance.lookup_citation("410 U.S. 113")

    assert result["caseName"] == "Roe v. Wade"


@pytest.mark.asyncio
async def test_lookup_citation_no_results(client_instance):
    """Test citation lookup with no results."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    client_instance.client.request.return_value = mock_response

    result = await client_instance.lookup_citation("999 U.S. 999")

    assert "error" in result
    assert result["citation"] == "999 U.S. 999"


@pytest.mark.asyncio
async def test_find_citing_cases(client_instance):
    """Test finding citing cases."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [{"caseName": "Citing Case"}]
    }
    mock_response.raise_for_status = MagicMock()

    client_instance.client.request.return_value = mock_response

    result = await client_instance.find_citing_cases("410 U.S. 113")

    assert len(result) == 1
    assert result[0]["caseName"] == "Citing Case"


@pytest.mark.asyncio
async def test_find_citing_cases_retry(client_instance):
    """Test finding citing cases with retry logic."""
    # First attempt (quoted query) fails to return results (returns empty list), second (unquoted) succeeds

    response1 = MagicMock()
    response1.status_code = 200
    response1.raise_for_status = MagicMock()
    response1.json.return_value = {"results": []}

    response2 = MagicMock()
    response2.status_code = 200
    response2.raise_for_status = MagicMock()
    response2.json.return_value = {"results": [{"caseName": "Success"}]}

    client_instance.client.request.side_effect = [response1, response2]

    result = await client_instance.find_citing_cases("410 U.S. 113")

    assert len(result) == 1
    assert result[0]["caseName"] == "Success"
    assert client_instance.client.request.call_count == 2


@pytest.mark.asyncio
async def test_close(client_instance):
    """Test closing the client."""
    await client_instance.close()
    client_instance.client.aclose.assert_called_once()
