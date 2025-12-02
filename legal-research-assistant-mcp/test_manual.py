"""Manual test script for Legal Research Assistant MCP.

This script provides a quick way to test the core functionality
without running the full MCP server.
"""

import asyncio
import json

from app.tools.treatment import check_case_validity_impl, get_citing_cases_impl


async def test_well_known_case():
    """Test with a well-known case that has been overruled."""
    print("\n" + "=" * 80)
    print("TEST 1: Checking Roe v. Wade (410 U.S. 113)")
    print("=" * 80)
    print("This case was overruled by Dobbs in 2022, so we expect negative treatment.\n")

    result = await check_case_validity_impl("410 U.S. 113")

    print(json.dumps(result, indent=2))


async def test_recent_case():
    """Test with a more recent case."""
    print("\n" + "=" * 80)
    print("TEST 2: Getting citing cases for a citation")
    print("=" * 80)

    result = await get_citing_cases_impl("410 U.S. 113", limit=5)

    print(json.dumps(result, indent=2))


async def test_negative_filter():
    """Test filtering for negative treatments."""
    print("\n" + "=" * 80)
    print("TEST 3: Getting citing cases with negative treatment filter")
    print("=" * 80)

    result = await get_citing_cases_impl(
        "410 U.S. 113",
        treatment_filter="negative",
        limit=3,
    )

    print(json.dumps(result, indent=2))


async def main():
    """Run all manual tests."""
    print("\n🔬 Legal Research Assistant MCP - Manual Testing")
    print("This will test the treatment analysis functionality.\n")

    try:
        await test_well_known_case()
        await test_recent_case()
        await test_negative_filter()

        print("\n" + "=" * 80)
        print("✅ All manual tests completed!")
        print("=" * 80)
        print("\nNote: Results depend on CourtListener API availability and data.")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
