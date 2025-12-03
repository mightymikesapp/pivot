import asyncio
import inspect
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest


# Ensure the repository root is on the import path so ``app`` can be imported
# without requiring callers to set PYTHONPATH manually.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def pytest_configure(config):
    """Register common markers to silence unknown-marker warnings."""

    config.addinivalue_line("markers", "asyncio: mark a test as asyncio-enabled")


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
    client_mock.find_citing_cases.return_value = {
        "results": [citing_case],
        "warnings": [],
        "failed_requests": [],
        "incomplete_data": False,
        "confidence": 1.0,
    }

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


def pytest_pyfunc_call(pyfuncitem):
    """Allow async tests to run even if pytest-asyncio plugin is unavailable.

    When the asyncio plugin is present we defer to it; otherwise we manually run
    coroutine tests with ``asyncio.run`` so that async test suites can execute
    in constrained environments.
    """

    # If pytest-asyncio is installed, let it handle async tests.
    if pyfuncitem.config.pluginmanager.hasplugin("asyncio"):
        return None

    testfunction = pyfuncitem.obj

    if inspect.iscoroutinefunction(testfunction):
        asyncio.run(testfunction(**pyfuncitem.funcargs))
        return True

    return None
