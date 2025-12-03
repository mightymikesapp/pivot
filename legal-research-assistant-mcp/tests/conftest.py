from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_client(mocker):
    """Mock the CourtListener client."""
    client_mock = AsyncMock()

    # Common mock data
    roe_case = {
        "caseName": "Roe v. Wade",
        "citation": ["410 U.S. 113"],
        "dateFiled": "1973-01-22",
        "court": "scotus",
        "cluster_id": 12345,
        "opinions": [{"id": 111}]
    }

    citing_case = {
        "caseName": "Planned Parenthood v. Casey",
        "citation": ["505 U.S. 833"],
        "dateFiled": "1992-06-29",
        "opinions": [{"id": 222}]
    }

    # Mock lookup_citation
    client_mock.lookup_citation.return_value = roe_case

    # Mock find_citing_cases
    client_mock.find_citing_cases.return_value = [citing_case]

    # Mock get_opinion_full_text
    client_mock.get_opinion_full_text.return_value = "This case affirms the essential holding of Roe. The right of privacy is broad enough to encompass a woman's decision."

    # Mock search_opinions
    client_mock.search_opinions.return_value = {
        "count": 1,
        "results": [roe_case]
    }

    # Mock get_opinion
    client_mock.get_opinion.return_value = {
        "plain_text": "Full text of the opinion...",
        "html_lawbox": "<p>HTML content</p>"
    }

    # Patch get_client in common locations
    mocker.patch("app.mcp_client.get_client", return_value=client_mock)
    mocker.patch("app.tools.treatment.get_client", return_value=client_mock)
    mocker.patch("app.tools.verification.get_client", return_value=client_mock)
    mocker.patch("app.tools.network.get_client", return_value=client_mock)

    return client_mock


def pytest_collection_modifyitems(config, items):
    """Mark tests as unit by default unless explicitly tagged as integration."""

    unit_marker = pytest.mark.unit

    for item in items:
        if not any(mark.name == "integration" for mark in item.iter_markers()):
            item.add_marker(unit_marker)
