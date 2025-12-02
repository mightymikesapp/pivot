"""Test script for quote verification functionality."""

import asyncio
import json

from app.tools.verification import verify_quote_impl, batch_verify_quotes_impl


async def test_exact_quote():
    """Test with an exact quote from a case."""
    print("\n" + "=" * 80)
    print("TEST 1: Exact Quote Verification")
    print("=" * 80)
    print("Testing a quote from Roe v. Wade\n")

    # This is an approximate quote - we'll see what we find
    quote = "the right of privacy is broad enough to encompass a woman's decision"
    citation = "410 U.S. 113"

    result = await verify_quote_impl(quote, citation)

    print(json.dumps(result, indent=2))


async def test_fuzzy_quote():
    """Test with a slightly modified quote."""
    print("\n" + "=" * 80)
    print("TEST 2: Fuzzy Quote Verification")
    print("=" * 80)
    print("Testing with minor modifications\n")

    # Quote with minor changes
    quote = "right to privacy encompasses woman's decision"
    citation = "410 U.S. 113"

    result = await verify_quote_impl(quote, citation)

    print(json.dumps(result, indent=2))


async def test_nonexistent_quote():
    """Test with a quote that doesn't exist."""
    print("\n" + "=" * 80)
    print("TEST 3: Non-existent Quote")
    print("=" * 80)
    print("Testing with a fabricated quote\n")

    quote = "This quote definitely does not appear anywhere in the case"
    citation = "410 U.S. 113"

    result = await verify_quote_impl(quote, citation)

    print(json.dumps(result, indent=2))


async def test_batch_verification():
    """Test batch quote verification."""
    print("\n" + "=" * 80)
    print("TEST 4: Batch Quote Verification")
    print("=" * 80)
    print("Testing multiple quotes at once\n")

    quotes = [
        {
            "quote": "the right of privacy",
            "citation": "410 U.S. 113",
        },
        {
            "quote": "State criminal abortion laws",
            "citation": "410 U.S. 113",
        },
        {
            "quote": "This is a fake quote",
            "citation": "410 U.S. 113",
        },
    ]

    result = await batch_verify_quotes_impl(quotes)

    print(json.dumps(result, indent=2))


async def main():
    """Run all quote verification tests."""
    print("\n🔬 Legal Research Assistant MCP - Quote Verification Testing")
    print("This will test the quote verification functionality.\n")

    try:
        await test_exact_quote()
        await test_fuzzy_quote()
        await test_nonexistent_quote()
        await test_batch_verification()

        print("\n" + "=" * 80)
        print("✅ All quote verification tests completed!")
        print("=" * 80)
        print("\nNote: Results depend on CourtListener API availability and data.")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
