"""Test full text fetching to see what we're getting."""

import asyncio
import json

from app.mcp_client import get_client


async def test_full_text():
    """Test fetching and examining full opinion text."""
    client = get_client()

    # First, find a case citing Roe
    results = await client.find_citing_cases("410 U.S. 113", limit=1)

    if not results:
        print("No results found")
        return

    case = results[0]
    print("=" * 80)
    print(f"Case: {case.get('caseName')}")
    print(f"Citation: {case.get('citation')}")
    print(f"Date: {case.get('dateFiled')}")
    print("=" * 80)

    # Get opinion IDs
    opinions = case.get("opinions", [])
    if not opinions:
        print("No opinions found")
        return

    opinion_id = opinions[0].get("id")
    print(f"\nFetching full text for opinion ID: {opinion_id}")

    # Fetch full text
    full_text = await client.get_opinion_full_text(opinion_id)

    if not full_text:
        print("No full text available")
        return

    print(f"\nFull text length: {len(full_text)} characters")
    print("\n" + "=" * 80)
    print("SEARCHING FOR CITATION '410 U.S. 113' IN FULL TEXT:")
    print("=" * 80)

    # Search for the citation
    import re

    # Try different citation patterns
    patterns = [
        r"410\s+U\.?\s*S\.?\s+113",
        r"Roe\s+v\.?\s+Wade",
        r"410 U\. S\. 113",
    ]

    for pattern in patterns:
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
        if matches:
            print(f"\nFound {len(matches)} matches for pattern: {pattern}")
            for i, match in enumerate(matches[:3], 1):  # Show first 3 matches
                start = max(0, match.start() - 200)
                end = min(len(full_text), match.end() + 200)
                context = full_text[start:end]
                print(f"\nMatch {i} (position {match.start()}):")
                print(context)
                print("-" * 80)
        else:
            print(f"No matches for pattern: {pattern}")

    # Show first 1000 characters
    print("\n" + "=" * 80)
    print("FIRST 1000 CHARACTERS OF FULL TEXT:")
    print("=" * 80)
    print(full_text[:1000])


if __name__ == "__main__":
    asyncio.run(test_full_text())
