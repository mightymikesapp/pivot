"""Tests for quote verification functionality."""

from unittest.mock import MagicMock

import pytest

from app.tools.verification import batch_verify_quotes_impl, verify_quote_impl


@pytest.fixture
def mock_quote_matcher(mocker):
    """Mock the QuoteMatcher."""
    # Patch the matcher object in app.tools.verification

    mock_matcher_instance = MagicMock()

    # Setup default mock return values
    mock_match = MagicMock()
    mock_match.found = True
    mock_match.exact_match = False
    mock_match.similarity = 0.95
    mock_match.matches = [MagicMock(position=100, matched_text="match", context_before="", context_after="", differences=[])]
    mock_match.warnings = []
    mock_match.recommendation = "Good"

    mock_matcher_instance.verify_quote.return_value = mock_match

    mocker.patch("app.tools.verification.matcher", mock_matcher_instance)
    return mock_matcher_instance

@pytest.mark.asyncio
async def test_verify_quote_found(mock_client, mock_quote_matcher):
    """Test verification of a found quote."""

    quote = "the right of privacy"
    citation = "410 U.S. 113"

    result = await verify_quote_impl(quote, citation)

    assert result["found"] is True
    assert result["similarity"] == 0.95
    assert result["citation"] == citation

    mock_client.lookup_citation.assert_called_with(citation)
    mock_quote_matcher.verify_quote.assert_called()

@pytest.mark.asyncio
async def test_verify_quote_not_found(mock_client, mock_quote_matcher):
    """Test verification of a quote that isn't found."""

    # Configure mock to return no match
    mock_match = MagicMock()
    mock_match.found = False
    mock_match.matches = []
    mock_match.similarity = 0.0
    mock_quote_matcher.verify_quote.return_value = mock_match

    quote = "definitely not in the text"
    citation = "410 U.S. 113"

    result = await verify_quote_impl(quote, citation)

    assert result["found"] is False
    assert result["similarity"] < 0.5

@pytest.mark.asyncio
async def test_batch_verification(mock_client, mock_quote_matcher):
    """Test batch quote verification."""

    quotes = [
        {"quote": "q1", "citation": "c1"},
        {"quote": "q2", "citation": "c1"},
    ]

    result = await batch_verify_quotes_impl(quotes)

    assert "results" in result
    assert len(result["results"]) == 2
    assert result["verified"] == 2 # Since our mock returns True
