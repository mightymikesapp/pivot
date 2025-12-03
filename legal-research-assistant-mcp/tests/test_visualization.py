"""Tests for visualization tools."""

from unittest.mock import MagicMock

import pytest

from app.analysis.treatment_classifier import TreatmentAnalysis, TreatmentType

# Import the implementation functions
from app.tools.network import (
    generate_citation_report_impl,
    visualize_citation_network_impl,
)


@pytest.fixture
def mock_citation_network_builder(mocker):
    """Mock the CitationNetworkBuilder class."""

    builder_mock = mocker.patch("app.tools.network.CitationNetworkBuilder")
    instance = builder_mock.return_value

    # Mock return value of build_network
    mock_network_data = MagicMock()
    mock_network_data.root_citation = "410 U.S. 113"
    mock_network_data.root_case_name = "Roe v. Wade"
    # nodes needs to be a dict of Node objects or similar structure that can be iterated
    # The code does `for node in network.nodes.values()`
    # So nodes should be a dict where values are objects with attributes

    mock_node = MagicMock()
    mock_node.citation = "410 U.S. 113"
    mock_node.case_name = "Roe v. Wade"
    mock_node.date_filed = "1973-01-22"
    mock_node.court = "scotus"
    mock_node.cluster_id = 123
    mock_node.opinion_ids = [111]
    mock_node.metadata = {}

    mock_network_data.nodes = {"410 U.S. 113": mock_node}

    # edges needs to be a list of Edge objects
    mock_edge = MagicMock()
    mock_edge.from_citation = "505 U.S. 833"
    mock_edge.to_citation = "410 U.S. 113"
    mock_edge.depth = 1
    mock_edge.treatment = "overruled"
    mock_edge.confidence = 0.9
    mock_edge.excerpt = "Overruled by Dobbs"

    mock_network_data.edges = [mock_edge]

    instance.build_network.return_value = mock_network_data

    # Mock return value of get_network_statistics
    instance.get_network_statistics.return_value = {
        "total_nodes": 10,
        "total_edges": 15,
        "treatment_distribution": {"overruled": 1}
    }

    return instance

@pytest.fixture
def mock_mermaid_generator(mocker):
    """Mock the MermaidGenerator class."""
    generator_mock = mocker.patch("app.tools.network.MermaidGenerator")
    instance = generator_mock.return_value
    instance.generate_flowchart.return_value = "graph TD\nA-->B"
    instance.generate_graph.return_value = "graph TD\nA-->B"
    instance.generate_timeline.return_value = "timeline\n2000 : Event"
    instance.generate_summary_stats.return_value = "Summary stats"
    return instance

@pytest.fixture
def mock_classifier(mocker):
    """Mock the TreatmentClassifier."""
    classifier_mock = mocker.patch("app.tools.network.TreatmentClassifier")
    instance = classifier_mock.return_value

    # Mock classify_treatment return value
    # It needs to return a TreatmentAnalysis object

    mock_analysis = MagicMock(spec=TreatmentAnalysis)
    mock_analysis.treatment_type = TreatmentType.NEGATIVE
    mock_analysis.case_name = "Negative Case"
    mock_analysis.citation = "505 U.S. 833"
    mock_analysis.date_filed = "1992-06-29"
    mock_analysis.confidence = 0.9
    mock_analysis.excerpt = "Overruled"

    # The code in build_citation_network_impl tries to access it as a dict: treatment["treatment"]
    # Wait, TreatmentClassifier.classify_treatment returns a TreatmentAnalysis object (dataclass).
    # But app/tools/network.py:75 says: "treatment": treatment["treatment"]
    # This implies the code in network.py expects a dict!
    # BUT TreatmentClassifier.classify_treatment returns TreatmentAnalysis object.

    # LET'S CHECK TreatmentClassifier.classify_treatment definition again.
    # It returns TreatmentAnalysis.

    # So app/tools/network.py:75 is BUGGY! It tries to subscript a dataclass object.
    # treatment["treatment"] -> treatment.treatment_type.value

    # I should FIX the bug in app/tools/network.py first.
    # But for now, to make the test pass or fail correctly, I will verify if I should fix the bug.
    # Yes, I should fix the bug.

    instance.classify_treatment.return_value = mock_analysis
    return instance

@pytest.mark.asyncio
async def test_basic_visualization(mock_client, mock_citation_network_builder, mock_mermaid_generator, mock_classifier):
    """Test basic Mermaid diagram generation."""

    # We need to mock the classifier because build_citation_network_impl instantiates it

    result = await visualize_citation_network_impl(
        citation="410 U.S. 113",
        diagram_type="flowchart",
        direction="TB",
        max_nodes=10,
    )

    assert result["citation"] == "410 U.S. 113"
    assert "mermaid_syntax" in result
    assert result["mermaid_syntax"] == "graph TD\nA-->B"

    mock_citation_network_builder.build_network.assert_called()
    mock_mermaid_generator.generate_flowchart.assert_called()

@pytest.mark.asyncio
async def test_timeline_visualization(mock_client, mock_citation_network_builder, mock_mermaid_generator, mock_classifier):
    """Test timeline diagram generation."""

    result = await visualize_citation_network_impl(
        citation="410 U.S. 113",
        diagram_type="timeline",
        max_nodes=10,
    )

    assert result["mermaid_syntax"] == "timeline\n2000 : Event"

    mock_mermaid_generator.generate_timeline.assert_called()

@pytest.mark.asyncio
async def test_full_report(mock_client, mock_citation_network_builder, mock_mermaid_generator, mock_classifier):
    """Test comprehensive citation report generation."""

    result = await generate_citation_report_impl(
        citation="410 U.S. 113",
        include_diagram=True,
        include_statistics=True,
        treatment_focus=["overruled"],
        max_nodes=15,
    )

    assert result["citation"] == "410 U.S. 113"
    assert "markdown_report" in result
    assert "statistics" in result
