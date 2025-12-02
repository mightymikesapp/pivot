"""Tests for full text fetching."""

import re

import pytest


@pytest.mark.asyncio
async def test_full_text_fetching(mock_client):
    """Test fetching and examining full opinion text."""

    # First, find a case citing Roe
    results = await mock_client.find_citing_cases("410 U.S. 113", limit=1)
    assert len(results) > 0
    case = results[0]

    # Get opinion IDs
    opinions = case.get("opinions", [])
    assert len(opinions) > 0
    opinion_id = opinions[0].get("id")

    # Fetch full text
    full_text = await mock_client.get_opinion_full_text(opinion_id)

    assert isinstance(full_text, str)
    assert len(full_text) > 0
    assert "Roe" in full_text

    mock_client.get_opinion_full_text.assert_called_with(opinion_id)

@pytest.mark.asyncio
async def test_full_text_regex_search(mock_client):
    """Test searching for patterns in full text."""
    full_text = await mock_client.get_opinion_full_text(111)

    # Test regex patterns
    patterns = [
        r"right of privacy",
        r"woman's decision",
    ]

    for pattern in patterns:
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
        assert len(matches) > 0, f"Pattern {pattern} not found in mock text"
