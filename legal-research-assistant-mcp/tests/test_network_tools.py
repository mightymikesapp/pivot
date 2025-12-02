"""Tests for network tools."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tools.network import (
    build_citation_network_impl,
    filter_citation_network_impl,
    generate_citation_report_impl,
    get_network_statistics_impl,
    visualize_citation_network_impl,
)


@pytest.fixture
def mock_client_funcs(mocker):
    """Mock the client functions used by network tools."""
    # Mock get_client
    client_mock = AsyncMock()
    mocker.patch("app.tools.network.get_client", return_value=client_mock)

    # Mock responses
    root_case = {
        "caseName": "Root Case",
        "citation": ["100 U.S. 100"],
        "dateFiled": "2000-01-01"
    }
    client_mock.lookup_citation.return_value = root_case

    citing_cases = [
        {
            "caseName": "Citing Case 1",
            "citation": ["200 U.S. 200"],
            "dateFiled": "2010-01-01"
        },
        {
            "caseName": "Citing Case 2",
            "citation": ["300 U.S. 300"],
            "dateFiled": "2020-01-01"
        }
    ]
    client_mock.find_citing_cases.return_value = citing_cases

    return client_mock

@pytest.fixture
def mock_classifier(mocker):
    """Mock the TreatmentClassifier."""
    classifier_mock = mocker.patch("app.tools.network.TreatmentClassifier")
    instance = classifier_mock.return_value

    # Setup treatment analysis mock
    mock_analysis = MagicMock()
    mock_analysis.treatment_type.value = "positive"
    mock_analysis.confidence = 0.9
    mock_analysis.excerpt = "Excerpt"

    instance.classify_treatment.return_value = mock_analysis
    return instance

@pytest.mark.asyncio
async def test_build_citation_network(mock_client_funcs, mock_classifier):
    """Test building a citation network."""
    result = await build_citation_network_impl("100 U.S. 100")

    assert result["root_citation"] == "100 U.S. 100"
    assert len(result["nodes"]) == 3 # Root + 2 citing
    assert len(result["edges"]) == 2

@pytest.mark.asyncio
async def test_build_citation_network_error(mock_client_funcs):
    """Test handling error in root case lookup."""
    mock_client_funcs.lookup_citation.return_value = {"error": "Not found"}

    result = await build_citation_network_impl("999 U.S. 999")

    assert "error" in result

@pytest.mark.asyncio
async def test_build_citation_network_no_citing(mock_client_funcs):
    """Test handling no citing cases."""
    mock_client_funcs.find_citing_cases.return_value = []

    result = await build_citation_network_impl("100 U.S. 100")

    assert len(result["nodes"]) == 1 # Only root
    assert len(result["edges"]) == 0

@pytest.mark.asyncio
async def test_filter_citation_network(mock_client_funcs, mock_classifier):
    """Test filtering a citation network."""
    # Mock classifier to return different treatments
    # For simplicity, we assume the classifier returns the same thing,
    # but we can filter by confidence which we can't easily change per call without side_effect.
    # Let's filter by date instead since we have dates.

    result = await filter_citation_network_impl(
        "100 U.S. 100",
        date_after="2015-01-01"
    )

    # Should only keep Citing Case 2 (2020)
    # Plus root node
    assert len(result["nodes"]) == 2
    # Check edges
    assert len(result["edges"]) == 1
    assert result["edges"][0]["from_citation"] == "300 U.S. 300"

@pytest.mark.asyncio
async def test_get_network_statistics(mock_client_funcs, mock_classifier):
    """Test getting network statistics."""
    result = await get_network_statistics_impl("100 U.S. 100")

    assert result["citation_count"] == 2
    assert "temporal_distribution" in result

@pytest.mark.asyncio
async def test_visualize_citation_network(mock_client_funcs, mock_classifier):
    """Test visualizing citation network."""
    result = await visualize_citation_network_impl(
        "100 U.S. 100",
        diagram_type="all"
    )

    assert "mermaid_syntax" in result
    assert "all_diagrams" in result
    assert "flowchart" in result["all_diagrams"]
    assert "graph" in result["all_diagrams"]
    assert "timeline" in result["all_diagrams"]

@pytest.mark.asyncio
async def test_generate_citation_report(mock_client_funcs, mock_classifier):
    """Test generating citation report."""
    result = await generate_citation_report_impl(
        "100 U.S. 100",
        treatment_focus=["positive"]
    )

    assert "markdown_report" in result
    assert "# Citation Analysis" in result["markdown_report"]
    assert "positive" in result["markdown_report"]
