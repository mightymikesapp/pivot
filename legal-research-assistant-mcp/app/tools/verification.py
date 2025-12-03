"""Quote verification tools for legal research.

This module provides MCP tools for verifying quotes against their cited sources,
essential for maintaining academic integrity in legal scholarship.
"""

import logging
from typing import Any

from fastmcp import FastMCP

from app.analysis.quote_matcher import QuoteMatcher
from app.logging_utils import log_event, log_operation
from app.mcp_client import get_client

logger = logging.getLogger(__name__)

# Initialize quote matcher
matcher = QuoteMatcher(
    exact_match_threshold=1.0,
    fuzzy_match_threshold=0.85,
    context_chars=200,
)


# Implementation functions
async def verify_quote_impl(
    quote: str,
    citation: str,
    pinpoint: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Verify a quote appears in the cited source.

    Args:
        quote: The quote to verify
        citation: The citation (e.g., "410 U.S. 113")
        pinpoint: Optional pinpoint citation (e.g., "at 153")

    Returns:
        Dictionary with verification results
    """
    client = get_client()

    with log_operation(
        logger,
        tool_name="verify_quote",
        request_id=request_id,
        query_params={"citation": citation, "pinpoint": pinpoint},
        event="verify_quote",
    ):
        # Step 1: Look up the case
        target_case = await client.lookup_citation(citation, request_id=request_id)

        if "error" in target_case:
            return {
                "error": f"Could not find case: {target_case.get('error')}",
                "citation": citation,
                "quote": quote,
            }

        case_name = target_case.get("caseName", "Unknown")
        log_event(
            logger,
            "Case located for quote verification",
            tool_name="verify_quote",
            request_id=request_id,
            query_params={"citation": citation, "pinpoint": pinpoint},
            event="verify_quote_case",
        )

        # Step 2: Get full text of the opinion
        # Extract opinion IDs
        opinion_ids = [
            op.get("id") for op in target_case.get("opinions", []) if op.get("id")
        ]

        if not opinion_ids:
            return {
                "error": "No opinion text available for this case",
                "citation": citation,
                "case_name": case_name,
                "quote": quote,
            }

        opinion_id = opinion_ids[0]
        full_text = await client.get_opinion_full_text(
            opinion_id, request_id=request_id
        )

        if not full_text:
            return {
                "error": "Could not retrieve opinion text",
                "citation": citation,
                "case_name": case_name,
                "quote": quote,
            }

        log_event(
            logger,
            "Opinion text retrieved for quote verification",
            tool_name="verify_quote",
            request_id=request_id,
            query_params={"citation": citation, "pinpoint": pinpoint},
            citation_count=len(full_text),
            event="verify_quote_text",
        )

        # Step 3: Verify the quote
        result = matcher.verify_quote(quote, full_text, citation)

        # Step 4: Build response
        response = {
            "citation": citation,
            "case_name": case_name,
            "quote": quote,
            "found": result.found,
            "exact_match": result.exact_match,
            "similarity": round(result.similarity, 3) if result.similarity else 0.0,
            "matches_found": len(result.matches),
            "warnings": result.warnings,
            "recommendation": result.recommendation,
        }

        # Add match details
        if result.matches:
            best_match = result.matches[0]
            response["best_match"] = {
                "position": best_match.position,
                "matched_text": best_match.matched_text[:200] + "..."
                if len(best_match.matched_text) > 200
                else best_match.matched_text,
                "context_before": best_match.context_before[-100:]
                if len(best_match.context_before) > 100
                else best_match.context_before,
                "context_after": best_match.context_after[:100]
                if len(best_match.context_after) > 100
                else best_match.context_after,
                "differences": best_match.differences if not best_match.exact_match else [],
            }

            # Include all match positions
            response["all_match_positions"] = [match.position for match in result.matches]

        # Validate pinpoint if provided
        if pinpoint:
            response["pinpoint_provided"] = pinpoint
            response["pinpoint_note"] = (
                "Note: Pinpoint page validation not yet implemented - "
                "CourtListener does not provide page numbers in API responses"
            )

        return response


async def batch_verify_quotes_impl(
    quotes: list[dict[str, str]],
    request_id: str | None = None,
) -> dict[str, Any]:
    """Verify multiple quotes in batch.

    Args:
        quotes: List of dicts with keys: "quote", "citation", optional "pinpoint"

    Returns:
        Dictionary with batch verification results
    """
    with log_operation(
        logger,
        tool_name="batch_verify_quotes",
        request_id=request_id,
        query_params={"total_quotes": len(quotes)},
        event="batch_verify_quotes",
    ):
        results = []
        for i, quote_data in enumerate(quotes, 1):
            log_event(
                logger,
                "Processing quote for verification",
                tool_name="batch_verify_quotes",
                request_id=request_id,
                query_params={"index": i, "citation": quote_data.get("citation")},
            )

            quote = quote_data.get("quote", "")
            citation = quote_data.get("citation", "")
            pinpoint = quote_data.get("pinpoint")

            if not quote or not citation:
                results.append(
                    {
                        "error": "Missing quote or citation",
                        "quote": quote,
                        "citation": citation,
                    }
                )
                continue

            result = await verify_quote_impl(
                quote, citation, pinpoint, request_id=request_id
            )
            results.append(result)

        # Summary statistics
        total = len(results)
        verified = sum(1 for r in results if r.get("found"))
        exact = sum(1 for r in results if r.get("exact_match"))
        errors = sum(1 for r in results if "error" in r)

        log_event(
            logger,
            "Batch verification complete",
            tool_name="batch_verify_quotes",
            request_id=request_id,
            query_params={"total_quotes": len(quotes)},
            citation_count=verified,
            event="batch_verify_quotes_complete",
        )

        return {
            "total_quotes": total,
            "verified": verified,
            "exact_matches": exact,
            "fuzzy_matches": verified - exact,
            "not_found": total - verified - errors,
            "errors": errors,
            "results": results,
        }


# Create verification tools server
verification_server = FastMCP(
    name="Quote Verification Tools",
    instructions="Tools for verifying legal quotes against their cited sources",
)


@verification_server.tool()
async def verify_quote(
    quote: str,
    citation: str,
    pinpoint: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Verify that a quote accurately appears in the cited case.

    This tool fetches the full text of a cited case and verifies that a quote
    appears exactly (or approximately) as stated. Essential for maintaining
    academic integrity in legal scholarship.

    Args:
        quote: The quote to verify (e.g., "Congress shall make no law...")
        citation: The citation (e.g., "410 U.S. 113" or "Roe v. Wade")
        pinpoint: Optional pinpoint citation (e.g., "at 153")

    Returns:
        Dictionary containing:
        - found: Boolean indicating if quote was found
        - exact_match: Boolean indicating if quote matched exactly
        - similarity: Float 0-1 similarity score (1.0 = exact)
        - matches_found: Number of matches found
        - best_match: Details of the best match including context
        - warnings: List of any issues found
        - recommendation: Guidance on quote validity

    Example:
        >>> await verify_quote(
        ...     "The right of privacy is fundamental",
        ...     "410 U.S. 113"
        ... )
        {
            "found": True,
            "exact_match": True,
            "similarity": 1.0,
            "best_match": {
                "context_before": "...Court has held that...",
                "matched_text": "The right of privacy is fundamental",
                "context_after": "...and applies to..."
            }
        }
    """
    return await verify_quote_impl(quote, citation, pinpoint, request_id=request_id)


@verification_server.tool()
async def batch_verify_quotes(
    quotes: list[dict[str, str]],
    request_id: str | None = None,
) -> dict[str, Any]:
    """Verify multiple quotes in a single batch operation.

    Useful for validating all citations in a law review article or brief.

    Args:
        quotes: List of quote dictionaries, each containing:
            - quote: The quote text
            - citation: The citation
            - pinpoint: Optional pinpoint (e.g., "at 153")

    Returns:
        Dictionary containing:
        - total_quotes: Total number of quotes processed
        - verified: Number of quotes found
        - exact_matches: Number of exact matches
        - fuzzy_matches: Number of approximate matches
        - not_found: Number of quotes not found
        - errors: Number of errors encountered
        - results: List of individual verification results

    Example:
        >>> await batch_verify_quotes([
        ...     {"quote": "Equal protection...", "citation": "347 U.S. 483"},
        ...     {"quote": "Congress shall...", "citation": "410 U.S. 113"}
        ... ])
        {
            "total_quotes": 2,
            "verified": 2,
            "exact_matches": 2,
            "results": [...]
        }
    """
    return await batch_verify_quotes_impl(quotes, request_id=request_id)
