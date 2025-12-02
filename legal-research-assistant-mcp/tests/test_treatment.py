"""Tests for treatment analysis tools."""

import pytest

from app.tools.treatment import check_case_validity_impl, get_citing_cases_impl


@pytest.mark.asyncio
async def test_check_case_validity_basic():
    """Test basic case validity checking."""
    # Test with a well-known case
    result = await check_case_validity_impl("410 U.S. 113")  # Roe v. Wade

    assert "citation" in result
    assert "is_good_law" in result
    assert "confidence" in result
    assert isinstance(result.get("total_citing_cases", 0), int)


@pytest.mark.asyncio
async def test_check_case_validity_invalid_citation():
    """Test with an invalid citation."""
    result = await check_case_validity_impl("999 U.S. 999")

    # Should return error or handle gracefully
    assert "error" in result or "total_citing_cases" in result


@pytest.mark.asyncio
async def test_get_citing_cases():
    """Test getting citing cases."""
    result = await get_citing_cases_impl("410 U.S. 113", limit=5)

    assert "citation" in result
    assert "citing_cases" in result
    assert isinstance(result["citing_cases"], list)


@pytest.mark.asyncio
async def test_get_citing_cases_with_filter():
    """Test getting citing cases with treatment filter."""
    result = await get_citing_cases_impl(
        "410 U.S. 113",
        treatment_filter="negative",
        limit=5,
    )

    assert "citation" in result
    assert "filter_applied" in result
    assert result["filter_applied"] == "negative"
