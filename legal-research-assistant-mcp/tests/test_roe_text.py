"""Tests for Roe text retrieval (formerly test_roe_text.py)."""

import pytest


@pytest.mark.asyncio
async def test_roe_text_retrieval(mock_client):
    """Test getting Roe text."""

    # Look up Roe
    case = await mock_client.lookup_citation("410 U.S. 113")
    assert case["caseName"] == "Roe v. Wade"

    # Get opinion IDs
    opinion_ids = [op.get("id") for op in case.get("opinions", []) if op.get("id")]
    assert len(opinion_ids) > 0

    # Fetch text
    full_text = await mock_client.get_opinion_full_text(opinion_ids[0])
    assert "Roe" in full_text
    assert "privacy" in full_text
