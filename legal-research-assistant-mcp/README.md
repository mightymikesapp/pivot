# Legal Research Assistant MCP

An advanced Model Context Protocol (MCP) server providing intelligent legal research capabilities built on top of CourtListener.
This server adds treatment analysis, citation networks, quote verification, and advanced visualizations to enhance legal research workflows in Obsidian and other MCP-compatible environments.

## 🎯 Features

### ✅ Treatment Analysis (Shepardizing Alternative)
**Determine if a case is still good law** - Our treatment analyzer examines citing cases and provides confidence-scored validity assessments.

- **Automated case validity checking** - Analyzes treatment signals from citing cases
- **12 negative signal patterns** (overruled, abrogated, reversed, etc.)
- **11 positive signal patterns** (followed, affirmed, adopted, etc.)
- **Two-pass analysis** - Smart full-text fetching for better accuracy
- **Confidence scoring** (0-1 scale) with detailed warnings
- **Context extraction** showing relevant excerpts

### ✅ Quote Verification
**Maintain academic integrity** - Verify that quotes accurately appear in cited cases.

- **Exact match finding** - Locates precise quotes in case text
- **Fuzzy matching** (85% threshold) - Finds similar passages with minor variations
- **Context extraction** (200+ chars before/after)
- **Batch verification** - Check multiple quotes at once
- **HTML text normalization** - Handles various text formats
- **Difference detection** - Shows specific discrepancies
- **Pinpoint citation validation**

### ✅ Citation Network Visualization
**Visualize precedent relationships** - Build and analyze citation graphs with beautiful Mermaid diagrams.

- **Network construction** - Build citation graphs from CourtListener data
- **Multiple diagram types:**
  - **Flowcharts** - Hierarchical citation networks
  - **Graphs** - Simplified network views
  - **Timelines** - Citations over time
- **Treatment-based coloring** - Visual distinction of positive/negative signals
- **Influence scoring** - Identify most important cases
- **Statistical analysis** - Temporal and court distribution
- **Obsidian-ready** - Copy-paste Mermaid syntax directly into notes
- **Comprehensive reports** - Markdown-formatted with diagrams and statistics

### 🚧 Semantic Search (Planned)
- Find cases by conceptual similarity
- Cross-jurisdictional pattern matching
- Analogous reasoning detection

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
│  ✓ Mermaid Visualizations              │
│  ○ Semantic Search (planned)           │
└──────────┬──────────────────────────────┘
           │ calls ↓
┌──────────▼──────────────────────────────┐
│  CourtListener API (Free Law Project)   │
│  (Data Access Layer)                    │
└─────────────────────────────────────────┘
```

## 🚀 Installation

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) for dependency management
- CourtListener API key (free at courtlistener.com)

### Setup

```bash
# Navigate to project directory
cd /Users/mikesapp/Desktop/legal-research-assistant-mcp

# Install dependencies
uv sync

# Copy environment configuration
cp .env.example .env

# Add your CourtListener API key to .env
echo "COURT_LISTENER_API_KEY=your_key_here" >> .env
```

### Configuration

Edit `.env` with your settings:

```bash
# Required
COURT_LISTENER_API_KEY=your_key_here

# Optional
LOG_LEVEL=INFO
DEBUG=false

# Treatment Analysis Configuration
MAX_CITING_CASES=100
FETCH_FULL_TEXT_STRATEGY=smart  # Options: smart, always, negative_only, never
MAX_FULL_TEXT_FETCHES=10

# Network Configuration
NETWORK_MAX_DEPTH=2
NETWORK_MAX_NODES=100
```

### Running the Server

```bash
# Run directly
uv run python -m app.server

# Or use the MCP CLI (if integrated with Claude Desktop)
# The server will be available as "Legal Research Assistant MCP"
```

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

## 🧪 Testing

Run the test scripts to verify functionality:

```bash
# Test case validity checking
uv run python test_validity_check.py

# Test quote verification
uv run python test_quote_verification.py

# Test visualization
uv run python test_visualization.py

# Test specific case lookup
uv run python test_case_lookup.py

# Inspect opinion text
uv run python test_roe_text.py
```

## 📁 Project Structure

```
legal-research-assistant-mcp/
├── app/
│   ├── __init__.py
│   ├── __main__.py           # Entry point
│   ├── server.py             # Main MCP server
│   ├── config.py             # Configuration with Pydantic
│   ├── mcp_client.py         # CourtListener API client
│   ├── tools/                # MCP tool implementations
│   │   ├── treatment.py      # Treatment analysis tools
│   │   ├── verification.py   # Quote verification tools
│   │   └── network.py        # Citation network tools
│   └── analysis/             # Core analysis modules
│       ├── treatment_classifier.py   # Signal detection & classification
│       ├── quote_matcher.py          # Quote matching with fuzzy search
│       ├── citation_network.py       # Network graph construction
│       └── mermaid_generator.py      # Mermaid diagram generation
├── tests/
│   ├── test_validity_check.py
│   ├── test_quote_verification.py
│   ├── test_visualization.py
│   ├── test_case_lookup.py
│   └── test_roe_text.py
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

- [x] Project scaffolding and setup
- [x] CourtListener API integration
- [x] Treatment analysis with signal detection
- [x] Two-pass analysis with smart full-text fetching
- [x] Quote verification with fuzzy matching
- [x] Citation network construction
- [x] Mermaid diagram generation
- [x] Comprehensive markdown reports

### 🎯 High-impact next tasks

1) **Reliability and hygiene**
- [ ] Tighten repository hygiene (.gitignore coverage, clearer defaults)
- [ ] Centralize configuration with .env/env vars for CourtListener, timeouts, retries, and cache controls
- [ ] Implement structured logging with correlation/request metadata and tool context

2) **Quality gates and repeatability**
- [ ] Add CI pipeline running `pytest` (fast unit suite), `ruff`, `mypy`, and coverage thresholds
- [ ] Split tests into fast unit checks vs. flagged integration suites for external calls

3) **Resilience for CourtListener and other external calls**
- [ ] Add caching with sensible TTLs for case metadata and query responses
- [ ] Wrap external calls with timeouts and retry/backoff policies; surface partial results with warnings

4) **User-facing research helpers**
- [ ] Build end-to-end research workflow helpers (e.g., `run_research_pipeline`, `issue_map`)
- [ ] Extend citation verification with grounding checks and better error surfacing

5) **Authority-aware analytics and visualization**
- [ ] Add weighted/clustered citation graph analytics (authority weighting, clustering, PageRank/centrality)
- [ ] Enhance visualizations and export formats (court/treatment coloring, node sizing, GraphML/JSON exports)

### 📈 Longer-horizon items

- [ ] Document uploads for user-provided sources
- [ ] Generative helpers (memo and outline builders)
- [ ] Semantic similarity search across corpora
- [ ] Obsidian plugin integration
- [ ] Batch processing pipelines
- [ ] Machine learning treatment classification
- [ ] Multi-jurisdiction support
- [ ] Export to citation management tools

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
  url = {https://github.com/mightymikesapp/pivot/legal-research-assistant-mcp}
}
```

## 📧 Contact

For questions, issues, or collaboration opportunities, please open an issue on GitHub.

---

**Built with ❤️ for the legal research community**
