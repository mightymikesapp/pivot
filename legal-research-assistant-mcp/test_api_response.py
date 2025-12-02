"""Quick test to see what data CourtListener API returns."""

import asyncio
import json

from app.mcp_client import get_client


async def test_api_response():
    """Test what data we get from CourtListener."""
    client = get_client()

    # Search for cases mentioning Roe v. Wade
    results = await client.find_citing_cases("410 U.S. 113", limit=2)

    print("Number of results:", len(results))
    print("\n" + "=" * 80)
    print("SAMPLE RESULT (first case):")
    print("=" * 80)

    if results:
        # Print first result with all fields
        print(json.dumps(results[0], indent=2))

        print("\n" + "=" * 80)
        print("AVAILABLE FIELDS:")
        print("=" * 80)
        print(list(results[0].keys()))


if __name__ == "__main__":
    asyncio.run(test_api_response())
