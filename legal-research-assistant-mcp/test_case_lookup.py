"""Test to see what case we're actually getting."""

import asyncio
import json

from app.mcp_client import get_client


async def test_lookup():
    """Test case lookup."""
    client = get_client()

    # Search for Roe v. Wade
    result = await client.lookup_citation("410 U.S. 113")

    print("Case found:")
    print(f"Case Name: {result.get('caseName')}")
    print(f"Date Filed: {result.get('dateFiled')}")
    print(f"Court: {result.get('court')}")
    print(f"Cluster ID: {result.get('cluster_id')}")

    # Get opinions
    opinions = result.get("opinions", [])
    print(f"\nNumber of opinions: {len(opinions)}")

    if opinions:
        print(f"Opinion IDs: {[op.get('id') for op in opinions]}")

    # Try searching specifically for Roe v. Wade by name
    print("\n" + "=" * 80)
    print("Searching for 'Roe v. Wade' specifically:")
    print("=" * 80)

    search_result = await client.search_opinions(
        q="Roe v. Wade",
        court="scotus",
        filed_after="1970-01-01",
        filed_before="1975-01-01",
        limit=5,
    )

    print(f"\nFound {search_result.get('count')} results")
    if search_result.get("results"):
        for i, case in enumerate(search_result["results"][:3], 1):
            print(f"\n{i}. {case.get('caseName')}")
            print(f"   Date: {case.get('dateFiled')}")
            print(f"   Citation: {case.get('citation')}")
            print(f"   Cluster ID: {case.get('cluster_id')}")


if __name__ == "__main__":
    asyncio.run(test_lookup())
