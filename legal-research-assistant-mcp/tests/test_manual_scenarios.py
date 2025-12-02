"""Tests for manual scenarios (formerly test_manual.py)."""

from unittest.mock import MagicMock

import pytest

from app.tools.treatment import check_case_validity_impl, get_citing_cases_impl


@pytest.mark.asyncio
async def test_well_known_case(mock_client):
    """Test with a well-known case."""
    # We mock check_case_validity_impl's internal calls via mock_client

    # Run the function
    result = await check_case_validity_impl("410 U.S. 113")

    assert "citation" in result
    assert result["citation"] == "410 U.S. 113"
    assert "is_good_law" in result

@pytest.mark.asyncio
async def test_recent_case(mock_client):
    """Test getting citing cases."""
    result = await get_citing_cases_impl("410 U.S. 113", limit=5)

    assert "citation" in result
    assert "citing_cases" in result
    assert len(result["citing_cases"]) > 0

@pytest.mark.asyncio
async def test_negative_filter(mock_client, mocker):
    """Test filtering for negative treatments."""

    # We need to mock the classifier to ensure we get negative results to filter
    from app.analysis.treatment_classifier import TreatmentAnalysis, TreatmentType

    mock_analysis = MagicMock(spec=TreatmentAnalysis)
    mock_analysis.treatment_type = TreatmentType.NEGATIVE
    mock_analysis.case_name = "Negative Case"
    mock_analysis.citation = "111 U.S. 222"
    mock_analysis.date_filed = "2022-01-01"
    mock_analysis.confidence = 0.9
    mock_analysis.signals_found = []
    mock_analysis.excerpt = "Overruled"

    # Patch the classifier instance that is global in the module
    # app.tools.treatment.classifier

    mock_classifier = MagicMock()
    mock_classifier.classify_treatment.return_value = mock_analysis
    mocker.patch("app.tools.treatment.classifier", mock_classifier)

    result = await get_citing_cases_impl(
        "410 U.S. 113",
        treatment_filter="negative",
        limit=3,
    )

    assert result["filter_applied"] == "negative"
    assert len(result["citing_cases"]) > 0
    assert result["citing_cases"][0]["treatment"] == "negative"
