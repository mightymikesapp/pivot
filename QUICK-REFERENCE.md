# Legal Research Assistant MCP - Quick Reference

**Total Tools**: 18 | **Status**: ✅ Operational

---

## 🎯 Most Used Tools (Top 6)

| Tool | What It Does | Example |
|------|--------------|---------|
| `check_case_validity(citation)` | Is case still good law? | `check_case_validity("410 U.S. 113")` |
| `verify_quote(quote, citation)` | Is quote accurate? | `verify_quote("text", "410 U.S. 113")` |
| `get_citing_cases(citation)` | Who cites this case? | `get_citing_cases("995 F.3d 1085")` |
| `semantic_search(query)` | Find cases by concept | `semantic_search("algorithmic manipulation")` |
| `visualize_citation_network(citation)` | Create visual network | `visualize_citation_network("410 U.S. 113")` |
| `run_research_pipeline(citation)` | Do everything at once | `run_research_pipeline("410 U.S. 113")` |

---

## 📋 All Tools by Category

### ✅ Server Status (2)
- `health_check()` - Check server health
- `status()` - Quick server ping

### ⚖️ Treatment Analysis (2)
- `check_case_validity(citation)` - Shepardizing alternative
- `get_citing_cases(citation, limit)` - Get all citing cases

### 📝 Quote Verification (2)
- `verify_quote(quote, citation, pinpoint)` - Single quote
- `batch_verify_quotes(quotes)` - Multiple quotes

### 🕸️ Citation Networks (5)
- `build_citation_network(citation, max_depth, max_nodes)` - Build network
- `visualize_citation_network(citation, diagram_type)` - Mermaid diagram
- `generate_citation_report(citation)` - Full markdown report
- `get_network_statistics(citation)` - Network analytics
- `filter_citation_network(citation, treatments)` - Filtered network

### 🔍 Semantic Search (3)
- `semantic_search(query, jurisdiction, limit)` - Vector search
- `get_library_stats()` - Vector store info
- `purge_memory()` - Clear vector store

### 🔬 Research Pipelines (2)
- `run_research_pipeline(citation, quotes)` - Comprehensive analysis
- `issue_map(citations, questions)` - Map issues to cases

### 💾 Cache Management (2)
- `cache_stats()` - Cache performance
- `cache_clear(cache_type)` - Clear cache

---

## 🚀 Common Workflows

### Verify a Case for Citation
```python
# 1. Check if still good law
validity = await check_case_validity("410 U.S. 113")

# 2. Get citing cases
citing = await get_citing_cases("410 U.S. 113")

# 3. Visualize network
viz = await visualize_citation_network("410 U.S. 113")
```

### Verify Document Citations
```python
# Batch verify all quotes
quotes = [
    {"quote": "text1", "citation": "410 U.S. 113"},
    {"quote": "text2", "citation": "995 F.3d 1085"}
]
results = await batch_verify_quotes(quotes)
```

### Research a Legal Topic
```python
# Find relevant cases
results = await semantic_search("product liability algorithms", limit=20)

# Check each case
for case in results['results']:
    validity = await check_case_validity(case['citation'])
```

### Full Case Analysis (One Command)
```python
# Does everything: treatment, quotes, network, search
analysis = await run_research_pipeline(
    primary_citation="410 U.S. 113",
    quotes_to_verify=["quote1", "quote2"]
)
```

---

## 💡 Quick Tips

- ✅ **Always check treatment** on cases older than 5 years
- ✅ **Use batch operations** for multiple quotes (much faster)
- ✅ **Start with pipeline** for comprehensive analysis
- ✅ **Check cache stats** before clearing cache
- ✅ **Save visualizations** - paste Mermaid syntax into Obsidian

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Slow queries | Run `cache_stats()` - might need `cache_clear()` |
| No search results | Try broader terms or remove jurisdiction filter |
| Quote not found | Try smaller snippets or check for OCR errors |
| Network too large | Reduce `max_nodes` parameter |

---

## 📍 File Locations

- **Full Guide**: `/Users/mikesapp/Desktop/projects/legal-research-assistant-mcp/TOOL-REFERENCE-GUIDE.md`
- **Configuration**: `/Users/mikesapp/Desktop/projects/legal-research-assistant-mcp/.env`
- **README**: `/Users/mikesapp/Desktop/projects/legal-research-assistant-mcp/README.md`

---

## ⚙️ MCP Server Info

**Command**: `claude mcp list`
**Name**: `legal-research-assistant-mcp`
**Status**: ✅ Connected
**Tools**: 18 operational

---

**Last Updated**: December 3, 2025
