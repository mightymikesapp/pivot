"""Tests for treatment analysis tools."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.analysis.treatment_classifier import TreatmentAnalysis, TreatmentType
from app.tools.treatment import check_case_validity_impl, get_citing_cases_impl


@pytest.fixture
def mock_client(mocker):
    """Mock the CourtListener client."""
    client_mock = AsyncMock()

    # Mock lookup_citation
    client_mock.lookup_citation.return_value = {
        "caseName": "Roe v. Wade",
        "citation": ["410 U.S. 113"],
        "dateFiled": "1973-01-22"
    }

    # Mock find_citing_cases
    client_mock.find_citing_cases.return_value = {
        "results": [
            {
                "caseName": "Planned Parenthood v. Casey",
                "citation": ["505 U.S. 833"],
                "dateFiled": "1992-06-29",
                "opinions": [{"id": 123}],
            }
        ],
        "warnings": [],
        "failed_requests": [],
        "incomplete_data": False,
        "confidence": 1.0,
    }

    # Mock get_opinion_full_text
    client_mock.get_opinion_full_text.return_value = "This case affirms the essential holding of Roe."

    # Patch get_client in the treatment module
    mocker.patch("app.tools.treatment.get_client", return_value=client_mock)

    return client_mock


@pytest.mark.asyncio
async def test_check_case_validity_basic(mock_client):
    """Test basic case validity checking."""
    # Test with a well-known case
    result = await check_case_validity_impl("410 U.S. 113")

    assert "citation" in result
    assert "is_good_law" in result
    assert "confidence" in result
    assert isinstance(result.get("total_citing_cases", 0), int)

    from unittest.mock import ANY
    mock_client.lookup_citation.assert_called_with("410 U.S. 113", request_id=ANY)
    mock_client.find_citing_cases.assert_called()


@pytest.mark.asyncio
async def test_check_case_validity_invalid_citation(mock_client):
    """Test with an invalid citation."""
    mock_client.lookup_citation.return_value = {"error": "Not found"}

    result = await check_case_validity_impl("999 U.S. 999")

    # Should return error
    assert "error" in result
    assert result["error"] == "Could not find case: Not found"


@pytest.mark.asyncio
async def test_get_citing_cases(mock_client):
    """Test getting citing cases."""
    result = await get_citing_cases_impl("410 U.S. 113", limit=5)

    assert "citation" in result
    assert "citing_cases" in result
    assert isinstance(result["citing_cases"], list)
    assert len(result["citing_cases"]) == 1
    assert result["citing_cases"][0]["case_name"] == "Planned Parenthood v. Casey"


@pytest.mark.asyncio
async def test_get_citing_cases_with_filter(mock_client, mocker):
    """Test getting citing cases with treatment filter."""

    # Mock classifier to return specific types for testing filters
    mock_classifier = MagicMock()

    # Create a positive analysis
    positive_analysis = MagicMock(spec=TreatmentAnalysis)
    positive_analysis.treatment_type = TreatmentType.POSITIVE
    positive_analysis.case_name = "Positive Case"
    positive_analysis.citation = "123 U.S. 456"
    positive_analysis.date_filed = "2000-01-01"
    positive_analysis.confidence = 0.9
    positive_analysis.signals_found = []
    positive_analysis.excerpt = "Followed"

    # Create a negative analysis
    negative_analysis = MagicMock(spec=TreatmentAnalysis)
    negative_analysis.treatment_type = TreatmentType.NEGATIVE
    negative_analysis.case_name = "Negative Case"
    negative_analysis.citation = "789 U.S. 012"
    negative_analysis.date_filed = "2020-01-01"
    negative_analysis.confidence = 0.9
    negative_analysis.signals_found = []
    negative_analysis.excerpt = "Overruled"

    # We need side_effect to return different values for different calls if we want to test filtering properly
    # But since the implementation iterates over results from find_citing_cases,
    # we need find_citing_cases to return 2 items, and classify_treatment to be called twice.

    mock_client.find_citing_cases.return_value = {
        "results": ["case1", "case2"],
        "warnings": [],
        "failed_requests": [],
        "incomplete_data": False,
        "confidence": 1.0,
    }

    mocker.patch("app.tools.treatment.classifier.classify_treatment", side_effect=[positive_analysis, negative_analysis])
    mocker.patch(
        "app.tools.treatment.classifier.classify_treatment",
        side_effect=[positive_analysis, negative_analysis],
    )

    # Test filtering for negative
    result = await get_citing_cases_impl(
        "410 U.S. 113",
        treatment_filter="negative",
        limit=5,
    )

    assert "citation" in result
    assert "filter_applied" in result
    assert result["filter_applied"] == "negative"
    assert len(result["citing_cases"]) == 1
    assert result["citing_cases"][0]["treatment"] == "negative"
