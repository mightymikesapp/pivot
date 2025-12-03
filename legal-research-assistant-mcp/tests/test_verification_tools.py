"""Tests for verification tools."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tools.verification import batch_verify_quotes_impl, verify_quote_impl


@pytest.fixture
def mock_client_funcs(mocker):
    """Mock the client functions used by verification tools."""
    # Mock get_client
    client_mock = AsyncMock()
    mocker.patch("app.tools.verification.get_client", return_value=client_mock)

    # Mock responses
    case = {
        "caseName": "Test Case",
        "citation": ["100 U.S. 100"],
        "opinions": [{"id": 1}]
    }
    client_mock.lookup_citation.return_value = case
    client_mock.get_opinion_full_text.return_value = "This is the full text of the opinion containing the quote."

    return client_mock

@pytest.fixture
def mock_matcher(mocker):
    """Mock the QuoteMatcher."""
    # We patch the 'matcher' instance in verification.py
    # Since verification.py does `matcher = QuoteMatcher(...)`

    mock_matcher_instance = MagicMock()
    mocker.patch("app.tools.verification.matcher", mock_matcher_instance)

    # Setup verify_quote return value
    mock_result = MagicMock()
    mock_result.found = True
    mock_result.exact_match = True
    mock_result.similarity = 1.0
    mock_result.matches = [MagicMock(position=10, matched_text="quote", context_before="", context_after="", differences=[])]
    mock_result.warnings = []
    mock_result.recommendation = "Good"

    mock_matcher_instance.verify_quote.return_value = mock_result
    return mock_matcher_instance

@pytest.mark.asyncio
async def test_verify_quote(mock_client_funcs, mock_matcher):
    """Test quote verification."""
    result = await verify_quote_impl("quote", "100 U.S. 100")

    assert result["found"] is True
    assert result["citation"] == "100 U.S. 100"

    from unittest.mock import ANY
    mock_client_funcs.lookup_citation.assert_called_with("100 U.S. 100", request_id=ANY)
    mock_client_funcs.get_opinion_full_text.assert_called_with(1, request_id=ANY)
    mock_matcher.verify_quote.assert_called()

@pytest.mark.asyncio
async def test_verify_quote_case_not_found(mock_client_funcs):
    """Test verification when case is not found."""
    mock_client_funcs.lookup_citation.return_value = {"error": "Not found"}

    result = await verify_quote_impl("quote", "999 U.S. 999")

    assert "error" in result

@pytest.mark.asyncio
async def test_verify_quote_no_opinions(mock_client_funcs):
    """Test verification when case has no opinions."""
    mock_client_funcs.lookup_citation.return_value = {
        "caseName": "Empty Case",
        "opinions": []
    }

    result = await verify_quote_impl("quote", "100 U.S. 100")

    assert "error" in result
    assert result["error"] == "No opinion text available for this case"

@pytest.mark.asyncio
async def test_verify_quote_no_text(mock_client_funcs):
    """Test verification when opinion text retrieval fails."""
    mock_client_funcs.get_opinion_full_text.return_value = ""

    result = await verify_quote_impl("quote", "100 U.S. 100")

    assert "error" in result
    assert result["error"] == "Could not retrieve opinion text"

@pytest.mark.asyncio
async def test_verify_quote_pinpoint(mock_client_funcs, mock_matcher):
    """Test verification with pinpoint citation."""
    result = await verify_quote_impl("quote", "100 U.S. 100", pinpoint="at 150")

    assert "pinpoint_provided" in result
    assert result["pinpoint_provided"] == "at 150"

@pytest.mark.asyncio
async def test_batch_verify_quotes(mock_client_funcs, mock_matcher):
    """Test batch verification."""
    quotes = [
        {"quote": "q1", "citation": "100 U.S. 100"},
        {"quote": "q2", "citation": "100 U.S. 100"}
    ]

    result = await batch_verify_quotes_impl(quotes)

    assert result["total_quotes"] == 2
    assert result["verified"] == 2

@pytest.mark.asyncio
async def test_batch_verify_quotes_invalid_input(mock_client_funcs):
    """Test batch verification with invalid input."""
    quotes = [
        {"quote": "", "citation": "100 U.S. 100"}, # Missing quote
        {"quote": "q2", "citation": ""} # Missing citation
    ]

    result = await batch_verify_quotes_impl(quotes)

    assert len(result["results"]) == 2
    assert "error" in result["results"][0]
