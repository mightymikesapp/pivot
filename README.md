# Legal Research Assistant MCP

An advanced Model Context Protocol (MCP) server providing intelligent legal research capabilities built on top of CourtListener.
This server adds treatment analysis, citation networks, quote verification, and advanced visualizations to enhance legal research workflows in Obsidian and other MCP-compatible environments.

## 🎯 Features

### ✅ Treatment Analysis (Shepardizing Alternative)
**Determine if a case is still good law** - Our treatment analyzer examines citing cases and provides confidence-scored validity assessments.

- **Automated case validity checking** - Analyzes treatment signals from citing cases
- **12 negative signal patterns** (overruled, abrogated, reversed, etc.)
- **11 positive signal patterns** (followed, affirmed, adopted, etc.)
- **Two-pass analysis** - Smart full-text fetching strategy (always, smart, negative_only, never)
- **Confidence scoring** (0-1 scale) with detailed warnings
- **Context extraction** showing relevant excerpts
- **Research request ID tracking** - Correlation IDs for debugging and tracing

### ✅ Quote Verification
**Maintain academic integrity** - Verify that quotes accurately appear in cited cases.

- **Exact match finding** - Locates precise quotes in case text
- **Fuzzy matching** (85% threshold) - Finds similar passages with minor variations
- **Context extraction** (200+ chars before/after)
- **Batch verification** - Check multiple quotes at once
- **HTML text normalization** - Handles various text formats
- **Difference detection** - Shows specific discrepancies
- **Pinpoint citation support** - Page/section/paragraph detection and alignment
- **Quote grounding information** - Context and relevance metrics

### ✅ Citation Network Visualization
**Visualize precedent relationships** - Build and analyze citation graphs with beautiful Mermaid diagrams.

- **Network construction** - Build citation graphs from CourtListener data
- **Multiple diagram types:**
  - **Flowcharts** - Hierarchical citation networks
  - **Graphs** - Simplified network views
  - **Timelines** - Citations over time
- **Treatment-based coloring** - Visual distinction of positive/negative signals
- **Advanced analytics** - PageRank, eigenvector centrality, community detection
- **Influence scoring** - Identify most important cases with customizable weighting
- **Statistical analysis** - Temporal and court distribution with hierarchical court weighting
- **Export formats** - GraphML and JSON for external analysis tools
- **Obsidian-ready** - Copy-paste Mermaid syntax directly into notes
- **Comprehensive reports** - Markdown-formatted with diagrams and statistics

### ✅ Semantic Search
**Find cases by conceptual similarity** - Vector-based intelligent search across legal opinions.

- **Smart Scout strategy** - Broad keyword search → full text fetching → semantic re-ranking
- **Vector indexing** - Persistent embeddings using sentence-transformers
- **Batch processing** - Efficient bulk case processing with rate-limit awareness
- **Deduplication** - Intelligent handling of existing documents
- **Customizable persistence** - Store embeddings locally or in memory
- **Integration with existing tools** - Combine with citation networks and treatment analysis

## 🏗️ Architecture

This MCP uses the **Wrapper/Orchestrator Pattern**, calling the CourtListener API directly while providing an intelligence layer for advanced analysis:

```
┌─────────────────────────────────────────┐
│  Legal Research Assistant MCP           │
│  (Intelligence Layer)                   │
│                                         │
│  ✓ Treatment Analysis                  │
│  ✓ Citation Networks                   │
│  ✓ Quote Verification                  │
│  ✓ Semantic Search                     │
│  ✓ Research Pipelines                  │
│  ✓ Mermaid Visualizations              │
└──────────┬──────────────────────────────┘
           │ calls ↓
┌──────────▼─────────────────┐  ┌──────────────────────┐
│  CourtListener API         │  │  Vector Store        │
│  (Free Law Project)        │  │  (Chromadb)          │
│  (Data Access Layer)       │  │  (Embeddings/Cache)  │
└────────────────────────────┘  └──────────────────────┘
```

## 🚀 Quickstart

The project uses [uv](https://github.com/astral-sh/uv) for dependency management and Python 3.12+.

```bash
# Clone and enter the repository
git clone https://github.com/mightymikesapp/legal-research-assistant-mcp.git
cd legal-research-assistant-mcp

# Install dependencies
uv sync

# Copy environment configuration template and customize
cp .env.example .env

# Add your CourtListener API key (either alias works)
echo "COURT_LISTENER_API_KEY=your_key_here" >> .env
```

### 🚀 Running the Server

```bash
# Start the MCP server
uv run python -m app.server

# Or launch via the MCP CLI (e.g., Claude Desktop)
# The server will be available as "Legal Research Assistant MCP"
```

## ⚙️ Configuration

Use `.env.example` as a reference for available settings. Key options include:

### API & Authentication
- `COURT_LISTENER_API_KEY` / `COURTLISTENER_API_KEY` - CourtListener API key (aliases supported)

### CourtListener API Settings
- `COURTLISTENER_BASE_URL` - API base URL (default: https://www.courtlistener.com/api/rest/v3)
- `COURTLISTENER_TIMEOUT` - Request timeout in seconds (default: 30)
- `COURTLISTENER_MAX_RETRIES` - Maximum retry attempts (default: 3)
- `COURTLISTENER_RETRY_BACKOFF_FACTOR` - Exponential backoff multiplier (default: 2)

### Treatment Analysis Settings
- `FETCH_FULL_TEXT_STRATEGY` - Full-text fetching strategy: `always`, `smart` (default), `negative_only`, `never`
- `MAX_FULL_TEXT_FETCHES` - Maximum full-text fetches per analysis (default: 5)
- `CONFIDENCE_THRESHOLD` - Minimum confidence score (default: 0.5)
- `CITING_CASE_LIMIT` - Maximum citing cases to analyze per treatment check (default: 100)

### Citation Network Settings
- `NETWORK_MAX_DEPTH` - Maximum recursion depth for network building (default: 2)
- `NETWORK_MAX_NODES` - Maximum nodes in citation network (default: 100)
- `ENABLE_ADVANCED_METRICS` - Compute PageRank and centrality (default: true)
- `ENABLE_COMMUNITY_DETECTION` - Use graph clustering (default: true)

### Semantic Search Settings
- `SEMANTIC_SEARCH_ENABLED` - Enable vector-based search (default: true)
- `SEMANTIC_SEARCH_PERSISTENCE_PATH` - Directory for embeddings storage (default: `.cache/embeddings`)
- `SEMANTIC_SEARCH_MODEL` - Embedding model name (default: `all-MiniLM-L6-v2`)
- `SEMANTIC_SEARCH_BATCH_SIZE` - Batch size for vector indexing (default: 32)

### Cache Settings
- `CACHE_ENABLED` - Enable caching (default: true)
- `CACHE_DIRECTORY` - Cache storage path (default: `.cache`)
- `CACHE_METADATA_TTL` - Metadata cache TTL in seconds (default: 86400, 24 hours)
- `CACHE_TEXT_TTL` - Full-text cache TTL in seconds (default: 604800, 7 days)
- `CACHE_SEARCH_TTL` - Search result cache TTL in seconds (default: 259200, 3 days)
- `CACHE_MAX_SIZE_MB` - Maximum cache size in MB (default: 1000)

### Logging Settings
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `LOG_FORMAT` - Log format: simple, detailed, json (default: detailed)
- `LOG_DATE_FORMAT` - Date format in logs (default: `%Y-%m-%d %H:%M:%S`)
- `LOG_INCLUDE_REQUEST_ID` - Include correlation IDs in logs (default: true)

After copying the template, adjust values in `.env` to match your environment and preferences.

## 🛠️ Available Tools

### Treatment Analysis Tools

#### `check_case_validity(citation: str) → dict`
Analyzes whether a case is still good law by examining citing cases and treatment signals.

**Example:**
```python
result = await check_case_validity("410 U.S. 113")
```

**Returns:**
```json
{
  "citation": "410 U.S. 113",
  "case_name": "Roe v. Wade",
  "valid": false,
  "confidence": 0.95,
  "overall_treatment": "questioned",
  "citing_cases_count": 12,
  "treatment_summary": {
    "negative_signals": 5,
    "positive_signals": 3,
    "neutral_citations": 4
  },
  "warnings": ["Case has been overruled", "Multiple negative treatments found"],
  "recommendation": "Use with caution - significant negative treatment"
}
```

#### `get_citing_cases(citation: str, limit: int = 100) → dict`
Retrieves all cases that cite a given citation with treatment classification.

### Quote Verification Tools

#### `verify_quote(quote: str, citation: str, pinpoint: str = None) → dict`
Verifies that a quote accurately appears in the cited case.

**Example:**
```python
result = await verify_quote(
    quote="the right of privacy",
    citation="410 U.S. 113"
)
```

**Returns:**
```json
{
  "citation": "410 U.S. 113",
  "case_name": "Roe v. Wade",
  "quote": "the right of privacy",
  "found": true,
  "exact_match": true,
  "similarity": 1.0,
  "matches_found": 2,
  "best_match": {
    "position": 52398,
    "matched_text": "the right of privacy",
    "context_before": "...has an unlimited right to do with one's body as one pleases bears a close relationship to ",
    "context_after": " previously articulated in the Court's decisions. The Court has refused to recognize...",
    "differences": []
  },
  "recommendation": "Quote verified exactly in source"
}
```

#### `batch_verify_quotes(quotes: list[dict]) → dict`
Verifies multiple quotes in a single operation.

### Citation Network Tools

#### `build_citation_network(citation: str, max_depth: int = 2, max_nodes: int = 100) → dict`
Constructs a citation network graph showing precedent relationships.

**Example:**
```python
network = await build_citation_network("410 U.S. 113", max_nodes=50)
```

**Returns:**
```json
{
  "root_citation": "410 U.S. 113",
  "root_case_name": "Roe v. Wade",
  "nodes": [...],
  "edges": [...],
  "statistics": {
    "total_nodes": 51,
    "total_edges": 50,
    "treatment_distribution": {
      "overruled": 3,
      "questioned": 2,
      "followed": 15,
      "cited": 30
    }
  }
}
```

#### `visualize_citation_network(citation: str, diagram_type: str = "flowchart") → dict`
Generates Mermaid diagram visualization of a citation network.

**Diagram Types:**
- `flowchart` - Hierarchical network with treatment colors
- `graph` - Simplified network view
- `timeline` - Citations over time
- `all` - All diagram types

**Example:**
```python
viz = await visualize_citation_network(
    citation="410 U.S. 113",
    diagram_type="flowchart",
    direction="TB",
    max_nodes=20
)

# Copy viz["mermaid_syntax"] and paste in Obsidian between ```mermaid tags
```

#### `generate_citation_report(citation: str, treatment_focus: list[str] = None) → dict`
Generates a comprehensive markdown report with visualizations and statistics.

**Example:**
```python
report = await generate_citation_report(
    citation="410 U.S. 113",
    include_diagram=True,
    treatment_focus=["overruled", "questioned"]
)

# Copy report["markdown_report"] directly into Obsidian
```

#### `get_network_statistics(citation: str) → dict`
Provides detailed statistical analysis of a citation network.

#### `filter_citation_network(citation: str, treatments: list[str], min_confidence: float) → dict`
Builds a filtered network showing only specific treatment types.

### Semantic Search Tools

#### `semantic_search(query: str, jurisdiction: str = None, limit: int = 20, rerank: bool = True) → dict`
Finds cases by conceptual similarity using vector embeddings and optional semantic re-ranking.

**Example:**
```python
results = await semantic_search(
    query="liability for failure to warn about product defects",
    jurisdiction="U.S.",
    limit=15,
    rerank=True
)
```

**Returns:**
```json
{
  "query": "liability for failure to warn about product defects",
  "results": [
    {
      "citation": "456 F.3d 789",
      "case_name": "Product Liability Corp v. Consumers",
      "similarity_score": 0.89,
      "snippet": "...failure to provide adequate warnings...",
      "jurisdiction": "2nd Circuit"
    }
  ],
  "vector_store_stats": {
    "total_cases_indexed": 5234,
    "search_method": "semantic_rerank"
  }
}
```

#### `purge_memory() → dict`
Clears the local vector store and resets embeddings cache.

#### `get_library_stats() → dict`
Returns statistics about the vector store (indexed cases, persistence path, etc.).

### Cache Management Tools

#### `cache_stats() → dict`
Reports cache hit rates, miss rates, and storage size by cache type.

**Example:**
```python
stats = await cache_stats()
# Returns hit/miss rates for metadata, text, and search caches
```

#### `cache_clear(cache_type: str = "all") → dict`
Clears cache by type: `metadata`, `text`, `search`, or `all`.

## 📊 Usage Examples

### Example 1: Check Case Validity

```python
from app.tools.treatment import check_case_validity

# Check if Roe v. Wade is still good law
result = await check_case_validity("410 U.S. 113")

if not result["valid"]:
    print(f"⚠️ Warning: {result['case_name']} may not be good law")
    print(f"Confidence: {result['confidence']:.0%}")
    print(f"Warnings: {', '.join(result['warnings'])}")
```

### Example 2: Verify Quotes in Paper

```python
from app.tools.verification import batch_verify_quotes

quotes_to_check = [
    {"quote": "the right of privacy", "citation": "410 U.S. 113"},
    {"quote": "State criminal abortion laws", "citation": "410 U.S. 113"},
]

results = await batch_verify_quotes(quotes_to_check)

for result in results["results"]:
    if not result["found"]:
        print(f"❌ Quote not found: {result['quote']}")
    elif not result["exact_match"]:
        print(f"⚠️ Fuzzy match: {result['quote']} ({result['similarity']:.0%})")
    else:
        print(f"✅ Verified: {result['quote']}")
```

### Example 3: Create Citation Network in Obsidian

```python
from app.tools.network import visualize_citation_network

# Generate visualization
viz = await visualize_citation_network(
    citation="410 U.S. 113",
    diagram_type="flowchart",
    direction="LR",
    max_nodes=30
)

# Print Mermaid syntax to copy into Obsidian
print("Copy this into your Obsidian note:")
print("```mermaid")
print(viz["mermaid_syntax"])
print("```")
```

### Example 4: Generate Research Report

```python
from app.tools.network import generate_citation_report

# Generate comprehensive report
report = await generate_citation_report(
    citation="410 U.S. 113",
    include_diagram=True,
    include_statistics=True,
    treatment_focus=["overruled", "questioned", "limited"],
    max_nodes=50
)

# Save to file or paste in Obsidian
with open("roe_citation_report.md", "w") as f:
    f.write(report["markdown_report"])
```

### Example 5: Semantic Search with Re-ranking

```python
from app.tools.search import semantic_search

# Find conceptually similar cases
results = await semantic_search(
    query="employment discrimination based on age",
    jurisdiction="U.S.",
    limit=20,
    rerank=True  # Re-rank by semantic similarity
)

for result in results["results"][:5]:
    print(f"📄 {result['case_name']} ({result['citation']})")
    print(f"   Similarity: {result['similarity_score']:.0%}")
    print(f"   {result['snippet']}\n")
```

### Example 6: Advanced Network Analysis with Metrics

```python
from app.tools.network import build_citation_network, get_network_statistics

# Build network with advanced metrics enabled
network = await build_citation_network(
    citation="410 U.S. 113",
    max_nodes=100,
    enable_advanced_metrics=True,
    enable_community_detection=True,
    weight_by_court_level=True,
    weight_by_treatment_polarity=True
)

# Get detailed statistics
stats = await get_network_statistics(citation="410 U.S. 113")

print(f"Most influential cases:")
for case in stats["influence_ranking"][:5]:
    print(f"  • {case['case_name']} (PageRank: {case['pagerank']:.3f})")

print(f"\nCommunity Clusters: {len(stats['communities'])}")
for i, community in enumerate(stats['communities']):
    print(f"  Cluster {i+1}: {len(community['nodes'])} cases")
```

### Example 7: Run Full Research Pipeline

```python
from app.tools.research import run_research_pipeline

# Execute comprehensive research workflow
pipeline_result = await run_research_pipeline(
    primary_citation="410 U.S. 113",
    quotes_to_verify=[
        "the right of privacy",
        "State criminal abortion laws"
    ],
    max_network_depth=3,
    max_network_nodes=50,
    semantic_search_enabled=True
)

print(f"Treatment: {pipeline_result['treatment_analysis']['overall_treatment']}")
print(f"Quote Verification: {pipeline_result['quote_verification']['verified_count']}/{len(quotes_to_verify)}")
print(f"Network Nodes: {len(pipeline_result['citation_network']['nodes'])}")
```

### Example 8: Manage Cache and Performance

```python
from app.tools.cache_tools import cache_stats, cache_clear

# Check cache performance
stats = await cache_stats()
print(f"Cache Hit Rate: {stats['metadata_hits']/stats['metadata_total']:.0%}")
print(f"Cache Size: {stats['total_size_mb']:.1f} MB")

# Clear cache if needed
if stats['total_size_mb'] > 500:
    await cache_clear("search")  # Clear search embeddings only
```

## 🧪 Testing

Run the automated suites with uv:

```bash
# Fast unit suite (default)
uv run pytest

# Full suite including integration checks (requires COURTLISTENER_API_KEY)
uv run pytest --run-integration
```

## 🚀 Advanced Features

### Two-Pass Treatment Analysis

The treatment analyzer uses a smart two-pass strategy for efficiency:

1. **First Pass (Fast)** - Analyze citing case metadata and available snippet text
2. **Second Pass (Smart)** - Conditionally fetch full text based on strategy:
   - `always` - Always fetch full text for all citing cases
   - `smart` - Fetch only for cases with negative signals (default)
   - `negative_only` - Fetch for negative signals, analyze positive cases by snippet
   - `never` - Never fetch, rely on snippet analysis only

**Smart fetching benefits:** Reduces API calls and latency while improving confidence scores for boundary cases.

### Network Weighting & Customization

Citation networks support multiple weighting strategies:

- **Court-level weighting** - Higher weights for SCOTUS → Circuit → District (e.g., SCOTUS=2.0x)
- **Treatment polarity weighting** - Positive treatments amplified, negative treatments dampened
- **Custom color palettes** - Hex-based court and treatment coloring
- **Community detection** - Automatic clustering using greedy modularity algorithms
- **Export formats** - GraphML (network analysis tools) and JSON (web visualization)

### Request ID Tracking & Correlation

All operations include unique request IDs for debugging:
- Correlation IDs propagated through nested tool calls
- Structured logging with request context
- Error traces tied to specific operations
- Performance metrics per request

### Caching & Resilience

Intelligent multi-layer caching:
- **Metadata cache** - Case names, citations, court info (24h TTL)
- **Full-text cache** - Opinion text (7d TTL)
- **Search cache** - Query results (3d TTL)
- **Adaptive retry logic** - Exponential backoff with jitter
- **Partial results** - Returns best-effort data with warnings if API limits hit
- **Rate-limit awareness** - Batch processing respects API quotas

## 📁 Project Structure

```
legal-research-assistant-mcp/
├── app/
│   ├── __init__.py
│   ├── __main__.py           # Entry point
│   ├── cache.py              # Cache utilities and interfaces
│   ├── config.py             # Configuration with Pydantic
│   ├── logging_utils.py      # Structured logging helpers
│   ├── mcp_client.py         # CourtListener API client
│   ├── server.py             # Main MCP server
│   ├── tools/                # MCP tool implementations
│   │   ├── cache_tools.py    # Cache management helpers
│   │   ├── network.py        # Citation network tools
│   │   ├── research.py       # Research workflow helpers
│   │   ├── search.py         # Semantic search tools
│   │   ├── treatment.py      # Treatment analysis tools
│   │   └── verification.py   # Quote verification tools
│   └── analysis/             # Core analysis modules
│       ├── citation_network.py       # Network graph construction
│       ├── mermaid_generator.py      # Mermaid diagram generation
│       ├── quote_matcher.py          # Quote matching with fuzzy search
│       ├── semantic_search.py        # Vector-based similarity search
│       └── treatment_classifier.py   # Signal detection & classification
├── tests/                   # Pytest suites (285+ test functions)
│   ├── test_cache.py
│   ├── test_mcp_client.py
│   ├── test_network_tools.py
│   ├── test_search_tool.py
│   ├── test_semantic_search.py
│   └── ...
├── pyproject.toml           # Python package configuration
├── .env.example             # Environment template
├── .gitignore
└── README.md
```

## 🎓 Use Cases

### Legal Academics
- Verify case validity before citing in papers
- Check quote accuracy for academic integrity
- Generate citation networks for doctrinal analysis
- Create visualizations for presentations

### Legal Practitioners
- Shepardize cases for free
- Validate citations in briefs
- Build case authority networks
- Track precedent evolution

### Law Students
- Understand precedent relationships
- Verify study notes and outlines
- Create visual study aids
- Check case validity for assignments

## 🗺️ Roadmap

### ✅ Completed Features

- [x] Project scaffolding and setup
- [x] CourtListener API integration with authentication & resilience
- [x] Treatment analysis with signal detection (12 negative, 11 positive patterns)
- [x] Two-pass analysis with smart full-text fetching strategy
- [x] Quote verification with fuzzy matching and pinpoint citations
- [x] Citation network construction with recursive depth control
- [x] Mermaid diagram generation (flowchart, graph, timeline)
- [x] Comprehensive markdown reports with statistics
- [x] Repository hygiene and configuration centralization
- [x] Structured logging with correlation IDs and request tracking
- [x] Multi-layer caching with configurable TTLs
- [x] Retry/backoff policies with partial result support
- [x] Advanced network analytics (PageRank, centrality, community detection)
- [x] Export formats (GraphML, JSON)
- [x] Research orchestration tools (`run_research_pipeline`, `issue_map`)
- [x] Semantic search with vector embeddings and re-ranking
- [x] Cache management tools
- [x] Comprehensive test coverage (285+ tests)

### 🎯 High-priority improvements

1) **Semantic Search Enhancements**
- [ ] Multi-model ensemble for embedding quality
- [ ] Hybrid search (keyword + semantic ranking)
- [ ] Custom embedding fine-tuning on legal corpora
- [ ] Similarity threshold optimization

2) **Network Visualization Improvements**
- [ ] Interactive web-based visualizations
- [ ] Real-time network updates
- [ ] Advanced filtering UI (by court, date range, treatment type)
- [ ] Node sizing by authority/influence

3) **User Experience**
- [ ] CLI interface for common workflows
- [ ] Example scripts for each use case
- [ ] Jupyter notebook demonstrations
- [ ] Performance benchmarking suite

4) **Expanded Research Capabilities**
- [ ] Batch processing pipelines for bulk research
- [ ] Issue mapping with cross-citation analysis
- [ ] Precedent evolution timelines
- [ ] Comparative case analysis

5) **Integration & Export**
- [ ] Obsidian plugin development
- [ ] Export to citation management tools (Zotero, Mendeley)
- [ ] Document upload and OCR support
- [ ] Multi-format export (PDF, Word, LaTeX)

### 📈 Longer-horizon items

- [ ] Machine learning treatment classification
- [ ] Generative helpers (memo and outline builders)
- [ ] Multi-jurisdiction support (state courts, international)
- [ ] Batch ML model training on case outcomes
- [ ] Predictive analytics for case law evolution
- [ ] Natural language policy analysis
- [ ] Advanced visualization (3D networks, AR support)

## 🤝 Contributing

This is a research project built for legal academic work. Contributions are welcome!

**Areas for contribution:**
- Additional treatment signal patterns
- Improved fuzzy matching algorithms
- New visualization types
- Documentation and examples
- Test coverage
- Performance optimizations

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **CourtListener/Free Law Project** - For providing free access to legal data
- **FastMCP** - For the MCP framework
- **Anthropic** - For the Model Context Protocol specification

## 📚 Citation

If you use this tool in academic work, please cite:

```bibtex
@software{legal_research_assistant_mcp,
  title = {Legal Research Assistant MCP},
  author = {Mike Sapp},
  year = {2025},
  description = {Advanced legal research MCP with treatment analysis,
                 citation networks, and quote verification},
  url = {https://github.com/mightymikesapp/legal-research-assistant-mcp}
}
```

## 📧 Contact

For questions, issues, or collaboration opportunities, please open an issue on GitHub.

---

**Built with ❤️ for the legal research community**
