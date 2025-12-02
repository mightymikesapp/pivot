"""Test script for citation network visualization."""

import asyncio
import json

from app.tools.network import visualize_citation_network, generate_citation_report


async def test_basic_visualization():
    """Test basic Mermaid diagram generation."""
    print("\n" + "=" * 80)
    print("TEST 1: Basic Citation Network Visualization")
    print("=" * 80)
    print("Generating flowchart for Roe v. Wade\n")

    result = await visualize_citation_network(
        citation="410 U.S. 113",
        diagram_type="flowchart",
        direction="TB",
        max_nodes=10,
    )

    print(f"Case: {result.get('case_name')}")
    print(f"Nodes: {result.get('node_count')}")
    print(f"Edges: {result.get('edge_count')}")
    print("\nMermaid Syntax:")
    print(result.get("mermaid_syntax"))


async def test_timeline_visualization():
    """Test timeline diagram generation."""
    print("\n" + "=" * 80)
    print("TEST 2: Timeline Visualization")
    print("=" * 80)
    print("Generating timeline for Roe v. Wade\n")

    result = await visualize_citation_network(
        citation="410 U.S. 113",
        diagram_type="timeline",
        max_nodes=10,
    )

    print(f"Case: {result.get('case_name')}")
    print("\nMermaid Timeline:")
    print(result.get("mermaid_syntax"))


async def test_full_report():
    """Test comprehensive citation report generation."""
    print("\n" + "=" * 80)
    print("TEST 3: Comprehensive Citation Report")
    print("=" * 80)
    print("Generating full report for Roe v. Wade\n")

    result = await generate_citation_report(
        citation="410 U.S. 113",
        include_diagram=True,
        include_statistics=True,
        treatment_focus=["overruled", "questioned", "limited"],
        max_nodes=15,
    )

    print(f"Case: {result.get('case_name')}")
    print("\nMarkdown Report:")
    print(result.get("markdown_report"))


async def test_filtered_network():
    """Test filtered network visualization."""
    print("\n" + "=" * 80)
    print("TEST 4: Filtered Network (Negative Treatments Only)")
    print("=" * 80)
    print("Showing only negative treatments\n")

    result = await generate_citation_report(
        citation="410 U.S. 113",
        include_diagram=True,
        include_statistics=True,
        treatment_focus=["overruled", "reversed", "vacated", "questioned"],
        max_nodes=20,
    )

    print(f"Case: {result.get('case_name')}")
    print(f"\nStatistics:")
    if result.get("statistics"):
        print(f"  Treatment Distribution: {result['statistics'].get('treatment_distribution')}")


async def main():
    """Run all visualization tests."""
    print("\n📊 Legal Research Assistant MCP - Visualization Testing")
    print("This will test the citation network visualization functionality.\n")

    try:
        await test_basic_visualization()
        await test_timeline_visualization()
        await test_full_report()
        await test_filtered_network()

        print("\n" + "=" * 80)
        print("✅ All visualization tests completed!")
        print("=" * 80)
        print("\nYou can now:")
        print("1. Copy the Mermaid syntax from above")
        print("2. Paste it in Obsidian between ```mermaid and ``` tags")
        print("3. The diagram will render automatically")
        print("\nOr use the markdown report directly in your notes!")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
