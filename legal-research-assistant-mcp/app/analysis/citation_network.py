"""Citation network analysis and graph construction.

This module builds citation networks showing how cases cite each other,
enabling visualization of precedent flow and influence analysis.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.logging_utils import log_event

logger = logging.getLogger(__name__)


@dataclass
class CaseNode:
    """A node in the citation network representing a case."""

    citation: str
    case_name: str
    date_filed: str | None
    court: str | None
    cluster_id: int | None
    opinion_ids: list[int]
    metadata: dict[str, Any]


@dataclass
class CitationEdge:
    """An edge in the citation network representing a citation relationship."""

    from_citation: str  # Citing case
    to_citation: str  # Cited case
    depth: int  # Distance from root case
    treatment: str | None  # How the citing case treats the cited case
    confidence: float  # Confidence in treatment classification
    excerpt: str  # Relevant text excerpt


@dataclass
class CitationNetwork:
    """A citation network graph structure."""

    root_citation: str
    nodes: dict[str, CaseNode]
    edges: list[CitationEdge]
    depth_map: dict[str, int]  # Citation -> depth from root
    citing_counts: dict[str, int]  # How many cases cite each case
    cited_counts: dict[str, int]  # How many cases each case cites


class CitationNetworkBuilder:
    """Builder for constructing citation networks from CourtListener data."""

    def __init__(self, max_depth: int = 2, max_nodes: int = 100) -> None:
        """Initialize the citation network builder.

        Args:
            max_depth: Maximum depth to traverse from root case
            max_nodes: Maximum number of nodes to include in network
        """
        self.max_depth = max_depth
        self.max_nodes = max_nodes

    def build_network(
        self,
        root_case: dict[str, Any],
        citing_cases: list[dict[str, Any]],
        treatments: list[dict[str, Any]] | None = None,
    ) -> CitationNetwork:
        """Build a citation network from a root case and its citing cases.

        Args:
            root_case: The root case (the case being cited)
            citing_cases: List of cases that cite the root case
            treatments: Optional treatment analysis results

        Returns:
            CitationNetwork with nodes and edges
        """
        log_event(
            logger,
            "Building citation network",
            tool_name="citation_network_builder",
            query_params={"root_case": root_case.get("citation")},
            event="build_network",
        )

        nodes: dict[str, CaseNode] = {}
        edges: list[CitationEdge] = []
        depth_map: dict[str, int] = {}
        citing_counts: dict[str, int] = defaultdict(int)
        cited_counts: dict[str, int] = defaultdict(int)

        # Create root node
        root_citation = self._extract_citation(root_case)
        root_node = self._create_node(root_case)
        nodes[root_citation] = root_node
        depth_map[root_citation] = 0

        # Create treatment lookup
        treatment_map = {}
        if treatments:
            for treatment in treatments:
                citing_citation = self._extract_citation(treatment.get("citing_case", {}))
                treatment_map[citing_citation] = treatment

        # Add citing cases as nodes and edges
        for i, citing_case in enumerate(citing_cases):
            if len(nodes) >= self.max_nodes:
                logger.warning(f"Reached max nodes limit ({self.max_nodes}), stopping")
                break

            citing_citation = self._extract_citation(citing_case)

            # Create node for citing case
            citing_node = self._create_node(citing_case)
            nodes[citing_citation] = citing_node
            depth_map[citing_citation] = 1  # Direct citations are depth 1

            # Get treatment info if available
            treatment_info = treatment_map.get(citing_citation, {})

            # Create edge from citing case to root case
            edge = CitationEdge(
                from_citation=citing_citation,
                to_citation=root_citation,
                depth=1,
                treatment=treatment_info.get("treatment"),
                confidence=treatment_info.get("confidence", 0.0),
                excerpt=treatment_info.get("excerpt", ""),
            )
            edges.append(edge)

            # Update counts
            citing_counts[root_citation] += 1
            cited_counts[citing_citation] += 1

        log_event(
            logger,
            "Built citation network",
            tool_name="citation_network_builder",
            query_params={"root_case": root_citation},
            citation_count=len(edges),
            extra_context={"node_count": len(nodes), "max_depth": max(depth_map.values())},
            event="build_network_complete",
        )

        return CitationNetwork(
            root_citation=root_citation,
            nodes=nodes,
            edges=edges,
            depth_map=depth_map,
            citing_counts=dict(citing_counts),
            cited_counts=dict(cited_counts),
        )

    def _extract_citation(self, case: dict[str, Any]) -> str:
        """Extract the primary citation from a case.

        Args:
            case: Case data from CourtListener

        Returns:
            Primary citation string
        """
        citations = case.get("citation", [])
        if isinstance(citations, list) and citations:
            return str(citations[0])
        if isinstance(citations, str):
            return citations
        return str(case.get("cluster_id", "unknown"))

    def _create_node(self, case: dict[str, Any]) -> CaseNode:
        """Create a case node from CourtListener case data.

        Args:
            case: Case data from CourtListener

        Returns:
            CaseNode instance
        """
        citation = self._extract_citation(case)

        # Extract opinion IDs
        opinions = case.get("opinions", [])
        opinion_ids = [op.get("id") for op in opinions if op.get("id")]

        return CaseNode(
            citation=citation,
            case_name=case.get("caseName", "Unknown Case"),
            date_filed=case.get("dateFiled"),
            court=case.get("court"),
            cluster_id=case.get("cluster_id"),
            opinion_ids=opinion_ids,
            metadata={
                "status": case.get("status"),
                "precedential_status": case.get("precedentialStatus"),
                "judge": case.get("judge"),
            },
        )

    def get_network_statistics(self, network: CitationNetwork) -> dict[str, Any]:
        """Calculate statistics about the citation network.

        Args:
            network: The citation network to analyze

        Returns:
            Dictionary with network statistics
        """
        # Count treatments
        treatment_counts: defaultdict[str, int] = defaultdict(int)
        for edge in network.edges:
            if edge.treatment:
                treatment_counts[edge.treatment] += 1

        # Find most cited cases
        most_cited = sorted(
            network.citing_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        # Find most influential cases (those that cite many others)
        most_influential = sorted(
            network.cited_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return {
            "total_nodes": len(network.nodes),
            "total_edges": len(network.edges),
            "max_depth": max(network.depth_map.values()) if network.depth_map else 0,
            "treatment_distribution": dict(treatment_counts),
            "most_cited_cases": most_cited,
            "most_influential_cases": most_influential,
            "root_citation_count": network.citing_counts.get(network.root_citation, 0),
        }

    def filter_network(
        self,
        network: CitationNetwork,
        treatments: list[str] | None = None,
        min_confidence: float = 0.0,
        date_after: str | None = None,
        date_before: str | None = None,
    ) -> CitationNetwork:
        """Filter a citation network based on criteria.

        Args:
            network: The network to filter
            treatments: List of treatments to include (e.g., ["overruled", "questioned"])
            min_confidence: Minimum confidence score for treatment classification
            date_after: Only include cases filed after this date (YYYY-MM-DD)
            date_before: Only include cases filed before this date (YYYY-MM-DD)

        Returns:
            Filtered citation network
        """
        filtered_edges = []

        for edge in network.edges:
            # Filter by treatment
            if treatments and edge.treatment not in treatments:
                continue

            # Filter by confidence
            if edge.confidence < min_confidence:
                continue

            # Filter by date
            citing_node = network.nodes.get(edge.from_citation)
            if citing_node and citing_node.date_filed:
                if date_after and citing_node.date_filed < date_after:
                    continue
                if date_before and citing_node.date_filed > date_before:
                    continue

            filtered_edges.append(edge)

        # Rebuild nodes with only those referenced in filtered edges
        filtered_nodes = {network.root_citation: network.nodes[network.root_citation]}
        for edge in filtered_edges:
            if edge.from_citation in network.nodes:
                filtered_nodes[edge.from_citation] = network.nodes[edge.from_citation]
            if edge.to_citation in network.nodes:
                filtered_nodes[edge.to_citation] = network.nodes[edge.to_citation]

        # Rebuild counts
        citing_counts: dict[str, int] = defaultdict(int)
        cited_counts: dict[str, int] = defaultdict(int)
        for edge in filtered_edges:
            citing_counts[edge.to_citation] += 1
            cited_counts[edge.from_citation] += 1

        # Keep depth map for filtered nodes
        filtered_depth_map = {
            citation: depth
            for citation, depth in network.depth_map.items()
            if citation in filtered_nodes
        }

        logger.info(
            f"Filtered network from {len(network.nodes)} to {len(filtered_nodes)} nodes, "
            f"{len(network.edges)} to {len(filtered_edges)} edges"
        )

        return CitationNetwork(
            root_citation=network.root_citation,
            nodes=filtered_nodes,
            edges=filtered_edges,
            depth_map=filtered_depth_map,
            citing_counts=dict(citing_counts),
            cited_counts=dict(cited_counts),
        )
