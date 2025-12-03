"""Mermaid diagram generation for citation networks.

This module converts citation networks into Mermaid diagram syntax
for visualization in Obsidian and other markdown-compatible tools.
It also provides export helpers for GraphML/JSON structures to
support external visualization utilities.
"""

import logging
from collections import defaultdict
from html import escape
from itertools import cycle
from typing import Any

logger = logging.getLogger(__name__)


class MermaidGenerator:
    """Generator for creating Mermaid diagrams from citation networks."""

    def __init__(self) -> None:
        """Initialize the Mermaid generator."""
        self.default_treatment_palette = {
            "positive": "#228B22",
            "negative": "#DC143C",
            "questioned": "#DAA520",
            "neutral": "#666",
        }
        self.default_court_palette = {
            "scotus": "#4A90E2",
            "circa": "#7B61FF",
            "district": "#2DBE8D",
            "state": "#FF9F1C",
            "unknown": "#B0B0B0",
        }

    def _build_color_palette(
        self, values: list[str], base_palette: dict[str, str]
    ) -> dict[str, str]:
        """Assign colors to categorical values using a palette with fallbacks."""

        colors = [
            "#4A90E2",
            "#2DBE8D",
            "#FF9F1C",
            "#7B61FF",
            "#EF476F",
            "#06D6A0",
            "#FFD166",
            "#118AB2",
        ]

        palette = base_palette.copy()
        color_cycle = cycle(colors)

        for value in values:
            key = (value or "unknown").lower()
            if key not in palette:
                palette[key] = next(color_cycle)

        return palette

    def _calculate_node_scores(
        self, network: dict[str, Any]
    ) -> tuple[dict[str, int], dict[str, int]]:
        """Calculate citation and authority scores for nodes."""

        citation_counts: dict[str, int] = defaultdict(int)
        authority_counts: dict[str, int] = defaultdict(int)

        for edge in network.get("edges", []):
            citation_counts[edge["to_citation"]] += 1
            authority_counts[edge["from_citation"]] += 1

        return dict(citation_counts), dict(authority_counts)

    def _size_class(self, score: int, max_score: int) -> str:
        """Get a size class name based on score magnitude."""

        if max_score <= 1:
            return "size-sm"

        ratio = score / max_score
        if ratio > 0.66:
            return "size-lg"
        if ratio > 0.33:
            return "size-md"
        return "size-sm"

    def _sanitize_class_key(self, value: str | None) -> str:
        """Convert arbitrary text to a Mermaid-safe class key."""

        key = (value or "unknown").lower()
        cleaned = "".join(ch if ch.isalnum() else "_" for ch in key)
        return cleaned or "unknown"

    def _sanitize_label(self, text: str, max_length: int = 40) -> str:
        """Sanitize text for use in Mermaid node labels.

        Args:
            text: Text to sanitize
            max_length: Maximum length for label

        Returns:
            Sanitized text safe for Mermaid
        """
        # Remove characters that break Mermaid syntax
        text = text.replace('"', "'").replace("\n", " ").replace("\r", " ")
        text = text.replace("[", "(").replace("]", ")")
        text = text.replace("{", "(").replace("}", ")")

        # Truncate if too long
        if len(text) > max_length:
            text = text[: max_length - 3] + "..."

        return text

    def _get_node_id(self, citation: str) -> str:
        """Generate a valid Mermaid node ID from a citation.

        Args:
            citation: Case citation

        Returns:
            Safe node ID for Mermaid
        """
        # Replace problematic characters
        node_id = citation.replace(" ", "_").replace(".", "_")
        node_id = node_id.replace(",", "_").replace("-", "_")
        # Ensure it starts with a letter
        if node_id and not node_id[0].isalpha():
            node_id = "case_" + node_id
        return node_id

    def _get_treatment_style(self, treatment: str | None) -> str:
        """Get Mermaid style class for a treatment type.

        Args:
            treatment: Treatment classification

        Returns:
            Style class name
        """
        if not treatment:
            return "neutral"

        treatment_lower = treatment.lower()

        # Negative treatments
        if any(
            neg in treatment_lower
            for neg in ["overruled", "reversed", "vacated", "abrogated", "superseded"]
        ):
            return "negative"

        # Questioned treatments
        if any(
            q in treatment_lower
            for q in ["questioned", "criticized", "limited", "distinguished"]
        ):
            return "questioned"

        # Positive treatments
        if any(
            pos in treatment_lower
            for pos in ["followed", "affirmed", "approved", "adopted", "cited"]
        ):
            return "positive"

        return "neutral"

    def generate_flowchart(
        self,
        network: dict[str, Any],
        direction: str = "TB",
        include_dates: bool = True,
        color_by_treatment: bool = True,
        color_by_court: bool = True,
        node_size_by: str | None = None,
        court_palette: dict[str, str] | None = None,
        treatment_palette: dict[str, str] | None = None,
        show_legend: bool = True,
    ) -> str:
        """Generate a Mermaid flowchart from a citation network.

        Args:
            network: Citation network dictionary from build_citation_network()
            direction: Flowchart direction (TB=top-bottom, LR=left-right, BT=bottom-top, RL=right-left)
            include_dates: Whether to include filing dates in node labels
            color_by_treatment: Whether to color edges by treatment type
            color_by_court: Whether to color nodes by court
            node_size_by: Size nodes by "citation" or "authority" scores
            court_palette: Optional custom palette for courts
            treatment_palette: Optional custom palette for treatments
            show_legend: Whether to include a legend explaining styling

        Returns:
            Mermaid flowchart syntax
        """
        lines = [f"flowchart {direction}"]

        citation_scores, authority_scores = self._calculate_node_scores(network)
        size_scores: dict[str, int] = {}
        if node_size_by == "citation":
            size_scores = citation_scores
        elif node_size_by == "authority":
            size_scores = authority_scores

        max_size_score = max(size_scores.values()) if size_scores else 1

        court_labels: dict[str, str] = {}
        for node in network["nodes"]:
            raw_court = node.get("court", "unknown") or "unknown"
            court_key = self._sanitize_class_key(raw_court)
            court_labels[court_key] = raw_court
        court_palette = self._build_color_palette(
            list(court_labels.keys()), court_palette or self.default_court_palette
        )
        treatment_palette = {
            **self.default_treatment_palette,
            **(treatment_palette or {}),
        }

        # Create node definitions
        node_map = {}
        for node in network["nodes"]:
            citation = node["citation"]
            node_id = self._get_node_id(citation)
            node_map[citation] = node_id

            # Build label
            case_name = self._sanitize_label(node["case_name"], max_length=30)
            label_parts = [case_name]

            if include_dates and node.get("date_filed"):
                year = node["date_filed"][:4]
                label_parts.append(year)

            label = f"{label_parts[0]}<br/>{label_parts[1]}" if len(label_parts) > 1 else label_parts[0]

            classes = []
            if citation == network["root_citation"]:
                classes.append("root")

            if color_by_court:
                court_key = self._sanitize_class_key(node.get("court"))
                classes.append(f"court_{court_key}")

            if node_size_by:
                score = size_scores.get(citation, 0)
                classes.append(self._size_class(score, max_size_score))

            class_suffix = f":::{','.join(classes)}" if classes else ""
            lines.append(f'    {node_id}["{label}"]{class_suffix}')

        # Create edges
        link_index = 0
        for edge in network["edges"]:
            from_id = node_map.get(edge["from_citation"])
            to_id = node_map.get(edge["to_citation"])

            if not from_id or not to_id:
                continue

            # Build edge label
            treatment = edge.get("treatment")
            confidence = edge.get("confidence", 0)

            if treatment and confidence > 0:
                treatment_label = self._sanitize_label(treatment, max_length=15)
                edge_text = f"{treatment_label} ({confidence:.0%})"
            else:
                edge_text = "cites"

            # Add edge with styling
            lines.append(f'    {from_id} -->|"{edge_text}"| {to_id}')

            if color_by_treatment and treatment:
                style_class = self._get_treatment_style(treatment)
                color = self._get_color(style_class, treatment_palette)
                lines.append(
                    f"    linkStyle {link_index} stroke:{color},stroke-width:2px"
                )
            link_index += 1

        # Add style definitions
        lines.append("")
        lines.append("    classDef root fill:#4A90E2,stroke:#2E5C8A,stroke-width:3px,color:#fff")
        lines.append("    classDef positive fill:#90EE90,stroke:#228B22,stroke-width:2px")
        lines.append("    classDef negative fill:#FFB6C1,stroke:#DC143C,stroke-width:2px")
        lines.append("    classDef questioned fill:#FFD700,stroke:#DAA520,stroke-width:2px")
        lines.append("    classDef neutral fill:#E8E8E8,stroke:#666,stroke-width:1px")
        lines.append("    classDef size-sm stroke-width:1px")
        lines.append("    classDef size-md stroke-width:2px,fill-opacity:90%")
        lines.append("    classDef size-lg stroke-width:3px,fill-opacity:85%")

        if color_by_court:
            for court, color in court_palette.items():
                lines.append(
                    f"    classDef court_{court} fill:{color},stroke:#1A1A1A,stroke-width:1.5px,color:#fff"
                )

        if show_legend:
            lines.append("    classDef legend fill:#f6f8fa,stroke:#d0d7de,stroke-width:1px")
            lines.append("    subgraph Legend")
            lines.append("      direction TB")
            lines.append("      legend_info[\"Styling\"]:::legend")

            if color_by_treatment:
                lines.append("      legend_treatments[[\"Treatment colors\"]]")
                for treatment, color in treatment_palette.items():
                    style_class = self._get_treatment_style(treatment)
                    lines.append(
                        f"      legend_{style_class}[\"{treatment.title()}\"]:::legend_{style_class}"
                    )
                    lines.append(
                        f"    classDef legend_{style_class} fill:{color},stroke:#1A1A1A,stroke-width:1px,color:#fff"
                    )

            if color_by_court:
                lines.append("      legend_courts[[\"Courts\"]]")
                for court, color in court_palette.items():
                    lines.append(
                        f"      legend_court_{court}[\"{court_labels.get(court, court).upper()}\"]:::court_{court}"
                    )

            if node_size_by:
                lines.append(
                    "      legend_sizes[[\"Node size by "
                    + node_size_by
                    + " score\"]]"
                )
                lines.append("      legend_small[\"Low\"]:::size-sm")
                lines.append("      legend_medium[\"Medium\"]:::size-md")
                lines.append("      legend_large[\"High\"]:::size-lg")

            lines.append("    end")

        return "\n".join(lines)

    def _get_color(self, style_class: str, palette: dict[str, str]) -> str:
        """Get color for a style class from the provided palette."""

        return palette.get(style_class, palette.get("neutral", "#666"))

    def generate_graph(
        self,
        network: dict[str, Any],
        direction: str = "LR",
        show_treatments: bool = True,
        color_by_court: bool = True,
        node_size_by: str | None = None,
        court_palette: dict[str, str] | None = None,
        show_legend: bool = False,
    ) -> str:
        """Generate a Mermaid graph (simpler style) from a citation network.

        Args:
            network: Citation network dictionary
            direction: Graph direction (LR or TB)
            show_treatments: Whether to show treatment labels
            color_by_court: Whether to color nodes by court
            node_size_by: Size nodes by "citation" or "authority" scores
            court_palette: Optional custom palette for courts
            show_legend: Whether to include a legend block

        Returns:
            Mermaid graph syntax
        """
        lines = [f"graph {direction}"]

        citation_scores, authority_scores = self._calculate_node_scores(network)
        size_scores: dict[str, int] = {}
        if node_size_by == "citation":
            size_scores = citation_scores
        elif node_size_by == "authority":
            size_scores = authority_scores

        max_size_score = max(size_scores.values()) if size_scores else 1
        court_labels: dict[str, str] = {}
        for node in network["nodes"]:
            raw_court = node.get("court", "unknown") or "unknown"
            court_key = self._sanitize_class_key(raw_court)
            court_labels[court_key] = raw_court
        court_palette = self._build_color_palette(
            list(court_labels.keys()), court_palette or self.default_court_palette
        )

        # Create nodes and edges
        node_map = {}
        for node in network["nodes"]:
            citation = node["citation"]
            node_id = self._get_node_id(citation)
            node_map[citation] = node_id

            case_name = self._sanitize_label(node["case_name"], max_length=25)
            classes = []
            if citation == network["root_citation"]:
                classes.append("root")
                shape = "((\"{case}\"))"
            else:
                shape = "[\"{case}\"]"

            if color_by_court:
                court_key = self._sanitize_class_key(node.get("court"))
                classes.append(f"court_{court_key}")

            if node_size_by:
                score = size_scores.get(citation, 0)
                classes.append(self._size_class(score, max_size_score))

            class_suffix = f":::{','.join(classes)}" if classes else ""
            lines.append(f"    {node_id}{shape.format(case=case_name)}{class_suffix}")

        # Create edges
        for edge in network["edges"]:
            from_id = node_map.get(edge["from_citation"])
            to_id = node_map.get(edge["to_citation"])

            if not from_id or not to_id:
                continue

            if show_treatments and edge.get("treatment"):
                treatment = self._sanitize_label(edge["treatment"], max_length=12)
                lines.append(f'    {from_id} -.->|{treatment}| {to_id}')
            else:
                lines.append(f"    {from_id} --> {to_id}")

        lines.append("")
        lines.append("    classDef root stroke:#2E5C8A,stroke-width:3px")
        lines.append("    classDef size-sm stroke-width:1px")
        lines.append("    classDef size-md stroke-width:2px,fill-opacity:90%")
        lines.append("    classDef size-lg stroke-width:3px,fill-opacity:85%")
        if color_by_court:
            for court, color in court_palette.items():
                lines.append(
                    f"    classDef court_{court} fill:{color},stroke:#1A1A1A,stroke-width:1.5px,color:#fff"
                )

        if show_legend:
            lines.append("    classDef legend fill:#f6f8fa,stroke:#d0d7de,stroke-width:1px")
            lines.append("    subgraph Legend")
            lines.append("      direction TB")
            lines.append("      legend_info[\"Graph styling\"]:::legend")

            if color_by_court:
                lines.append("      legend_courts[[\"Courts\"]]")
                for court, color in court_palette.items():
                    lines.append(
                        f"      legend_court_{court}[\"{court_labels.get(court, court).upper()}\"]:::court_{court}"
                    )

            if node_size_by:
                lines.append(
                    "      legend_sizes[[\"Node size by "
                    + node_size_by
                    + " score\"]]"
                )
                lines.append("      legend_small[\"Low\"]:::size-sm")
                lines.append("      legend_medium[\"Medium\"]:::size-md")
                lines.append("      legend_large[\"High\"]:::size-lg")

            lines.append("    end")

        return "\n".join(lines)

    def generate_timeline(
        self,
        network: dict[str, Any],
        treatment_filter: list[str] | None = None,
    ) -> str:
        """Generate a Mermaid timeline showing citations over time.

        Args:
            network: Citation network dictionary
            treatment_filter: Optional list of treatments to include

        Returns:
            Mermaid timeline syntax
        """
        # Collect cases by year
        timeline_data: dict[str, list[tuple[str, str | None]]] = {}

        for node in network["nodes"]:
            if node["citation"] == network["root_citation"]:
                continue

            date_filed = node.get("date_filed")
            if not date_filed:
                continue

            year = date_filed[:4]

            # Find associated edge to get treatment
            treatment = None
            for edge in network["edges"]:
                if edge["from_citation"] == node["citation"]:
                    treatment = edge.get("treatment")
                    break

            # Apply filter
            if treatment_filter and treatment not in treatment_filter:
                continue

            case_name = self._sanitize_label(node["case_name"], max_length=20)

            if year not in timeline_data:
                timeline_data[year] = []

            timeline_data[year].append((case_name, treatment))

        # Generate timeline
        lines = ["timeline"]
        lines.append(f'    title Citation History: {network["root_case_name"]}')

        for year in sorted(timeline_data.keys()):
            cases = timeline_data[year]
            lines.append(f"    {year}")

            for case_name, treatment in cases[:3]:  # Limit to 3 per year
                if treatment:
                    lines.append(f"      : {case_name} ({treatment})")
                else:
                    lines.append(f"      : {case_name}")

        return "\n".join(lines)

    def generate_graphml(self, network: dict[str, Any]) -> str:
        """Export the citation network as GraphML."""

        lines = [
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            "<graphml xmlns=\"http://graphml.graphdrawing.org/xmlns\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd\">",
            '  <key id="d0" for="node" attr.name="label" attr.type="string"/>',
            '  <key id="d1" for="node" attr.name="court" attr.type="string"/>',
            '  <key id="d2" for="node" attr.name="date_filed" attr.type="string"/>',
            '  <key id="d3" for="edge" attr.name="treatment" attr.type="string"/>',
            '  <key id="d4" for="edge" attr.name="confidence" attr.type="double"/>',
            '  <key id="d5" for="edge" attr.name="excerpt" attr.type="string"/>',
            '  <graph id="citation_network" edgedefault="directed">',
        ]

        for node in network.get("nodes", []):
            node_id = self._get_node_id(node["citation"])
            lines.append(f'    <node id="{escape(node_id)}">')
            lines.append(f'      <data key="d0">{escape(node["case_name"])}</data>')
            lines.append(f'      <data key="d1">{escape(str(node.get("court", "")))}</data>')
            lines.append(f'      <data key="d2">{escape(str(node.get("date_filed", "")))}</data>')
            lines.append("    </node>")

        for i, edge in enumerate(network.get("edges", [])):
            source = self._get_node_id(edge["from_citation"])
            target = self._get_node_id(edge["to_citation"])
            lines.append(f'    <edge id="e{i}" source="{escape(source)}" target="{escape(target)}">')
            lines.append(f'      <data key="d3">{escape(str(edge.get("treatment", "")))}</data>')
            lines.append(f'      <data key="d4">{edge.get("confidence", 0.0)}</data>')
            lines.append(f'      <data key="d5">{escape(edge.get("excerpt", ""))}</data>')
            lines.append("    </edge>")

        lines.append("  </graph>")
        lines.append("</graphml>")

        return "\n".join(lines)

    def generate_json_graph(self, network: dict[str, Any]) -> dict[str, Any]:
        """Export the citation network as a JSON graph structure."""

        citation_scores, authority_scores = self._calculate_node_scores(network)

        nodes = []
        for node in network.get("nodes", []):
            citation = node["citation"]
            nodes.append(
                {
                    "id": self._get_node_id(citation),
                    "citation": citation,
                    "case_name": node.get("case_name"),
                    "court": node.get("court"),
                    "date_filed": node.get("date_filed"),
                    "citation_score": citation_scores.get(citation, 0),
                    "authority_score": authority_scores.get(citation, 0),
                }
            )

        edges = []
        for edge in network.get("edges", []):
            edges.append(
                {
                    "source": self._get_node_id(edge["from_citation"]),
                    "target": self._get_node_id(edge["to_citation"]),
                    "treatment": edge.get("treatment"),
                    "confidence": edge.get("confidence", 0.0),
                    "excerpt": edge.get("excerpt", ""),
                }
            )

        return {"nodes": nodes, "edges": edges, "root": network.get("root_citation")}

    def generate_summary_stats(self, network: dict[str, Any]) -> str:
        """Generate a text summary of network statistics.

        Args:
            network: Citation network dictionary

        Returns:
            Formatted summary text
        """
        stats = network.get("statistics", {})

        lines = [
            f"# Citation Network: {network['root_case_name']}",
            f"**Citation:** {network['root_citation']}",
            "",
            "## Network Statistics",
            f"- **Total Cases:** {stats.get('total_nodes', 0)}",
            f"- **Total Citations:** {stats.get('total_edges', 0)}",
            f"- **Network Depth:** {stats.get('max_depth', 0)}",
            "",
        ]

        # Treatment distribution
        treatment_dist = stats.get("treatment_distribution", {})
        if treatment_dist:
            lines.append("## Treatment Distribution")
            for treatment, count in sorted(
                treatment_dist.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"- **{treatment}:** {count}")
            lines.append("")

        return "\n".join(lines)
