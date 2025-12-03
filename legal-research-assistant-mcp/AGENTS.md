# AGENTS.md

## Setup Commands
- Install: `uv sync`
- Run server: `uv run python -m app.server`
- Test (unit): `uv run pytest tests/unit/`
- Test (all): `uv run pytest --run-integration`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Type check: `uv run mypy app/`

## Code Style
- Python 3.12+
- Use type hints everywhere
- Pydantic for configuration and validation
- Async/await for all external calls
- Structured logging (no print statements)

## Architecture
- app/server.py - MCP server entry point
- app/tools/ - MCP tool implementations (user-facing)
- app/analysis/ - Core logic modules (internal)
- app/mcp_client.py - CourtListener API wrapper

## Testing
- Unit tests mock all external calls
- Integration tests require COURTLISTENER_API_KEY
- Target 80%+ coverage

## Testing Conventions
- Use pytest with async support (pytest-asyncio)
- Mock all external API calls in unit tests
- Fixtures go in tests/conftest.py or tests/fixtures/
- Test file naming: test_{module_name}.py
- Use @pytest.mark.asyncio for async tests
- Target 80%+ coverage on app/ modules
- Integration tests require --run-integration flag
- Canonical test case: Roe v. Wade (410 U.S. 113)

## External APIs
- CourtListener API: Rate limited, cache responses
- Always use retry/backoff for external calls
