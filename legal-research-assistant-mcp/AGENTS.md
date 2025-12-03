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

## External APIs
- CourtListener API: Rate limited, cache responses
- Always use retry/backoff for external calls
