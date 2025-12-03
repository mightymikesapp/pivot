"""Tests for API response structure."""


import pytest


@pytest.mark.asyncio
async def test_api_response_structure(mock_client):
    """Test what data we get from CourtListener (mocked)."""

    # Search for cases mentioning Roe v. Wade
    results = await mock_client.find_citing_cases("410 U.S. 113", limit=2)

    assert isinstance(results, dict)
    assert "results" in results
    assert isinstance(results["results"], list)
    assert len(results["results"]) > 0

    first_result = results["results"][0]
    assert "caseName" in first_result
    assert "citation" in first_result
    assert "dateFiled" in first_result

    # Check that the mock was called correctly
    mock_client.find_citing_cases.assert_called_with("410 U.S. 113", limit=2)
