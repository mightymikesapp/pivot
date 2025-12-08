import asyncio
import inspect
import json
import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from _pytest.python import Function

ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _load_json_fixture(filename: str) -> dict:
    return json.loads((FIXTURES_DIR / filename).read_text())


def _load_text_fixture(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text()


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register CLI and ini options used across the test suite."""

    parser.addini(
        "asyncio_mode",
        "Asyncio execution mode (provided for compatibility with pytest-asyncio)",
        default="auto",
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run tests marked as integration that hit external services.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers and silence unknown marker warnings."""

    config.addinivalue_line("markers", "asyncio: mark a coroutine test")
    config.addinivalue_line("markers", "integration: mark a test that hits external services")
    config.addinivalue_line("markers", "unit: mark a test that runs without external services")


@pytest.fixture
def mock_client(mocker):
    """Mock the CourtListener client and patch common access points."""

    fixture_data = _load_json_fixture("courtlistener_case.json")
    full_text = _load_text_fixture("roe_v_wade_text.txt")

    client_mock = AsyncMock()

    roe_case = fixture_data["roe_case"]
    citing_case = fixture_data["citing_case"]
    opinion_payload = fixture_data["opinion"]

    client_mock.lookup_citation.return_value = roe_case

    client_mock.find_citing_cases.return_value = {
        "results": [citing_case],
        "warnings": [],
        "failed_requests": [],
        "incomplete_data": False,
        "confidence": 1.0,
    }

    client_mock.get_opinion_full_text.return_value = full_text

    client_mock.search_opinions.return_value = {
        "count": 1,
        "results": [roe_case],
    }

    client_mock.get_opinion.return_value = opinion_payload

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


@pytest.hookimpl(tryfirst=True)
def pytest_pycollect_makeitem(collector: pytest.Collector, name: str, obj: object):
    """Collect coroutine test functions as regular pytest functions."""
    if inspect.iscoroutinefunction(obj) and name.startswith("test"):
        return [Function.from_parent(collector, name=name, callobj=obj)]
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip integration tests unless explicitly requested and mark unit tests by default."""

    run_integration = config.getoption("--run-integration")
    skip_integration = pytest.mark.skip(reason="use --run-integration to run integration tests")
    unit_marker = pytest.mark.unit

    for item in items:
        if any(mark.name == "integration" for mark in item.iter_markers()):
            if not run_integration:
                item.add_marker(skip_integration)
        else:
            item.add_marker(unit_marker)


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Allow async tests to run even if pytest-asyncio plugin is unavailable."""

    if pyfuncitem.config.pluginmanager.hasplugin("asyncio"):
        return None

    testfunction = pyfuncitem.obj

    if inspect.iscoroutinefunction(testfunction):
        func_args = {
            name: value
            for name, value in pyfuncitem.funcargs.items()
            if name in pyfuncitem._fixtureinfo.argnames
        }
        asyncio.run(testfunction(**func_args))
        return True

    return None
