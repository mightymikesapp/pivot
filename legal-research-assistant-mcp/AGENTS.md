# AGENTS.md

## Setup
- Install: `uv sync`
- Test: `uv run pytest`
- Lint: `uv run ruff check .`
- Type check: `uv run mypy app/`

## Commands to Run
- After modifying Python files: `uv run pytest tests/unit/`
- Before completing: `uv run ruff check . && uv run mypy app/`

## Code Style
- Python 3.12+, strict type hints
- Async/await for all external calls
- Pydantic for config/validation
- No print() - use structured logging

## Project Structure
- app/server.py - MCP entry point
- app/tools/ - User-facing MCP tools
- app/analysis/ - Internal logic modules
- app/mcp_client.py - CourtListener API wrapper
- tests/unit/ - Fast tests (mock external)
- tests/integration/ - Slow tests (real APIs)

## Conventions
- Test files mirror source: app/tools/foo.py → tests/unit/tools/test_foo.py
- External API calls: always use retry/backoff
- Cache CourtListener responses (see app/cache.py)

## PR Messages
- Format: `[scope] description`
- Include: what changed, why, how to test

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
