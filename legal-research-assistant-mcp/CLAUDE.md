# CLAUDE.md - AI Assistant Development Guide

> **Purpose**: This document provides AI assistants with comprehensive guidance for understanding, navigating, and modifying the Legal Research Assistant MCP codebase.

**Last Updated**: 2025-12-04
**Python Version**: 3.12+
**Framework**: FastMCP 0.3+
**Project Type**: Model Context Protocol (MCP) Server for Legal Research

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Design Patterns](#architecture--design-patterns)
3. [Codebase Structure](#codebase-structure)
4. [Development Workflow](#development-workflow)
5. [Testing Conventions](#testing-conventions)
6. [Code Style Guidelines](#code-style-guidelines)
7. [Common Tasks](#common-tasks)
8. [Key Concepts](#key-concepts)
9. [Integration Points](#integration-points)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

### What This Project Does

The Legal Research Assistant MCP is a **wrapper/orchestrator** that:
- Wraps the CourtListener API (Free Law Project)
- Adds intelligent analysis layers on top of raw legal data
- Exposes 20+ MCP tools for legal research workflows
- Provides case validity checking (Shepardizing alternative)
- Verifies quotes with fuzzy matching
- Builds citation networks with treatment signals
- Enables semantic search over case law

### Core Value Propositions

1. **Case Treatment Analysis** - Determines if cases are still "good law"
2. **Quote Verification** - Validates quotes against actual opinion text
3. **Citation Network Visualization** - Maps case relationships with Mermaid diagrams
4. **Semantic Search** - AI-powered case discovery beyond keyword matching
5. **Intelligent Caching** - Multi-layer cache reduces API calls by 70-90%

### Key Metrics

- **4,235 lines** of production code
- **285+ tests** with 80% minimum coverage requirement
- **20+ MCP tools** exposed to clients
- **23 treatment signals** (12 negative, 11 positive)
- **3-tier caching** (metadata: 24h, text: 7d, search: 1h)

---

## Architecture & Design Patterns

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   MCP Client (Claude Desktop, etc.)         │
└───────────────────────────┬─────────────────────────────────┘
                            │ stdio transport
┌───────────────────────────▼─────────────────────────────────┐
│                   FastMCP Server (app/server.py)            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tool Modules (app/tools/)                           │   │
│  │  - treatment.py     - verification.py                │   │
│  │  - network.py       - search.py                      │   │
│  │  - research.py      - cache_tools.py                 │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │  Analysis Modules (app/analysis/)                    │   │
│  │  - treatment_classifier.py  - quote_matcher.py       │   │
│  │  - citation_network.py      - mermaid_generator.py   │   │
│  │  - search/vector_store.py                            │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │  Infrastructure (app/)                               │   │
│  │  - mcp_client.py (API wrapper)                       │   │
│  │  - cache.py (file-based cache)                       │   │
│  │  - config.py (settings)                              │   │
│  │  - logging_config.py (structured logging)            │   │
│  └──────────────────────┬───────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│               CourtListener API v4 (External)               │
└─────────────────────────────────────────────────────────────┘
```

### Design Patterns

#### 1. Wrapper/Orchestrator Pattern
- **Purpose**: Add intelligence layer without rebuilding CourtListener
- **Implementation**: MCP server wraps API, adds analysis capabilities
- **Key Files**: `app/mcp_client.py`, `app/tools/*.py`

#### 2. Two-Pass Analysis Strategy
```python
# Pass 1: Fast metadata + snippet analysis
initial_signals = classify_from_snippet(case)

# Pass 2: Smart full-text fetching (configurable)
if strategy == "smart" and has_negative_signal(initial_signals):
    full_text = await client.get_opinion_full_text(case_id)
    refined_signals = classify_from_full_text(full_text)
```
**Strategies**: `always`, `smart` (default), `negative_only`, `never`
**Location**: `app/analysis/treatment_classifier.py`

#### 3. Smart Scout Strategy (Semantic Search)
```python
# 1. Broad keyword search → candidate pool
candidates = await search_courtlistener(query)

# 2. Fetch full text for candidates
texts = await batch_fetch_full_text(candidates)

# 3. Embed & store locally
vector_store.add_documents(texts)

# 4. Semantic re-ranking
results = vector_store.search(query, top_k=limit)
```
**Location**: `app/tools/search.py`, `app/analysis/search/vector_store.py`

#### 4. Multi-Layer Caching
```python
Cache.METADATA   # 24h TTL - citations, case names, metadata
Cache.TEXT       # 7d TTL - full opinion text
Cache.SEARCH     # 1h TTL - search results
```
**Benefits**: 70-90% reduction in API calls, faster response times
**Location**: `app/cache.py`

#### 5. Circuit Breaker Pattern
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.RequestError)
)
```
**Trigger**: 5 consecutive failures → 60s backoff
**Location**: `app/mcp_client.py`

---

## Codebase Structure

### Directory Layout

```
legal-research-assistant-mcp/
├── app/
│   ├── __init__.py
│   ├── __main__.py              # Entry point: python -m app
│   ├── server.py                # FastMCP server setup (179 lines)
│   ├── mcp_client.py            # CourtListener API client (660+ lines)
│   ├── config.py                # Pydantic configuration (148 lines)
│   ├── cache.py                 # File-based cache with TTL (206 lines)
│   ├── logging_config.py        # Structured JSON logging
│   ├── logging_utils.py         # Logging decorators
│   ├── management.py            # Management utilities
│   ├── types.py                 # TypedDict definitions
│   ├── mcp_types.py             # MCP-specific types
│   ├── settings_base.py         # Base settings class
│   ├── py.typed                 # PEP 561 marker
│   │
│   ├── tools/                   # MCP tool implementations (user-facing)
│   │   ├── __init__.py
│   │   ├── treatment.py         # check_case_validity, get_citing_cases
│   │   ├── verification.py      # verify_quote, batch_verify_quotes
│   │   ├── network.py           # build_citation_network, visualize_*
│   │   ├── search.py            # semantic_search, purge_memory
│   │   ├── research.py          # run_research_pipeline, issue_map
│   │   └── cache_tools.py       # cache_stats, cache_clear
│   │
│   └── analysis/                # Core analysis modules (internal logic)
│       ├── __init__.py
│       ├── treatment_classifier.py   # Signal detection (350+ lines)
│       ├── quote_matcher.py          # Quote verification (300+ lines)
│       ├── citation_network.py       # Graph construction (280+ lines)
│       ├── mermaid_generator.py      # Diagram generation (600+ lines)
│       └── search/
│           ├── __init__.py
│           └── vector_store.py       # ChromaDB integration (200+ lines)
│
├── tests/                       # 30 test files, 285+ test functions
│   ├── conftest.py              # Shared pytest fixtures
│   ├── integration/
│   │   ├── test_caching.py
│   │   └── test_research_workflows.py
│   ├── test_treatment.py
│   ├── test_quote_matcher.py
│   ├── test_citation_network.py
│   ├── test_mermaid_generator.py
│   ├── test_mcp_client.py
│   ├── test_semantic_search.py
│   ├── test_cache.py
│   └── [22 more test files]
│
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI/CD
│
├── pyproject.toml               # Project metadata, dependencies, tool configs
├── .env.example                 # Environment variable template
├── .gitignore
├── README.md                    # User-facing documentation (735 lines)
├── AGENTS.md                    # Developer guidelines
├── API_FIX_SUMMARY.md           # API migration notes
└── FULL_TEXT_ENHANCEMENT.md     # Feature documentation
```

### File Responsibilities

| Category | Files | Purpose |
|----------|-------|---------|
| **Entry Points** | `__main__.py`, `server.py` | Server initialization and tool registration |
| **External API** | `mcp_client.py` | CourtListener API wrapper with retry/caching |
| **Configuration** | `config.py`, `.env.example` | Settings management and environment config |
| **Infrastructure** | `cache.py`, `logging_config.py`, `logging_utils.py` | Core utilities |
| **Tool Layer** | `tools/*.py` | MCP-exposed tools (public API) |
| **Analysis Layer** | `analysis/*.py` | Internal analysis logic (private) |
| **Type Definitions** | `types.py`, `mcp_types.py` | Shared type definitions |
| **Tests** | `tests/*.py` | Unit and integration tests |

---

## Development Workflow

### Setup Commands

```bash
# Clone repository
git clone <repo-url>
cd legal-research-assistant-mcp

# Install uv package manager (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --dev

# Configure environment
cp .env.example .env
# Edit .env and set COURTLISTENER_API_KEY

# Run tests
uv run pytest                    # Unit tests only
uv run pytest --run-integration  # Include integration tests

# Lint and type check
uv run ruff check .              # Lint
uv run ruff format .             # Auto-format
uv run mypy app/                 # Type check

# Run server
python -m app.server             # Or: uv run python -m app.server
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/description

# Make changes, run tests
uv run pytest
uv run ruff check .
uv run mypy app/

# Commit changes
git add .
git commit -m "feat: description"

# Push and create PR
git push origin feature/description
```

### CI/CD Pipeline

**Trigger**: Push to `main`, PRs to `main`

**Steps**:
1. **Setup**: Ubuntu latest, Python 3.12, uv installation
2. **Install**: `uv sync --dev` (with retry logic)
3. **Lint**: `ruff format --check`, `ruff check`
4. **Type Check**: `mypy --strict app/`
5. **Test**:
   - Unit tests: `pytest -m "unit" --cov=app --cov-fail-under=80`
   - Integration tests: `pytest -m "integration"` (requires API key)

**Location**: `.github/workflows/ci.yml`

---

## Testing Conventions

### Test Organization

```python
# tests/conftest.py - Shared fixtures
@pytest.fixture
def mock_client():
    """Mocks CourtListener API client with Roe v. Wade test data."""
    # Returns client with mocked: lookup_citation, find_citing_cases, get_opinion_full_text

@pytest.fixture
def event_loop():
    """Fresh async event loop for each test."""
```

### Test Markers

```python
@pytest.mark.unit          # Unit tests (default, no API calls)
@pytest.mark.integration   # Integration tests (requires COURTLISTENER_API_KEY)
```

### Test Patterns

#### Unit Test Example
```python
@pytest.mark.unit
async def test_classify_treatment_signals(mock_client):
    """Test treatment signal classification from snippet."""
    # Arrange
    snippet = "overruled on other grounds by..."

    # Act
    result = classify_treatment_signals(snippet)

    # Assert
    assert result["classification"] == "negative"
    assert result["confidence"] >= 0.7
    assert "overruled" in result["signals"]
```

#### Integration Test Example
```python
@pytest.mark.integration
async def test_verify_quote_real_api(real_client):
    """Test quote verification with real CourtListener API."""
    # Requires COURTLISTENER_API_KEY in environment
    quote = "the right of privacy... is broad enough to encompass"
    citation = "410 U.S. 113"

    result = await verify_quote(quote, citation)

    assert result["verified"] is True
    assert result["match_type"] in ["exact", "fuzzy"]
```

### Running Tests

```bash
# Unit tests only (default)
uv run pytest

# Integration tests (requires API key)
uv run pytest --run-integration

# Specific file
uv run pytest tests/test_treatment.py

# Specific test
uv run pytest tests/test_treatment.py::test_classify_treatment_signals

# With coverage
uv run pytest --cov=app --cov-report=html

# Verbose output
uv run pytest -v
```

### Coverage Requirements

- **Minimum**: 80% code coverage on `app/` modules
- **Checked in CI**: Yes, with `--cov-fail-under=80`
- **Report**: HTML coverage report generated in `htmlcov/`

---

## Code Style Guidelines

### Python Standards

- **Version**: Python 3.12+
- **Type Checking**: `mypy --strict` (no untyped code)
- **Linting**: `ruff` with 100-character line limit
- **Formatting**: `ruff format` (auto-formatter)
- **Imports**: Sorted alphabetically (ruff enforces)

### Type Annotations

```python
# GOOD: Full type annotations
async def verify_quote(
    quote: str,
    citation: str,
    pinpoint: str | None = None
) -> dict[str, Any]:
    """Verify quote against opinion text."""

# BAD: Missing return type
async def verify_quote(quote: str, citation: str):
    ...
```

### Async Conventions

```python
# GOOD: Async for external calls
async def get_case_data(citation: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# BAD: Sync for I/O-bound operations
def get_case_data(citation: str) -> dict[str, Any]:
    response = requests.get(url)  # Blocks event loop
    return response.json()
```

### Logging

```python
# GOOD: Structured logging with context
logger.info(
    "Quote verified",
    extra={
        "citation": citation,
        "match_type": "exact",
        "confidence": 1.0,
        "request_id": get_request_id()
    }
)

# BAD: print() statements
print(f"Quote verified: {citation}")  # Never use print()
```

### Error Handling

```python
# GOOD: Return errors as dicts for MCP tools
@mcp.tool()
async def verify_quote(quote: str, citation: str) -> dict[str, Any]:
    try:
        result = await _verify_quote_impl(quote, citation)
        return result
    except Exception as e:
        logger.error(f"Quote verification failed: {e}")
        return {"error": str(e), "citation": citation}

# BAD: Unhandled exceptions crash the server
@mcp.tool()
async def verify_quote(quote: str, citation: str) -> dict[str, Any]:
    result = await _verify_quote_impl(quote, citation)  # May raise
    return result
```

### Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| **Functions** | `snake_case` | `verify_quote()` |
| **Classes** | `PascalCase` | `TreatmentClassifier` |
| **Constants** | `UPPER_SNAKE_CASE` | `MAX_DEPTH = 3` |
| **Private** | `_leading_underscore` | `_classify_internal()` |
| **MCP Tools** | `snake_case` (descriptive) | `build_citation_network()` |

---

## Common Tasks

### Adding a New MCP Tool

1. **Create tool function in appropriate module** (`app/tools/`)
```python
# app/tools/my_module.py
from fastmcp import FastMCP
from app.logging_utils import tool_logging

mcp = FastMCP("my-module")

@mcp.tool()
@tool_logging("my_new_tool")
async def my_new_tool(param: str) -> dict[str, Any]:
    """
    Tool description for AI clients.

    Args:
        param: Parameter description

    Returns:
        Result dictionary with keys: result, status, etc.
    """
    try:
        # Implementation
        result = await _process(param)
        return {"result": result, "status": "success"}
    except Exception as e:
        logger.error(f"Tool failed: {e}")
        return {"error": str(e), "status": "error"}
```

2. **Register tool in server** (`app/server.py`)
```python
from app.tools.my_module import mcp as my_module_server

def setup():
    # ... existing imports ...
    mcp.import_server(my_module_server)
```

3. **Add tests** (`tests/test_my_module.py`)
```python
@pytest.mark.unit
async def test_my_new_tool():
    result = await my_new_tool("test")
    assert result["status"] == "success"
```

4. **Update documentation** (`README.md`)

### Adding a New Analysis Module

1. **Create module** (`app/analysis/my_analyzer.py`)
```python
from typing import Any

class MyAnalyzer:
    def __init__(self, config: dict[str, Any]):
        self.config = config

    async def analyze(self, data: str) -> dict[str, Any]:
        """Core analysis logic."""
        # Implementation
        return {"analysis": result}
```

2. **Import in tools layer** (`app/tools/my_module.py`)
```python
from app.analysis.my_analyzer import MyAnalyzer

analyzer = MyAnalyzer(config)
result = await analyzer.analyze(data)
```

3. **Add unit tests** for analysis module
4. **Add integration tests** for tool using analyzer

### Modifying CourtListener API Client

**Location**: `app/mcp_client.py`

**Pattern**:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def new_api_method(self, param: str) -> dict[str, Any]:
    """
    Call CourtListener API endpoint.

    Args:
        param: API parameter

    Returns:
        API response data
    """
    # Check cache first
    cache_key = f"api_method:{param}"
    if cached := self.cache.get(cache_key, Cache.METADATA):
        logger.debug("Cache hit", extra={"key": cache_key})
        return cached

    # Make API request
    url = f"{self.base_url}/endpoint/{param}/"
    async with self.client.get(url) as response:
        response.raise_for_status()
        data = response.json()

    # Cache result
    self.cache.set(cache_key, data, Cache.METADATA)
    return data
```

### Adding Configuration Options

1. **Update `.env.example`**
```bash
# New feature configuration
MY_NEW_OPTION=default_value
```

2. **Add to `app/config.py`**
```python
class Settings(BaseSettings):
    # ... existing settings ...

    my_new_option: str = Field(
        default="default_value",
        description="Description of the option"
    )
```

3. **Use in code**
```python
from app.config import settings

value = settings.my_new_option
```

---

## Key Concepts

### Treatment Signals

**Definition**: How later cases cite earlier cases (positive/negative/neutral)

**23 Signal Types**:

**Negative (12)**: Weight 0.5-1.0
- `overruled` (1.0) - Case explicitly overruled
- `abrogated` (1.0) - Case law abrogated by statute/rule
- `reversed` (0.9) - Reversed on appeal
- `vacated` (0.9) - Decision vacated
- `criticized` (0.7) - Critical treatment
- `questioned` (0.7) - Validity questioned
- `limited` (0.6) - Holding limited
- `distinguished` (0.5) - Factually distinguished
- `superseded` (0.8) - Superseded by statute
- `declined_to_follow` (0.7) - Explicitly declined
- `not_followed` (0.6) - Not followed
- `disapproved` (0.8) - Disapproved

**Positive (11)**: Weight 0.6-1.0
- `followed` (1.0) - Explicitly followed
- `affirmed` (1.0) - Affirmed on appeal
- `adopted` (0.9) - Reasoning adopted
- `approved` (0.9) - Approved
- `cited_favorably` (0.8) - Favorably cited
- `relied_upon` (0.9) - Relied upon
- `applied` (0.8) - Applied to facts
- `explained` (0.7) - Explained favorably
- `harmonized` (0.7) - Harmonized with other cases
- `confirmed` (0.8) - Confirmed
- `reinforced` (0.6) - Reasoning reinforced

**Location**: `app/analysis/treatment_classifier.py`

### Quote Verification Matching

**Exact Match** (Threshold: 1.0)
- Normalized whitespace and punctuation
- Case-insensitive
- Removes line breaks, extra spaces

**Fuzzy Match** (Threshold: 0.85)
- Uses `difflib.SequenceMatcher`
- Accounts for OCR errors, minor differences
- Returns similarity ratio 0.0-1.0

**Match Confidence**:
- `1.0` = Exact match
- `0.85-0.99` = Fuzzy match (high confidence)
- `< 0.85` = No match

**Location**: `app/analysis/quote_matcher.py`

### Citation Network Metrics

**Node Centrality**:
- **In-degree**: Number of citing cases
- **Out-degree**: Number of cited cases
- **PageRank**: Importance based on citation graph

**Network Statistics**:
- **Total nodes**: Number of cases in network
- **Total edges**: Number of citations
- **Network density**: Ratio of actual to possible edges
- **Average degree**: Mean citations per case
- **Connected components**: Number of disconnected subgraphs

**Location**: `app/analysis/citation_network.py`

### Semantic Search Reranking

**Two-Stage Process**:
1. **Broad Search**: Keyword search on CourtListener API
2. **Semantic Reranking**: Local vector similarity on full text

**Embedding Model**: `all-MiniLM-L6-v2` (Sentence Transformers)
- 80MB model size
- 384-dimensional embeddings
- Fast inference on CPU

**Storage**: ChromaDB (local vector database)

**Location**: `app/analysis/search/vector_store.py`

---

## Integration Points

### CourtListener API v4

**Base URL**: `https://www.courtlistener.com/api/rest/v4/`
**Authentication**: Token in `Authorization: Token <key>` header
**Rate Limits**: Respect API quotas (handled by circuit breaker)

**Key Endpoints**:
- `/search/`: Search opinions
- `/opinions/<id>/`: Get opinion metadata
- `/opinions/<id>/full_text/`: Get full opinion text
- `/citations/lookup/`: Look up citation

**Documentation**: https://www.courtlistener.com/help/api/

### FastMCP Framework

**Tool Definition**:
```python
@mcp.tool()
async def tool_name(param: str) -> dict[str, Any]:
    """Tool description."""
    return {"result": "value"}
```

**Server Registration**:
```python
mcp.import_server(tool_module_server)
```

**Documentation**: https://github.com/jlowin/fastmcp

### ChromaDB (Vector Database)

**Initialization**:
```python
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="legal_cases",
    embedding_function=SentenceTransformerEmbeddingFunction()
)
```

**Operations**:
- `collection.add()` - Add documents
- `collection.query()` - Semantic search
- `collection.get()` - Retrieve by ID

**Location**: `app/analysis/search/vector_store.py`

---

## Troubleshooting

### Common Issues

#### API Authentication Errors

**Symptom**: `401 Unauthorized` from CourtListener API

**Solutions**:
1. Check `.env` has `COURTLISTENER_API_KEY` or `COURT_LISTENER_API_KEY`
2. Verify key is valid at https://www.courtlistener.com/profile/
3. Check key has no leading/trailing whitespace

**Location**: `app/config.py` (loads both key names)

#### Cache Issues

**Symptom**: Stale data, incorrect results

**Solutions**:
```bash
# Clear all caches
uv run python -c "from app.cache import cache; cache.clear()"

# Or use MCP tool
# Call: cache_clear(cache_type="all")
```

**Symptom**: Disk space issues

**Solutions**:
1. Check cache directory size: `du -sh ~/.cache/legal-research-assistant-mcp/`
2. Clear old caches: Use `cache_tools.cache_clear()`
3. Reduce TTLs in `.env`

#### Vector Store Model Download Failures

**Symptom**: `ConnectionError` downloading Sentence Transformers model

**Solutions**:
1. Pre-download model: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`
2. Check internet connection
3. Check disk space (~80MB required)

#### Test Failures

**Symptom**: Integration tests fail with `401 Unauthorized`

**Solution**: Set `COURTLISTENER_API_KEY` in environment before running:
```bash
export COURTLISTENER_API_KEY=your_key
uv run pytest --run-integration
```

**Symptom**: Type checking fails with `mypy`

**Solutions**:
1. Ensure all functions have return type annotations
2. Use `from typing import Any` for flexible types
3. Check `pyproject.toml` has `allow_untyped_decorators = true`

### Debugging Tips

#### Enable Debug Logging

```python
# In .env
LOG_LEVEL=DEBUG

# Or programmatically
import logging
logging.getLogger("app").setLevel(logging.DEBUG)
```

#### Track Request IDs

All log messages include `request_id` for correlation:
```python
from app.logging_config import get_request_id

request_id = get_request_id()  # Propagates through async context
```

#### Inspect Cache Contents

```python
from app.cache import cache

# Get cache stats
stats = cache.stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")

# Get specific cached value
value = cache.get("key", Cache.METADATA)
```

#### Test API Calls Manually

```python
from app.mcp_client import CourtListenerAPIClient
from app.config import settings

client = CourtListenerAPIClient(settings)
result = await client.lookup_citation("410 U.S. 113")
```

---

## Best Practices for AI Assistants

### When Modifying Code

1. **Read existing code first** - Never modify files you haven't read
2. **Run tests before and after** - Ensure changes don't break existing functionality
3. **Follow existing patterns** - Match the style and architecture already in use
4. **Update tests** - Add/modify tests for any code changes
5. **Update documentation** - Keep README.md and this file in sync

### When Adding Features

1. **Check for existing implementations** - Search codebase before adding duplicates
2. **Use analysis modules** - Keep tools thin, logic in analysis layer
3. **Add configuration options** - Make features configurable via `.env`
4. **Write comprehensive tests** - Both unit and integration tests
5. **Document in README.md** - Add usage examples for new tools

### When Debugging

1. **Check logs first** - Structured logging provides rich context
2. **Verify configuration** - Ensure `.env` is correct
3. **Test in isolation** - Use unit tests to isolate issues
4. **Check API status** - CourtListener API may be down
5. **Clear caches** - Stale data can cause mysterious issues

### When Reviewing Code

1. **Type safety** - All code should pass `mypy --strict`
2. **Error handling** - All tools should return `{"error": "..."}` on failure
3. **Async correctness** - External calls must be async
4. **Logging, not printing** - Never use `print()`, always use `logger`
5. **Test coverage** - New code should maintain 80% coverage

---

## Quick Reference

### Project Commands

```bash
# Development
uv sync --dev                    # Install dependencies
uv run pytest                    # Run unit tests
uv run pytest --run-integration  # Run all tests
uv run ruff check .              # Lint
uv run ruff format .             # Format
uv run mypy app/                 # Type check

# Server
python -m app.server             # Run MCP server

# Testing
pytest tests/test_treatment.py   # Specific file
pytest -v                        # Verbose output
pytest --cov=app                 # With coverage

# Debugging
pytest -v -s                     # Show print/log output
pytest --pdb                     # Drop into debugger on failure
```

### Key Files to Know

| File | Purpose | When to Edit |
|------|---------|-------------|
| `app/server.py` | Tool registration | Adding new tool modules |
| `app/mcp_client.py` | API client | New API endpoints |
| `app/config.py` | Configuration | New settings |
| `app/tools/*.py` | MCP tools | New user-facing features |
| `app/analysis/*.py` | Core logic | New analysis capabilities |
| `tests/conftest.py` | Test fixtures | Shared test setup |
| `pyproject.toml` | Dependencies | Adding packages |
| `.env.example` | Config template | New environment variables |

### Environment Variables

```bash
# Required
COURTLISTENER_API_KEY=your_key_here

# Optional (with defaults)
COURTLISTENER_BASE_URL=https://www.courtlistener.com/api/rest/v4/
COURTLISTENER_TIMEOUT=30
CACHE_ENABLED=true
CACHE_TTL_METADATA=86400    # 24 hours
CACHE_TTL_TEXT=604800        # 7 days
CACHE_TTL_SEARCH=3600        # 1 hour
LOG_LEVEL=INFO
LOG_FORMAT=json
TREATMENT_CONFIDENCE_THRESHOLD=0.7
TREATMENT_FULL_TEXT_STRATEGY=smart
MAX_NETWORK_DEPTH=3
MAX_NETWORK_NODES=100
```

---

**End of CLAUDE.md**

For user-facing documentation, see `README.md`.
For developer setup, see `AGENTS.md`.
For API migration history, see `API_FIX_SUMMARY.md`.
