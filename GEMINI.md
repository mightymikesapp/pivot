# GEMINI.md - Context & Operational Guide

## 🧠 Project Overview
**Name:** Legal Research Assistant MCP
**Type:** Python (FastMCP) Server
**Goal:** AI-powered legal research (Treatment Analysis, Citation Networks, Quote Verification) wrapping the CourtListener API.
**State:** Local development, synced with remote `mightymikesapp/pivot`.

## 🛠️ Development Environment
- **Dependency Manager:** `uv` (Strict requirement).
- **Python Version:** 3.12+
- **Linter/Formatter:** `ruff`
- **Type Checker:** `mypy`

## ⚡ Operational Commands
*Execute these exactly as written to ensure environment consistency.*

| Action | Command | Notes |
| :--- | :--- | :--- |
| **Sync Deps** | `uv sync` | Run after pulling changes. |
| **Unit Tests** | `uv run pytest` | Fast, mocks external APIs. Run frequently. |
| **Full Tests** | `uv run pytest --run-integration` | Slow, hits real APIs. Requires API Key. |
| **Linting** | `uv run ruff check .` | Fix auto-fixable with `--fix`. |
| **Type Check** | `uv run mypy app/` | Strict typing enforced. |
| **Run Server** | `uv run python -m app.server` | Starts MCP server on stdio. |

## 🏗️ Architecture & Mental Model

### Data Flow
1.  **MCP Request** (Claude/IDE) -> `app/server.py`
2.  **Tool Router** -> `app/tools/*.py` (Specific capability)
3.  **Logic Layer** -> `app/analysis/*.py` (Business logic, no API calls)
4.  **Data Layer** -> `app/mcp_client.py` (CourtListener API Wrapper)
5.  **Cache Layer** -> `app/cache.py` (Disk-based caching for API resilience)

### Key Directories
- `app/tools/`: User-facing tools (Research, Search, Verification).
- `app/analysis/`: Heavy lifting (Graph building, text processing).
- `app/mcp_client.py`: The *only* place HTTP requests happen.
- `tests/`: Mirrored structure. `conftest.py` handles async fixtures.

## 📝 Coding Standards (Gemini Preference)
1.  **Async First:** All I/O must be `async await`.
2.  **Type Hints:** Use `dict[str, Any]`, not `Dict`. Return typed objects/Pydantic models where possible.
3.  **Error Handling:** Catch specific exceptions in `mcp_client.py`, re-raise as user-friendly messages in `tools/`.
4.  **Testing:** deeply prefer `pytest-asyncio`. Mock `mcp_client.get_client()` in unit tests.

## 🧩 Current Roadmap / Active Context
- **Focus:** Stability and reliability of the CourtListener integration.
- **Recent Fixes:** Timezone awareness (UTC), Dependency Injection in Search, global side-effect removal.
- **Next Steps:**
    - Local Brief Analyzer (RAG).
    - Recursive Research Agent.
    - Interactive Frontend (React/Next.js).

## 🛑 Critical Rules
1.  **Never** commit secrets (`.env`).
2.  **Always** run `uv run pytest` before committing.
3.  **Do not** assume `pip` or `python` maps to the venv; use `uv run`.
