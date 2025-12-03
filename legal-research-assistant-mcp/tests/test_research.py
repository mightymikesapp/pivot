"""Tests for research orchestration tools."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tools.research import (
    _analyze_citation,
    _format_key_questions,
    issue_map as issue_map_tool,
    run_research_pipeline as run_research_pipeline_tool,
)

# Get underlying functions from FastMCP tools
run_research_pipeline = run_research_pipeline_tool.fn
issue_map = issue_map_tool.fn


@pytest.fixture
def mock_implementations(mocker):
    """Mock all the implementation functions that research tools call."""
    # Mock get_client
    client_mock = AsyncMock()
    mocker.patch("app.tools.research.get_client", return_value=client_mock)

    # Mock lookup_citation
    client_mock.lookup_citation.return_value = {
        "caseName": "Roe v. Wade",
        "citation": ["410 U.S. 113"],
        "dateFiled": "1973-01-22",
        "court": "scotus",
    }

    # Mock check_case_validity_impl
    treatment_result = {
        "citation": "410 U.S. 113",
        "is_good_law": True,
        "confidence": 0.85,
        "summary": "Landmark case on reproductive rights, partially affirmed by Casey",
        "total_citing_cases": 150,
        "treatment_breakdown": {
            "positive": 100,
            "neutral": 40,
            "negative": 10,
        },
    }
    mock_treatment = mocker.patch(
        "app.tools.research.check_case_validity_impl",
        return_value=treatment_result,
    )

    # Mock build_citation_network_impl
    network_result = {
        "root_citation": "410 U.S. 113",
        "nodes": [
            {
                "citation": "410 U.S. 113",
                "case_name": "Roe v. Wade",
                "date_filed": "1973-01-22",
            },
            {
                "citation": "505 U.S. 833",
                "case_name": "Planned Parenthood v. Casey",
                "date_filed": "1992-06-29",
            },
        ],
        "edges": [
            {
                "from_citation": "505 U.S. 833",
                "to_citation": "410 U.S. 113",
                "treatment": "positive",
            }
        ],
        "statistics": {
            "total_nodes": 2,
            "total_edges": 1,
            "depth": 1,
        },
    }
    mock_network = mocker.patch(
        "app.tools.research.build_citation_network_impl",
        return_value=network_result,
    )

    # Mock batch_verify_quotes_impl
    quotes_result = {
        "results": [
            {
                "citation": "410 U.S. 113",
                "quote": "right of privacy",
                "found": True,
                "similarity": 0.95,
            }
        ]
    }
    mock_quotes = mocker.patch(
        "app.tools.research.batch_verify_quotes_impl",
        return_value=quotes_result,
    )

    # Mock MermaidGenerator
    mermaid_mock = MagicMock()
    mermaid_mock.generate_flowchart.return_value = "graph TD\n  A-->B"
    mocker.patch(
        "app.tools.research.MermaidGenerator",
        return_value=mermaid_mock,
    )

    return {
        "client": client_mock,
        "treatment": mock_treatment,
        "network": mock_network,
        "quotes": mock_quotes,
        "mermaid": mermaid_mock,
    }


@pytest.fixture
def mock_settings(mocker):
    """Mock settings."""
    settings_mock = MagicMock()
    settings_mock.network_max_depth = 3
    settings_mock.max_citing_cases = 100
    mocker.patch("app.tools.research.get_settings", return_value=settings_mock)
    return settings_mock


# Tests for _format_key_questions helper


def test_format_key_questions_removes_empty_strings():
    """Test that empty strings are filtered out."""
    questions = ["What is the law?", "", "  ", "How to apply?"]
    result = _format_key_questions(questions)
    assert result == ["What is the law?", "How to apply?"]


def test_format_key_questions_empty_list():
    """Test with empty list."""
    result = _format_key_questions([])
    assert result == []


def test_format_key_questions_all_valid():
    """Test with all valid questions."""
    questions = ["Question 1", "Question 2", "Question 3"]
    result = _format_key_questions(questions)
    assert result == questions


# Tests for _analyze_citation helper


@pytest.mark.asyncio
async def test_analyze_citation_success(mock_implementations, mock_settings):
    """Test successful citation analysis."""
    result = await _analyze_citation(
        citation="410 U.S. 113",
        scope="federal",
        mermaid_generator=mock_implementations["mermaid"],
        request_id="test-123",
    )

    assert result["citation"] == "410 U.S. 113"
    assert result["case_name"] == "Roe v. Wade"
    assert result["court"] == "scotus"
    assert result["date_filed"] == "1973-01-22"
    assert "treatment" in result
    assert "network" in result
    assert "mermaid" in result
    assert result["mermaid"] == "graph TD\n  A-->B"

    # Verify calls
    mock_implementations["client"].lookup_citation.assert_called_once_with(
        "410 U.S. 113", request_id="test-123"
    )
    mock_implementations["treatment"].assert_called_once()
    mock_implementations["network"].assert_called_once()


@pytest.mark.asyncio
async def test_analyze_citation_lookup_error(mock_implementations, mock_settings):
    """Test when citation lookup fails."""
    mock_implementations["client"].lookup_citation.return_value = {
        "error": "Citation not found"
    }

    result = await _analyze_citation(
        citation="999 U.S. 999",
        scope=None,
        mermaid_generator=mock_implementations["mermaid"],
        request_id="test-123",
    )

    assert result["citation"] == "999 U.S. 999"
    assert "error" in result
    assert result["error"] == "Citation not found"

    # Should not call treatment or network if lookup fails
    mock_implementations["treatment"].assert_not_called()
    mock_implementations["network"].assert_not_called()


@pytest.mark.asyncio
async def test_analyze_citation_no_network_nodes(mock_implementations, mock_settings):
    """Test when network has no nodes."""
    mock_implementations["network"].return_value = {
        "nodes": [],
        "edges": [],
        "statistics": {"total_nodes": 0},
    }

    result = await _analyze_citation(
        citation="410 U.S. 113",
        scope=None,
        mermaid_generator=mock_implementations["mermaid"],
        request_id=None,
    )

    assert result["mermaid"] is None
    mock_implementations["mermaid"].generate_flowchart.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_citation_network_error(mock_implementations, mock_settings):
    """Test when network building returns error."""
    mock_implementations["network"].return_value = {
        "error": "Network building failed"
    }

    result = await _analyze_citation(
        citation="410 U.S. 113",
        scope=None,
        mermaid_generator=mock_implementations["mermaid"],
        request_id=None,
    )

    assert result["mermaid"] is None


# Tests for run_research_pipeline


@pytest.mark.asyncio
async def test_run_research_pipeline_basic(mock_implementations, mock_settings):
    """Test basic research pipeline execution."""
    result = await run_research_pipeline(
        citations=["410 U.S. 113"],
        key_questions=["What is the current status?"],
        scope="federal",
        request_id="test-123",
    )

    assert "summary_markdown" in result
    assert "cases" in result
    assert "key_questions" in result
    assert "scope" in result

    assert result["scope"] == "federal"
    assert len(result["cases"]) == 1
    assert len(result["key_questions"]) == 1
    assert "# Research Pipeline Summary" in result["summary_markdown"]
    assert "*Scope:* federal" in result["summary_markdown"]


@pytest.mark.asyncio
async def test_run_research_pipeline_multiple_citations(
    mock_implementations, mock_settings
):
    """Test pipeline with multiple citations."""
    result = await run_research_pipeline(
        citations=["410 U.S. 113", "505 U.S. 833"],
        key_questions=["Question 1", "Question 2"],
        request_id="test-123",
    )

    assert len(result["cases"]) == 2
    assert len(result["key_questions"]) == 2

    # Both cases should be in summary
    assert "410 U.S. 113" in result["summary_markdown"]
    assert "505 U.S. 833" in result["summary_markdown"]


@pytest.mark.asyncio
async def test_run_research_pipeline_with_quotes(
    mock_implementations, mock_settings
):
    """Test pipeline with quote verification."""
    quotes = [
        {"quote": "right of privacy", "citation": "410 U.S. 113"}
    ]

    result = await run_research_pipeline(
        citations=["410 U.S. 113"],
        quotes=quotes,
        request_id="test-123",
    )

    assert "quotes" in result
    assert result["quotes"] is not None
    assert "## Quote Verification" in result["summary_markdown"]
    assert "found" in result["summary_markdown"]

    mock_implementations["quotes"].assert_called_once_with(
        quotes, request_id="test-123"
    )


@pytest.mark.asyncio
async def test_run_research_pipeline_no_citations_error(
    mock_implementations, mock_settings
):
    """Test error when no citations provided."""
    result = await run_research_pipeline(citations=[])

    assert "error" in result
    assert result["error"] == "At least one citation is required"


@pytest.mark.asyncio
async def test_run_research_pipeline_no_questions(
    mock_implementations, mock_settings
):
    """Test pipeline without key questions."""
    result = await run_research_pipeline(
        citations=["410 U.S. 113"],
        request_id="test-123",
    )

    assert "No key questions provided" in result["summary_markdown"]
    assert result["key_questions"] == []


@pytest.mark.asyncio
async def test_run_research_pipeline_case_error(
    mock_implementations, mock_settings
):
    """Test handling of case lookup error."""
    mock_implementations["client"].lookup_citation.return_value = {
        "error": "Not found"
    }

    result = await run_research_pipeline(
        citations=["999 U.S. 999"],
        request_id="test-123",
    )

    assert len(result["cases"]) == 1
    assert "error" in result["cases"][0]
    assert "999 U.S. 999" in result["summary_markdown"]
    assert "Not found" in result["summary_markdown"]


@pytest.mark.asyncio
async def test_run_research_pipeline_quote_verification_error(
    mock_implementations, mock_settings
):
    """Test handling of quote verification error."""
    mock_implementations["quotes"].return_value = {
        "error": "Quote verification failed"
    }

    quotes = [{"quote": "test", "citation": "410 U.S. 113"}]
    result = await run_research_pipeline(
        citations=["410 U.S. 113"],
        quotes=quotes,
        request_id="test-123",
    )

    assert "## Quote Verification" in result["summary_markdown"]
    assert "Error verifying quotes" in result["summary_markdown"]


@pytest.mark.asyncio
async def test_run_research_pipeline_formats_network_stats(
    mock_implementations, mock_settings
):
    """Test that network statistics are included in summary."""
    result = await run_research_pipeline(
        citations=["410 U.S. 113"],
        request_id="test-123",
    )

    assert "Network: 2 nodes, 1 edges" in result["summary_markdown"]
    assert "Mermaid diagram available" in result["summary_markdown"]


@pytest.mark.asyncio
async def test_run_research_pipeline_no_scope(
    mock_implementations, mock_settings
):
    """Test pipeline without scope."""
    result = await run_research_pipeline(
        citations=["410 U.S. 113"],
        request_id="test-123",
    )

    assert "*Scope:*" not in result["summary_markdown"]
    assert result["scope"] is None


# Tests for issue_map


@pytest.mark.asyncio
async def test_issue_map_basic(mock_implementations, mock_settings):
    """Test basic issue map generation."""
    result = await issue_map(
        citations=["410 U.S. 113"],
        key_questions=["What is the current status?"],
        scope="federal",
        request_id="test-123",
    )

    assert "summary_markdown" in result
    assert "issues" in result
    assert "cases" in result
    assert "key_questions" in result
    assert "scope" in result

    assert len(result["issues"]) == 1
    assert result["issues"][0]["question"] == "What is the current status?"
    assert len(result["issues"][0]["related_cases"]) == 1


@pytest.mark.asyncio
async def test_issue_map_multiple_questions(
    mock_implementations, mock_settings
):
    """Test issue map with multiple questions."""
    result = await issue_map(
        citations=["410 U.S. 113", "505 U.S. 833"],
        key_questions=["Question 1", "Question 2"],
        request_id="test-123",
    )

    assert len(result["issues"]) == 2
    # Each issue should have both cases as related
    for issue in result["issues"]:
        assert len(issue["related_cases"]) == 2


@pytest.mark.asyncio
async def test_issue_map_no_questions(mock_implementations, mock_settings):
    """Test issue map without questions uses default."""
    result = await issue_map(
        citations=["410 U.S. 113"],
        request_id="test-123",
    )

    assert len(result["issues"]) == 1
    assert result["issues"][0]["question"] == "General application"


@pytest.mark.asyncio
async def test_issue_map_no_citations_error(
    mock_implementations, mock_settings
):
    """Test error when no citations provided."""
    result = await issue_map(citations=[])

    assert "error" in result
    assert result["error"] == "At least one citation is required"


@pytest.mark.asyncio
async def test_issue_map_structure(mock_implementations, mock_settings):
    """Test the structure of issue entries."""
    result = await issue_map(
        citations=["410 U.S. 113"],
        key_questions=["Test question"],
        scope="state",
        request_id="test-123",
    )

    issue = result["issues"][0]
    assert issue["question"] == "Test question"
    assert issue["scope"] == "state"
    assert "related_cases" in issue

    case = issue["related_cases"][0]
    assert "citation" in case
    assert "case_name" in case
    assert "summary" in case
    assert "treatment" in case
    assert "network_statistics" in case


@pytest.mark.asyncio
async def test_issue_map_summary_markdown(
    mock_implementations, mock_settings
):
    """Test the markdown summary format."""
    result = await issue_map(
        citations=["410 U.S. 113"],
        key_questions=["What is the law?"],
        request_id="test-123",
    )

    summary = result["summary_markdown"]
    assert "# Issue Map" in summary
    assert "## Questions" in summary
    assert "What is the law?" in summary
    assert "## Related Authorities" in summary
    assert "Roe v. Wade" in summary


@pytest.mark.asyncio
async def test_issue_map_handles_case_errors(
    mock_implementations, mock_settings
):
    """Test that issue map handles case lookup errors gracefully."""
    mock_implementations["client"].lookup_citation.return_value = {
        "error": "Not found"
    }

    result = await issue_map(
        citations=["999 U.S. 999"],
        key_questions=["Test"],
        request_id="test-123",
    )

    # Should still create issue entry
    assert len(result["issues"]) == 1
    assert len(result["issues"][0]["related_cases"]) == 1

    # Error should appear in summary
    assert "999 U.S. 999" in result["summary_markdown"]
    assert "Not found" in result["summary_markdown"]


@pytest.mark.asyncio
async def test_issue_map_includes_network_statistics(
    mock_implementations, mock_settings
):
    """Test that network statistics are included in issue entries."""
    result = await issue_map(
        citations=["410 U.S. 113"],
        key_questions=["Test"],
        request_id="test-123",
    )

    case = result["issues"][0]["related_cases"][0]
    assert case["network_statistics"] is not None
    assert case["network_statistics"]["total_nodes"] == 2
    assert case["network_statistics"]["total_edges"] == 1
