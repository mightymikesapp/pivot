"""MCP tools for citation network analysis."""

import logging
from typing import Any

from fastmcp import FastMCP

from ..analysis.citation_network import CitationNetworkBuilder
from ..analysis.mermaid_generator import MermaidGenerator
from ..analysis.treatment_classifier import TreatmentClassifier
from ..config import get_settings
from ..mcp_client import get_client

logger = logging.getLogger(__name__)

network_server = FastMCP[Any]("Citation Network")


@network_server.tool()
async def build_citation_network(
    citation: str,
    max_depth: int = 2,
    max_nodes: int = 100,
    include_treatments: bool = True,
) -> dict[str, Any]:
    """Build a citation network for a given case.

    Creates a graph showing how cases cite each other, starting from the target case.
    Useful for understanding precedent flow and case influence.

    Args:
        citation: The citation to build a network around (e.g., "410 U.S. 113")
        max_depth: Maximum depth to traverse (1 = direct citations only, 2 = citations of citations)
        max_nodes: Maximum number of nodes to include in the network
        include_treatments: Whether to include treatment analysis for edges

    Returns:
        Dictionary containing:
        - root_citation: The citation at the center of the network
        - root_case_name: Name of the root case
        - nodes: List of case nodes in the network
        - edges: List of citation edges with treatment info
        - statistics: Network statistics and metrics
    """
    settings = get_settings()
    client = get_client()

    logger.info(f"Building citation network for {citation}")

    # Look up the root case
    root_case = await client.lookup_citation(citation)

    if "error" in root_case:
        return {
            "error": f"Could not find case for citation: {citation}",
            "citation": citation,
        }

    # Get citing cases
    citing_cases = await client.find_citing_cases(citation, limit=max_nodes)

    if not citing_cases:
        return {
            "root_citation": citation,
            "root_case_name": root_case.get("caseName"),
            "nodes": [
                {
                    "citation": citation,
                    "case_name": root_case.get("caseName"),
                    "date_filed": root_case.get("dateFiled"),
                    "court": root_case.get("court"),
                }
            ],
            "edges": [],
            "statistics": {
                "total_nodes": 1,
                "total_edges": 0,
                "message": "No citing cases found",
            },
        }

    # Optionally include treatment analysis
    treatments = None
    if include_treatments:
        logger.info("Including treatment analysis in network")
        classifier = TreatmentClassifier()

        treatments = []
        for citing_case in citing_cases[:max_nodes]:
            treatment = classifier.classify_treatment(citing_case, citation)
            treatments.append(
                {
                    "citing_case": citing_case,
                    "treatment": treatment["treatment"],
                    "confidence": treatment["confidence"],
                    "excerpt": treatment["excerpt"],
                }
            )

    # Build the network
    builder = CitationNetworkBuilder(max_depth=max_depth, max_nodes=max_nodes)
    network = builder.build_network(root_case, citing_cases, treatments)

    # Get statistics
    statistics = builder.get_network_statistics(network)

    # Convert to JSON-serializable format
    return {
        "root_citation": network.root_citation,
        "root_case_name": root_case.get("caseName"),
        "nodes": [
            {
                "citation": node.citation,
                "case_name": node.case_name,
                "date_filed": node.date_filed,
                "court": node.court,
                "cluster_id": node.cluster_id,
                "opinion_ids": node.opinion_ids,
                "metadata": node.metadata,
            }
            for node in network.nodes.values()
        ],
        "edges": [
            {
                "from_citation": edge.from_citation,
                "to_citation": edge.to_citation,
                "depth": edge.depth,
                "treatment": edge.treatment,
                "confidence": edge.confidence,
                "excerpt": edge.excerpt[:200] if edge.excerpt else "",
            }
            for edge in network.edges
        ],
        "statistics": statistics,
    }


@network_server.tool()
async def filter_citation_network(
    citation: str,
    treatments: list[str] | None = None,
    min_confidence: float = 0.5,
    date_after: str | None = None,
    date_before: str | None = None,
    max_nodes: int = 100,
) -> dict[str, Any]:
    """Build a filtered citation network showing only specific relationships.

    Useful for focusing on particular types of treatment (e.g., only negative signals)
    or specific time periods.

    Args:
        citation: The citation to analyze
        treatments: List of treatments to include (e.g., ["overruled", "questioned", "criticized"])
        min_confidence: Minimum confidence score (0.0-1.0) for treatment classification
        date_after: Only include cases filed after this date (YYYY-MM-DD format)
        date_before: Only include cases filed before this date (YYYY-MM-DD format)
        max_nodes: Maximum number of nodes to include

    Returns:
        Filtered citation network with nodes and edges matching criteria
    """
    logger.info(f"Building filtered citation network for {citation}")

    # First build the full network
    full_network = await build_citation_network(
        citation=citation,
        max_depth=1,
        max_nodes=max_nodes,
        include_treatments=True,
    )

    if "error" in full_network:
        return full_network

    # Apply filters
    filtered_edges = []
    for edge in full_network["edges"]:
        # Filter by treatment
        if treatments and edge["treatment"] not in treatments:
            continue

        # Filter by confidence
        if edge["confidence"] < min_confidence:
            continue

        # Find the node for date filtering
        citing_node = None
        for node in full_network["nodes"]:
            if node["citation"] == edge["from_citation"]:
                citing_node = node
                break

        # Filter by date
        if citing_node and citing_node["date_filed"]:
            if date_after and citing_node["date_filed"] < date_after:
                continue
            if date_before and citing_node["date_filed"] > date_before:
                continue

        filtered_edges.append(edge)

    # Keep only nodes referenced in filtered edges
    referenced_citations = {full_network["root_citation"]}
    for edge in filtered_edges:
        referenced_citations.add(edge["from_citation"])
        referenced_citations.add(edge["to_citation"])

    filtered_nodes = [
        node for node in full_network["nodes"] if node["citation"] in referenced_citations
    ]

    # Recalculate statistics
    treatment_counts: dict[str, int] = {}
    for edge in filtered_edges:
        if edge["treatment"]:
            treatment_counts[edge["treatment"]] = treatment_counts.get(edge["treatment"], 0) + 1

    return {
        "root_citation": full_network["root_citation"],
        "root_case_name": full_network["root_case_name"],
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "statistics": {
            "total_nodes": len(filtered_nodes),
            "total_edges": len(filtered_edges),
            "treatment_distribution": treatment_counts,
            "filters_applied": {
                "treatments": treatments,
                "min_confidence": min_confidence,
                "date_after": date_after,
                "date_before": date_before,
            },
        },
    }


@network_server.tool()
async def get_network_statistics(citation: str, max_nodes: int = 100) -> dict[str, Any]:
    """Get statistical analysis of a citation network.

    Provides metrics about case influence, treatment distribution, and network structure.

    Args:
        citation: The citation to analyze
        max_nodes: Maximum number of nodes to include in analysis

    Returns:
        Dictionary containing:
        - citation_count: How many cases cite this case
        - treatment_distribution: Breakdown of how citing cases treat this case
        - temporal_distribution: Citations over time
        - court_distribution: Which courts cite this case most
        - influence_score: Composite score of case influence
    """
    logger.info(f"Getting network statistics for {citation}")

    # Build network with treatments
    network = await build_citation_network(
        citation=citation,
        max_depth=1,
        max_nodes=max_nodes,
        include_treatments=True,
    )

    if "error" in network:
        return network

    # Analyze temporal distribution
    temporal: dict[str, int] = {}
    court_dist: dict[str, int] = {}

    for node in network["nodes"]:
        if node["citation"] == network["root_citation"]:
            continue

        # Count by year
        if node["date_filed"]:
            year = node["date_filed"][:4]
            temporal[year] = temporal.get(year, 0) + 1

        # Count by court
        if node["court"]:
            court_dist[node["court"]] = court_dist.get(node["court"], 0) + 1

    # Calculate influence score
    # Based on: citation count, treatment diversity, temporal span
    citation_count = len(network["edges"])
    treatment_diversity = len(network["statistics"].get("treatment_distribution", {}))
    temporal_span = len(temporal)

    # Simple influence score (0-100)
    influence_score = min(
        100,
        (citation_count * 0.5) + (treatment_diversity * 10) + (temporal_span * 2),
    )

    return {
        "citation": citation,
        "case_name": network["root_case_name"],
        "citation_count": citation_count,
        "treatment_distribution": network["statistics"].get("treatment_distribution", {}),
        "temporal_distribution": temporal,
        "court_distribution": court_dist,
        "influence_score": round(influence_score, 2),
        "insights": {
            "most_active_year": max(temporal.items(), key=lambda x: x[1])[0]
            if temporal
            else None,
            "most_citing_court": max(court_dist.items(), key=lambda x: x[1])[0]
            if court_dist
            else None,
            "citation_trend": "increasing"
            if temporal and list(temporal.values())[-1] > list(temporal.values())[0]
            else "stable",
        },
    }


@network_server.tool()
async def visualize_citation_network(
    citation: str,
    diagram_type: str = "flowchart",
    direction: str = "TB",
    color_by_treatment: bool = True,
    max_nodes: int = 50,
) -> dict[str, Any]:
    """Generate a Mermaid diagram visualization of a citation network.

    Creates beautiful visualizations perfect for Obsidian notes and academic papers.
    Supports multiple diagram types including flowcharts, graphs, and timelines.

    Args:
        citation: The citation to visualize
        diagram_type: Type of diagram ("flowchart", "graph", "timeline", or "all")
        direction: Diagram direction - "TB" (top-bottom), "LR" (left-right), "BT", "RL"
        color_by_treatment: Whether to color-code by treatment type
        max_nodes: Maximum number of nodes to include

    Returns:
        Dictionary containing:
        - mermaid_syntax: The Mermaid diagram code (ready to paste in Obsidian)
        - summary_stats: Text summary of the network
        - node_count: Number of nodes in visualization
        - edge_count: Number of edges in visualization
    """
    logger.info(f"Generating Mermaid visualization for {citation}")

    # Build the citation network
    network = await build_citation_network(
        citation=citation,
        max_depth=1,
        max_nodes=max_nodes,
        include_treatments=True,
    )

    if "error" in network:
        return network

    # Generate Mermaid diagrams
    generator = MermaidGenerator()

    diagrams = {}

    if diagram_type == "flowchart" or diagram_type == "all":
        diagrams["flowchart"] = generator.generate_flowchart(
            network,
            direction=direction,
            include_dates=True,
            color_by_treatment=color_by_treatment,
        )

    if diagram_type == "graph" or diagram_type == "all":
        diagrams["graph"] = generator.generate_graph(
            network,
            direction=direction,
            show_treatments=True,
        )

    if diagram_type == "timeline" or diagram_type == "all":
        diagrams["timeline"] = generator.generate_timeline(network)

    # Generate summary
    summary = generator.generate_summary_stats(network)

    # Get the primary diagram
    primary_diagram = diagrams.get(diagram_type, diagrams.get("flowchart", ""))

    return {
        "citation": citation,
        "case_name": network["root_case_name"],
        "mermaid_syntax": primary_diagram,
        "all_diagrams": diagrams if diagram_type == "all" else None,
        "summary_stats": summary,
        "node_count": len(network["nodes"]),
        "edge_count": len(network["edges"]),
        "usage_instructions": (
            "To use in Obsidian:\n"
            "1. Copy the mermaid_syntax\n"
            "2. Paste in your note between ```mermaid and ``` tags\n"
            "3. The diagram will render automatically"
        ),
    }


@network_server.tool()
async def generate_citation_report(
    citation: str,
    include_diagram: bool = True,
    include_statistics: bool = True,
    treatment_focus: list[str] | None = None,
    max_nodes: int = 50,
) -> dict[str, Any]:
    """Generate a comprehensive citation analysis report.

    Creates a complete markdown report with visualizations, statistics, and analysis.
    Perfect for inclusion in legal research notes and academic papers.

    Args:
        citation: The citation to analyze
        include_diagram: Whether to include Mermaid diagram
        include_statistics: Whether to include detailed statistics
        treatment_focus: Optional list of treatments to highlight (e.g., ["overruled", "questioned"])
        max_nodes: Maximum number of cases to include

    Returns:
        Dictionary containing:
        - markdown_report: Complete markdown-formatted report
        - mermaid_diagram: Mermaid syntax (if include_diagram=True)
        - statistics: Detailed statistics (if include_statistics=True)
    """
    logger.info(f"Generating citation report for {citation}")

    # Build network
    network = await build_citation_network(
        citation=citation,
        max_depth=1,
        max_nodes=max_nodes,
        include_treatments=True,
    )

    if "error" in network:
        return network

    # Start building report
    report_lines = []

    # Title
    report_lines.append(f"# Citation Analysis: {network['root_case_name']}")
    report_lines.append(f"**Citation:** {network['root_citation']}")
    report_lines.append("")

    # Statistics section
    if include_statistics:
        stats = network["statistics"]
        report_lines.append("## Overview")
        report_lines.append(f"- **Total Citing Cases:** {stats['total_nodes'] - 1}")
        report_lines.append(f"- **Citation Edges:** {stats['total_edges']}")
        report_lines.append("")

        # Treatment distribution
        treatment_dist = stats.get("treatment_distribution", {})
        if treatment_dist:
            report_lines.append("## Treatment Analysis")

            for treatment, count in sorted(
                treatment_dist.items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / stats["total_edges"]) * 100 if stats["total_edges"] > 0 else 0
                report_lines.append(f"- **{treatment}:** {count} ({percentage:.1f}%)")

            report_lines.append("")

    # Diagram section
    mermaid_diagram = None
    if include_diagram:
        generator = MermaidGenerator()
        mermaid_diagram = generator.generate_flowchart(
            network,
            direction="TB",
            include_dates=True,
            color_by_treatment=True,
        )

        report_lines.append("## Citation Network Diagram")
        report_lines.append("")
        report_lines.append("```mermaid")
        report_lines.append(mermaid_diagram)
        report_lines.append("```")
        report_lines.append("")

    # Key cases section
    if treatment_focus:
        report_lines.append("## Key Cases")
        report_lines.append("")

        for edge in network["edges"]:
            if edge["treatment"] in treatment_focus:
                # Find the citing case node
                citing_case = None
                for node in network["nodes"]:
                    if node["citation"] == edge["from_citation"]:
                        citing_case = node
                        break

                if citing_case:
                    report_lines.append(f"### {citing_case['case_name']}")
                    report_lines.append(f"- **Citation:** {citing_case['citation']}")
                    if citing_case["date_filed"]:
                        report_lines.append(f"- **Date:** {citing_case['date_filed']}")
                    report_lines.append(
                        f"- **Treatment:** {edge['treatment']} (confidence: {edge['confidence']:.0%})"
                    )
                    if edge["excerpt"]:
                        report_lines.append(f"- **Excerpt:** {edge['excerpt'][:200]}...")
                    report_lines.append("")

    markdown_report = "\n".join(report_lines)

    return {
        "citation": citation,
        "case_name": network["root_case_name"],
        "markdown_report": markdown_report,
        "mermaid_diagram": mermaid_diagram,
        "statistics": network["statistics"] if include_statistics else None,
        "usage_tip": "Copy the markdown_report and paste directly into your Obsidian vault",
    }
