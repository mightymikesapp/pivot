"""Mermaid diagram generation for citation networks.

This module converts citation networks into Mermaid diagram syntax
for visualization in Obsidian and other markdown-compatible tools.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MermaidGenerator:
    """Generator for creating Mermaid diagrams from citation networks."""

    def __init__(self) -> None:
        """Initialize the Mermaid generator."""
        pass

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
    ) -> str:
        """Generate a Mermaid flowchart from a citation network.

        Args:
            network: Citation network dictionary from build_citation_network()
            direction: Flowchart direction (TB=top-bottom, LR=left-right, BT=bottom-top, RL=right-left)
            include_dates: Whether to include filing dates in node labels
            color_by_treatment: Whether to color edges by treatment type

        Returns:
            Mermaid flowchart syntax
        """
        lines = [f"flowchart {direction}"]

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

            # Root node gets special styling
            if citation == network["root_citation"]:
                lines.append(f'    {node_id}["{label}"]:::root')
            else:
                lines.append(f'    {node_id}["{label}"]')

        # Create edges
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
            if color_by_treatment and treatment:
                style_class = self._get_treatment_style(treatment)
                lines.append(f'    {from_id} -->|"{edge_text}"| {to_id}')
                lines.append(f"    linkStyle {len([l for l in lines if '-->' in l]) - 1} stroke:{self._get_color(style_class)},stroke-width:2px")
            else:
                lines.append(f'    {from_id} -->|"{edge_text}"| {to_id}')

        # Add style definitions
        lines.append("")
        lines.append("    classDef root fill:#4A90E2,stroke:#2E5C8A,stroke-width:3px,color:#fff")
        lines.append("    classDef positive fill:#90EE90,stroke:#228B22,stroke-width:2px")
        lines.append("    classDef negative fill:#FFB6C1,stroke:#DC143C,stroke-width:2px")
        lines.append("    classDef questioned fill:#FFD700,stroke:#DAA520,stroke-width:2px")
        lines.append("    classDef neutral fill:#E8E8E8,stroke:#666,stroke-width:1px")

        return "\n".join(lines)

    def _get_color(self, style_class: str) -> str:
        """Get color for a style class.

        Args:
            style_class: Style class name

        Returns:
            Color code
        """
        colors = {
            "positive": "#228B22",
            "negative": "#DC143C",
            "questioned": "#DAA520",
            "neutral": "#666",
        }
        return colors.get(style_class, "#666")

    def generate_graph(
        self,
        network: dict[str, Any],
        direction: str = "LR",
        show_treatments: bool = True,
    ) -> str:
        """Generate a Mermaid graph (simpler style) from a citation network.

        Args:
            network: Citation network dictionary
            direction: Graph direction (LR or TB)
            show_treatments: Whether to show treatment labels

        Returns:
            Mermaid graph syntax
        """
        lines = [f"graph {direction}"]

        # Create nodes and edges
        node_map = {}
        for node in network["nodes"]:
            citation = node["citation"]
            node_id = self._get_node_id(citation)
            node_map[citation] = node_id

            case_name = self._sanitize_label(node["case_name"], max_length=25)

            if citation == network["root_citation"]:
                lines.append(f'    {node_id}(("{case_name}"))')
            else:
                lines.append(f'    {node_id}["{case_name}"]')

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
