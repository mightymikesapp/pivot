"""Test to see what text we get from Roe v. Wade."""

import asyncio

from app.mcp_client import get_client


async def test():
    """Test getting Roe text."""
    client = get_client()

    # Look up Roe
    case = await client.lookup_citation("410 U.S. 113")
    print(f"Case: {case.get('caseName')}")
    print(f"Date: {case.get('dateFiled')}")

    # Get opinion IDs
    opinion_ids = [op.get("id") for op in case.get("opinions", []) if op.get("id")]
    print(f"\nOpinion IDs: {opinion_ids}")

    # Try first opinion
    if opinion_ids:
        opinion_id = opinion_ids[0]
        print(f"\nFetching text for opinion {opinion_id}...")

        full_text = await client.get_opinion_full_text(opinion_id)

        if full_text:
            print(f"\nText length: {len(full_text)} chars")
            print("\nFirst 2000 characters:")
            print(full_text[:2000])

            # Search for some keywords
            keywords = ["privacy", "woman", "decision", "encompass"]
            print("\n\nKeyword search:")
            for keyword in keywords:
                count = full_text.lower().count(keyword.lower())
                print(f"  '{keyword}': {count} occurrences")

            # Try to find a specific phrase
            import re

            patterns = [
                r"right of privacy",
                r"woman's decision",
                r"privacy.*woman",
            ]

            print("\n\nPattern search:")
            for pattern in patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE | re.DOTALL)
                print(f"  '{pattern}': {len(matches)} matches")
                if matches:
                    for i, match in enumerate(matches[:2], 1):
                        # Get context
                        pos = full_text.lower().find(match.lower())
                        context_start = max(0, pos - 100)
                        context_end = min(len(full_text), pos + len(match) + 100)
                        context = full_text[context_start:context_end]
                        print(f"\n    Match {i}:")
                        print(f"    {context}")
        else:
            print("No text available")


if __name__ == "__main__":
    asyncio.run(test())
