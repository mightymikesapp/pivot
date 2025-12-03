"""Tests for case lookup functionality."""

import pytest


@pytest.mark.asyncio
async def test_lookup(mock_client):
    """Test case lookup."""

    # Search for Roe v. Wade
    result = await mock_client.lookup_citation("410 U.S. 113")

    assert result.get("caseName") == "Roe v. Wade"
    assert result.get("citation") == ["410 U.S. 113"]
    assert "opinions" in result

    mock_client.lookup_citation.assert_called_with("410 U.S. 113")

@pytest.mark.asyncio
async def test_search_opinions(mock_client):
    """Test searching for opinions."""

    search_result = await mock_client.search_opinions(
        q="Roe v. Wade",
        court="scotus",
        filed_after="1970-01-01",
        filed_before="1975-01-01",
        limit=5,
    )

    assert "count" in search_result
    assert "results" in search_result
    assert len(search_result["results"]) > 0
    assert search_result["results"][0]["caseName"] == "Roe v. Wade"

    mock_client.search_opinions.assert_called()
