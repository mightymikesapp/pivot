# Legal Research Assistant MCP - Tool Reference Guide

**Version**: 0.1.0
**Total Tools**: 18
**Status**: ✅ All tools operational

---

## Quick Access: Tool Categories

1. [Server Status Tools](#server-status-tools) (2 tools)
2. [Treatment Analysis Tools](#treatment-analysis-tools) (2 tools)
3. [Quote Verification Tools](#quote-verification-tools) (2 tools)
4. [Citation Network Tools](#citation-network-tools) (5 tools)
5. [Semantic Search Tools](#semantic-search-tools) (3 tools)
6. [Research Pipeline Tools](#research-pipeline-tools) (2 tools)
7. [Cache Management Tools](#cache-management-tools) (2 tools)

---

## Server Status Tools

### `health_check()`

**Purpose**: Check the health status of the Legal Research Assistant MCP server

**Returns**:
- Server status
- Version number
- Available capabilities
- Configuration info
- Python version

**Example Use**:
```python
health = await health_check()
print(health["status"])  # "healthy"
```

**When to Use**: Verify server is operational before running complex operations

---

### `status()`

**Purpose**: Get simple server status message

**Returns**:
- Operational status
- Timestamp

**Example Use**:
```python
status = await status()
print(status["status"])  # "operational"
```

**When to Use**: Quick ping to confirm server is running

---

## Treatment Analysis Tools

### `check_case_validity(citation: str) → dict`

**Purpose**: Analyze whether a case is still good law by examining citing cases and treatment signals

**Parameters**:
- `citation` (str): Case citation (e.g., "410 U.S. 113")

**Returns**:
- `valid` (bool): Whether case is still good law
- `confidence` (float): Confidence score (0-1)
- `overall_treatment` (str): Summary treatment classification
- `citing_cases_count` (int): Number of citing cases analyzed
- `treatment_summary` (dict): Breakdown of treatment types
- `warnings` (list): Any concerning patterns
- `recommendation` (str): Usage recommendation

**Example Use**:
```python
result = await check_case_validity("410 U.S. 113")
if not result["valid"]:
    print(f"⚠️ Warning: {result['warnings']}")
```

**When to Use**:
- Before citing a case in legal brief
- Verifying precedents are still good law
- Checking if case has been overruled or questioned

**Real-World Example**: We used this to verify Roe v. Wade's treatment status

---

### `get_citing_cases(citation: str, limit: int = 100) → dict`

**Purpose**: Retrieve all cases that cite a given citation with treatment classification

**Parameters**:
- `citation` (str): Case citation
- `limit` (int): Maximum number of citing cases (default: 100)

**Returns**:
- `citing_cases` (list): List of cases citing the target
- `citing_cases_count` (int): Total count
- `treatment_breakdown` (dict): Distribution of treatment types

**Example Use**:
```python
result = await get_citing_cases("995 F.3d 1085", limit=50)
print(f"Found {result['citing_cases_count']} citing cases")
```

**When to Use**:
- Building citation networks
- Understanding how case has been treated over time
- Finding related precedents

**Real-World Example**: We found 20+ cases citing *Lemmon v. Snap*

---

## Quote Verification Tools

### `verify_quote(quote: str, citation: str, pinpoint: str = None) → dict`

**Purpose**: Verify that a quote accurately appears in the cited case

**Parameters**:
- `quote` (str): The quoted text to verify
- `citation` (str): Case citation
- `pinpoint` (str, optional): Page or section reference

**Returns**:
- `found` (bool): Whether quote was found
- `exact_match` (bool): Whether match was exact
- `similarity` (float): Similarity score (0-1)
- `matches_found` (int): Number of matches
- `best_match` (dict): Location and context
- `recommendation` (str): Verification assessment

**Example Use**:
```python
result = await verify_quote(
    quote="the right of privacy",
    citation="410 U.S. 113"
)
print(f"Exact match: {result['exact_match']}")
```

**When to Use**:
- Verifying quotes before submission
- Academic integrity checks
- Ensuring accurate citations

**Real-World Example**: This is what you asked me to use to verify quotes in "The Rage Machine"

---

### `batch_verify_quotes(quotes: list[dict]) → dict`

**Purpose**: Verify multiple quotes in a single batch operation

**Parameters**:
- `quotes` (list): List of dicts with `quote` and `citation` keys

**Returns**:
- `results` (list): Verification result for each quote
- `summary` (dict): Aggregate statistics
- `verified_count` (int): Number of verified quotes
- `failed_count` (int): Number of unverified quotes

**Example Use**:
```python
quotes = [
    {"quote": "text 1", "citation": "410 U.S. 113"},
    {"quote": "text 2", "citation": "995 F.3d 1085"}
]
result = await batch_verify_quotes(quotes)
```

**When to Use**:
- Verifying all quotes in a document at once
- Large-scale citation audits
- Pre-submission compliance checks

**Efficiency**: Much faster than verifying quotes one-by-one

---

## Citation Network Tools

### `build_citation_network(citation: str, max_depth: int = 2, max_nodes: int = 100) → dict`

**Purpose**: Construct a citation network graph showing precedent relationships

**Parameters**:
- `citation` (str): Root case citation
- `max_depth` (int): Recursion depth (default: 2)
- `max_nodes` (int): Maximum network size (default: 100)

**Returns**:
- `root_citation` (str): Starting case
- `nodes` (list): All cases in network
- `edges` (list): Citation relationships
- `statistics` (dict): Network metrics

**Example Use**:
```python
network = await build_citation_network("410 U.S. 113", max_nodes=50)
print(f"Network contains {len(network['nodes'])} cases")
```

**When to Use**:
- Understanding precedent landscape
- Finding related cases
- Mapping doctrinal evolution

**Real-World Example**: We built a citation network for Roe v. Wade with 15 nodes

---

### `visualize_citation_network(citation: str, diagram_type: str = "flowchart") → dict`

**Purpose**: Generate a Mermaid diagram visualization of a citation network

**Parameters**:
- `citation` (str): Root case citation
- `diagram_type` (str): Type of diagram ("flowchart", "graph", "timeline", "all")
- `direction` (str): Flow direction ("TB", "LR", "RL", "BT")
- `max_nodes` (int): Maximum nodes to include
- `color_by_treatment` (bool): Color nodes by treatment type
- `show_legend` (bool): Include legend

**Returns**:
- `mermaid_syntax` (str): Complete Mermaid diagram code
- `case_name` (str): Root case name
- `node_count` (int): Number of nodes
- `edge_count` (int): Number of edges
- `usage_instructions` (str): How to use the diagram

**Example Use**:
```python
viz = await visualize_citation_network(
    citation="410 U.S. 113",
    diagram_type="flowchart",
    max_nodes=15
)
# Copy viz["mermaid_syntax"] and paste into Obsidian
```

**When to Use**:
- Creating visual aids for legal writing
- Court presentations
- Understanding precedent relationships visually

**Real-World Example**: We created the Roe v. Wade visualization you saw earlier

**Output Format**: Ready to paste into Obsidian between ` ```mermaid ` tags

---

### `generate_citation_report(citation: str, treatment_focus: list[str] = None) → dict`

**Purpose**: Generate a comprehensive markdown report with visualizations and statistics

**Parameters**:
- `citation` (str): Root case citation
- `treatment_focus` (list): Treatment types to emphasize
- `include_diagram` (bool): Include Mermaid visualization
- `include_statistics` (bool): Include network analytics
- `max_nodes` (int): Maximum network size

**Returns**:
- `markdown_report` (str): Complete markdown document
- `statistics` (dict): Network statistics
- `mermaid_diagrams` (dict): Generated visualizations

**Example Use**:
```python
report = await generate_citation_report(
    citation="410 U.S. 113",
    include_diagram=True,
    treatment_focus=["overruled", "questioned"]
)
# Save report["markdown_report"] to .md file
```

**When to Use**:
- Creating comprehensive case analysis documents
- Research memoranda
- Law review footnote preparation

**Output**: Complete markdown document ready for Obsidian

---

### `get_network_statistics(citation: str) → dict`

**Purpose**: Provide detailed statistical analysis of a citation network

**Parameters**:
- `citation` (str): Root case citation

**Returns**:
- `influence_ranking` (list): Most influential cases (PageRank)
- `communities` (list): Case clusters
- `temporal_distribution` (dict): Citations over time
- `court_distribution` (dict): Distribution by court level
- `treatment_trends` (dict): Treatment patterns

**Example Use**:
```python
stats = await get_network_statistics("410 U.S. 113")
print(f"Most influential: {stats['influence_ranking'][0]}")
```

**When to Use**:
- Understanding citation impact
- Identifying key precedents
- Quantitative legal analysis

---

### `filter_citation_network(citation: str, treatments: list[str], min_confidence: float) → dict`

**Purpose**: Build a filtered network showing only specific treatment types

**Parameters**:
- `citation` (str): Root case citation
- `treatments` (list): Treatment types to include (e.g., ["overruled", "questioned"])
- `min_confidence` (float): Minimum confidence threshold (0-1)

**Returns**:
- Filtered network with only specified relationships

**Example Use**:
```python
# Show only negative treatment
negative_network = await filter_citation_network(
    citation="410 U.S. 113",
    treatments=["overruled", "questioned", "limited"],
    min_confidence=0.7
)
```

**When to Use**:
- Focusing on adverse precedent
- Identifying problematic citations
- Targeted precedent analysis

---

## Semantic Search Tools

### `semantic_search(query: str, jurisdiction: str = None, limit: int = 20) → dict`

**Purpose**: Find cases by conceptual similarity using vector embeddings

**Parameters**:
- `query` (str): Natural language search query
- `jurisdiction` (str, optional): Filter by jurisdiction
- `limit` (int): Maximum results (default: 20)
- `rerank` (bool): Use semantic re-ranking

**Returns**:
- `results` (list): Matching cases with similarity scores
- `query` (str): Original query
- `vector_store_stats` (dict): Search statistics

**Example Use**:
```python
results = await semantic_search(
    query="liability for failure to warn about product defects",
    jurisdiction="Federal",
    limit=15
)
```

**When to Use**:
- Finding cases when you don't know specific citations
- Conceptual legal research
- Discovering related precedents

**How It Works**: Uses sentence transformers to find conceptually similar cases, not just keyword matches

---

### `get_library_stats() → dict`

**Purpose**: Get statistics about the local semantic search library

**Returns**:
- `total_cases_indexed` (int): Cases in vector store
- `persistence_path` (str): Storage location
- `model_name` (str): Embedding model used
- `semantic_search_enabled` (bool): Whether feature is active

**Example Use**:
```python
stats = await get_library_stats()
print(f"Indexed cases: {stats['total_cases_indexed']}")
```

**When to Use**:
- Checking vector store size
- Verifying semantic search is working
- Monitoring storage usage

---

### `purge_memory() → dict`

**Purpose**: Clear the local vector store and reset embeddings cache

**Returns**:
- Confirmation of purge operation

**Example Use**:
```python
result = await purge_memory()
```

**When to Use**:
- Clearing old embeddings
- Resetting after corrupted data
- Freeing disk space

**⚠️ Warning**: This deletes all cached embeddings - use with caution

---

## Research Pipeline Tools

### `run_research_pipeline(primary_citation: str, quotes_to_verify: list = None) → dict`

**Purpose**: Execute a comprehensive research workflow combining multiple tools

**Parameters**:
- `primary_citation` (str): Main case to analyze
- `quotes_to_verify` (list): Quotes to check
- `max_network_depth` (int): Citation network depth
- `max_network_nodes` (int): Network size limit
- `semantic_search_enabled` (bool): Use semantic search

**Returns**:
- `treatment_analysis` (dict): Case validity assessment
- `quote_verification` (dict): Quote verification results
- `citation_network` (dict): Network analysis
- `semantic_results` (dict, optional): Related cases

**Example Use**:
```python
pipeline = await run_research_pipeline(
    primary_citation="410 U.S. 113",
    quotes_to_verify=["the right of privacy"],
    max_network_nodes=50
)
```

**When to Use**:
- Comprehensive case analysis
- Pre-submission verification
- One-stop research operation

**Efficiency**: Runs all analyses in parallel where possible

---

### `issue_map(citations: list[str], legal_questions: list[str]) → dict`

**Purpose**: Create an issue map linking key questions to cited authorities

**Parameters**:
- `citations` (list): List of case citations
- `legal_questions` (list): Legal issues to map

**Returns**:
- Mapping of issues to supporting cases

**Example Use**:
```python
issue_map = await issue_map(
    citations=["410 U.S. 113", "995 F.3d 1085"],
    legal_questions=[
        "Does Section 230 cover algorithmic recommendations?",
        "Is cognitive integrity a protected interest?"
    ]
)
```

**When to Use**:
- Organizing research by issue
- Brief preparation
- Case outline development

---

## Cache Management Tools

### `cache_stats() → dict`

**Purpose**: Report cache hit rates, miss rates, and storage size

**Returns**:
- `metadata_hits` (int): Metadata cache hits
- `metadata_misses` (int): Metadata cache misses
- `text_hits` (int): Full-text cache hits
- `search_hits` (int): Search cache hits
- `total_size_mb` (float): Cache size in megabytes
- `hit_rate` (float): Overall cache efficiency

**Example Use**:
```python
stats = await cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.1%}")
print(f"Cache size: {stats['total_size_mb']:.1f} MB")
```

**When to Use**:
- Monitoring performance
- Diagnosing slow queries
- Managing storage

---

### `cache_clear(cache_type: str = "all") → dict`

**Purpose**: Clear cache by type

**Parameters**:
- `cache_type` (str): Type to clear ("metadata", "text", "search", "all")

**Returns**:
- Confirmation and statistics

**Example Use**:
```python
result = await cache_clear("search")  # Clear only search cache
```

**When to Use**:
- Freeing disk space
- Forcing fresh data fetches
- After configuration changes

**Options**:
- `"metadata"`: Clear case metadata cache
- `"text"`: Clear full-text cache
- `"search"`: Clear search results cache
- `"all"`: Clear everything

---

## Common Workflows

### Workflow 1: Full Citation Verification

```python
# 1. Check if case is still good law
validity = await check_case_validity("410 U.S. 113")

# 2. Verify quotes from the case
quotes_result = await batch_verify_quotes([
    {"quote": "text1", "citation": "410 U.S. 113"},
    {"quote": "text2", "citation": "410 U.S. 113"}
])

# 3. Build citation network
network = await build_citation_network("410 U.S. 113")

# 4. Generate visualization
viz = await visualize_citation_network("410 U.S. 113")
```

---

### Workflow 2: Research a Legal Topic

```python
# 1. Semantic search for relevant cases
results = await semantic_search(
    query="algorithmic manipulation behavioral conditioning",
    limit=20
)

# 2. For each promising case, check treatment
for case in results['results']:
    validity = await check_case_validity(case['citation'])
    if validity['valid']:
        print(f"Good case to cite: {case['case_name']}")

# 3. Build network from best case
network = await build_citation_network(best_citation)
```

---

### Workflow 3: Quick Case Analysis

```python
# Use the research pipeline for one-stop analysis
analysis = await run_research_pipeline(
    primary_citation="410 U.S. 113",
    quotes_to_verify=["quote1", "quote2"],
    max_network_nodes=30
)

# Get everything in one call:
# - Treatment analysis
# - Quote verification
# - Citation network
# - Statistics
```

---

## Tips for Efficient Use

### Performance Tips:

1. **Use caching**: Don't clear cache unless necessary - it makes subsequent queries much faster
2. **Batch operations**: Use `batch_verify_quotes` instead of multiple `verify_quote` calls
3. **Limit network size**: Start with smaller `max_nodes` (20-30) before expanding
4. **Use research pipeline**: When you need multiple analyses, the pipeline runs them in parallel

### Best Practices:

1. **Always check cache stats** before large operations to see if data is already cached
2. **Start broad, then narrow**: Use semantic search to find cases, then get_citing_cases to expand
3. **Verify recent cases**: Always check treatment on cases older than 5-10 years
4. **Save reports**: Use `generate_citation_report` to create permanent records

### Troubleshooting:

- **Slow queries?** → Check `cache_stats()` - low hit rate means clearing cache might help
- **No results?** → Try broader search terms or different jurisdictions
- **Quote not found?** → Try smaller snippets or check for OCR errors in original
- **Network too large?** → Reduce `max_nodes` or `max_depth`

---

## Configuration

The MCP server uses environment variables from `.env`:

**Key Settings**:
- `COURT_LISTENER_API_KEY`: Your API key (required)
- `CACHE_ENABLED`: Enable/disable caching (default: true)
- `SEMANTIC_SEARCH_ENABLED`: Enable vector search (default: true)
- `MAX_CITING_CASES`: Limit for citing case queries (default: 100)
- `NETWORK_MAX_DEPTH`: Default network depth (default: 2)

**Full configuration**: See `.env.example` in the project directory

---

## Quick Reference: When to Use Which Tool

| Task | Tool | Priority |
|------|------|----------|
| Check if case is still good law | `check_case_validity` | ⭐⭐⭐ |
| Verify quote accuracy | `verify_quote` or `batch_verify_quotes` | ⭐⭐⭐ |
| Find related cases | `get_citing_cases` or `semantic_search` | ⭐⭐⭐ |
| Create visual citation network | `visualize_citation_network` | ⭐⭐ |
| Comprehensive case analysis | `run_research_pipeline` | ⭐⭐⭐ |
| Generate research report | `generate_citation_report` | ⭐⭐ |
| Find cases on a topic | `semantic_search` | ⭐⭐⭐ |
| Check server status | `health_check` | ⭐ |
| Manage disk space | `cache_clear`, `purge_memory` | ⭐ |

---

## Real-World Examples from Today's Session

### What We Actually Did:

1. ✅ **Citation Verification** - Verified 14 cases in "The Rage Machine" article
2. ✅ **Treatment Analysis** - Checked *Lemmon v. Snap* and *Anderson v. TikTok* for negative treatment
3. ✅ **Citation Networks** - Built network from *Lemmon* showing 20+ citing cases
4. ✅ **Visualization** - Created Roe v. Wade citation network with 15 nodes
5. ✅ **Semantic Search** - Found 16 additional supporting cases for the article

### Results:
- All 14 citations verified as accurate ✅
- No negative treatment found on key cases ✅
- Found circuit split (*M.P. v. Meta* vs. *Anderson*) ✅
- Discovered 16 new 2024-2025 cases to strengthen article ✅

---

## Support & Documentation

- **GitHub**: https://github.com/mightymikesapp/legal-research-assistant-mcp
- **Full README**: `/Users/mikesapp/Desktop/projects/legal-research-assistant-mcp/README.md`
- **Configuration**: `.env.example` for all settings
- **Issues**: Report bugs on GitHub Issues

---

## Version History

- **v0.1.0** (Current): Initial release with 18 tools
  - Treatment analysis (Shepardizing alternative)
  - Citation networks with Mermaid visualization
  - Quote verification
  - Semantic search
  - Research pipelines

---

**Last Updated**: December 3, 2025
**Status**: ✅ All 18 tools operational and tested

*This reference guide was generated by the Legal Research Assistant MCP - eat the dog food! 🐕*
