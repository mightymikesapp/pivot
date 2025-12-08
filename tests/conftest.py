import asyncio
import inspect
import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from _pytest.python import Function


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
    """Mock the CourtListener client and patch common access points."""

    client_mock = AsyncMock()

    # Common mock data
    roe_case = {
        "caseName": "Roe v. Wade",
        "citation": ["410 U.S. 113"],
        "dateFiled": "1973-01-22",
        "court": "scotus",
        "cluster_id": 12345,
        "opinions": [{"id": 111}],
    }

    citing_case = {
        "caseName": "Planned Parenthood v. Casey",
        "citation": ["505 U.S. 833"],
        "dateFiled": "1992-06-29",
        "opinions": [{"id": 222}],
    }

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
        "html_lawbox": "<p>HTML content</p>",
    }

    # Patch get_client in common modules
    mocker.patch("app.mcp_client.get_client", return_value=client_mock)
    mocker.patch("app.tools.treatment.get_client", return_value=client_mock)
    mocker.patch("app.tools.verification.get_client", return_value=client_mock)
    mocker.patch("app.tools.network.get_client", return_value=client_mock)

    return client_mock


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Provide a fresh event loop for async tests."""
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register ini options expected by asyncio-aware tests."""
    parser.addini(
        "asyncio_mode",
        "Asyncio execution mode (provided for compatibility with pytest-asyncio)",
        default="auto",
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Include tests marked as integration",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers used in the test suite."""
    config.addinivalue_line("markers", "asyncio: mark a coroutine test")

    if config.getoption("--run-integration"):
        # The default "-m not integration" expression in ``pyproject.toml``
        # excludes integration tests. Clear it so the explicit flag can
        # include them without requiring callers to override mark selection.
        config.option.markexpr = ""


@pytest.hookimpl(tryfirst=True)
def pytest_pycollect_makeitem(collector: pytest.Collector, name: str, obj: object):
    """Collect coroutine test functions as regular pytest functions."""
    if inspect.iscoroutinefunction(obj) and name.startswith("test"):
        return [Function.from_parent(collector, name=name, callobj=obj)]
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Execute coroutine tests using an event loop."""
    test_obj = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_obj):
        return None

    loop: asyncio.AbstractEventLoop | None = pyfuncitem.funcargs.get("event_loop")  # type: ignore[attr-defined]
    created_loop = False

    if loop is None:
        loop = asyncio.new_event_loop()
        created_loop = True

    try:
        asyncio.set_event_loop(loop)
        kwargs = {name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
        loop.run_until_complete(test_obj(**kwargs))
    finally:
        if created_loop:
            loop.close()
        asyncio.set_event_loop(None)
    return True


def pytest_collection_modifyitems(config, items):
    """Mark tests as unit by default unless explicitly tagged as integration."""

    unit_marker = pytest.mark.unit
    run_integration = config.getoption("--run-integration")
    skip_integration = pytest.mark.skip(
        reason="Integration tests require --run-integration"
    )

    for item in items:
        is_integration = any(mark.name == "integration" for mark in item.iter_markers())

        if is_integration and not run_integration:
            item.add_marker(skip_integration)
            continue

        if not is_integration:
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
        # Filter out built-in pytest fixtures that shouldn't be passed to the test function
        func_args = {
            name: value
            for name, value in pyfuncitem.funcargs.items()
            if name in pyfuncitem._fixtureinfo.argnames
        }
        asyncio.run(testfunction(**func_args))
        return True

    return None
