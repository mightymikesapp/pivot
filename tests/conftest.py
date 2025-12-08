import asyncio
import inspect
import json
import sys
from collections.abc import Generator
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from _pytest.python import Function


# Ensure the repository root is on the import path so ``app`` can be imported
# without requiring callers to set PYTHONPATH manually.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def pytest_configure(config):
    """Register common markers to silence unknown-marker warnings."""

    config.addinivalue_line("markers", "asyncio: mark a test as asyncio-enabled")


def _load_json_fixture(file_name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / file_name).read_text())


def _load_text_fixture(file_name: str) -> str:
    return (FIXTURE_DIR / file_name).read_text()


@pytest.fixture(scope="session")
def roe_metadata_payload() -> dict[str, object]:
    return _load_json_fixture("roe_metadata.json")


@pytest.fixture(scope="session")
def courtlistener_search_payload() -> dict[str, object]:
    return _load_json_fixture("courtlistener_search_response.json")


@pytest.fixture(scope="session")
def courtlistener_citing_cases_payload() -> dict[str, object]:
    return _load_json_fixture("courtlistener_citing_cases_response.json")


@pytest.fixture(scope="session")
def courtlistener_opinion_payload() -> dict[str, object]:
    return _load_json_fixture("courtlistener_opinion_response.json")


@pytest.fixture(scope="session")
def roe_opinion_text() -> str:
    return _load_text_fixture("roe_opinion_excerpt.txt")


@pytest.fixture
def mock_client(
    mocker,
    roe_metadata_payload,
    courtlistener_citing_cases_payload,
    courtlistener_opinion_payload,
    courtlistener_search_payload,
    roe_opinion_text,
):
    """Mock the CourtListener client and patch common access points."""

    client_mock = AsyncMock()

    # Common mock data
    client_mock.lookup_citation.return_value = deepcopy(roe_metadata_payload)

    # Mock find_citing_cases
    client_mock.find_citing_cases.return_value = deepcopy(
        courtlistener_citing_cases_payload
    )

    # Mock get_opinion_full_text
    client_mock.get_opinion_full_text.return_value = roe_opinion_text

    # Mock search_opinions
    client_mock.search_opinions.return_value = deepcopy(courtlistener_search_payload)

    # Mock get_opinion
    client_mock.get_opinion.return_value = deepcopy(courtlistener_opinion_payload)

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


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers used in the test suite."""
    config.addinivalue_line("markers", "asyncio: mark a coroutine test")


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
        # Filter out built-in pytest fixtures that shouldn't be passed to the test function
        func_args = {
            name: value
            for name, value in pyfuncitem.funcargs.items()
            if name in pyfuncitem._fixtureinfo.argnames
        }
        asyncio.run(testfunction(**func_args))
        return True

    return None
