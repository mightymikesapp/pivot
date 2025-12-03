"""Treatment analysis tools for legal research.

This module provides MCP tools for analyzing case treatment and validity,
serving as a free alternative to Shepard's Citations and KeyCite.
"""

import logging

from fastmcp import FastMCP

from app.analysis.treatment_classifier import TreatmentClassifier
from app.config import settings
from app.logging_config import tool_logging
from app.logging_utils import log_event, log_operation
from app.mcp_client import get_client
from app.types import CourtListenerCase, TreatmentResult

logger = logging.getLogger(__name__)

# Initialize classifier
classifier = TreatmentClassifier()


# Implementation functions (can be called directly or via MCP tools)
async def check_case_validity_impl(
    citation: str, request_id: str | None = None
) -> TreatmentResult:
    """Check if a case is still good law by analyzing citing cases.

    This provides a free alternative to Shepard's Citations and KeyCite by:
    1. Finding all cases that cite the target case
    2. Analyzing treatment signals (overruled, questioned, followed, etc.)
    3. Providing a confidence-scored validity assessment

    Args:
        citation: Legal citation to check (e.g., "410 U.S. 113" or "Roe v. Wade")

    Returns:
        Dictionary containing validity assessment and analysis
    """
    client = get_client()

    with log_operation(
        logger,
        tool_name="check_case_validity",
        request_id=request_id,
        query_params={"citation": citation},
        event="check_case_validity",
    ):
        # Step 1: Look up the target case
        target_case = await client.lookup_citation(citation, request_id=request_id)

        if "error" in target_case:
            return {
                "error": f"Could not find case: {target_case.get('error')}",
                "citation": citation,
            }

        # Step 2: Find citing cases
        citing_cases_result = await client.find_citing_cases(
            citation,
            limit=settings.max_citing_cases,
            request_id=request_id,
        )
        citing_cases: list[CourtListenerCase] = citing_cases_result["results"]
        log_event(
            logger,
            "Citing cases located",
            tool_name="check_case_validity",
            request_id=request_id,
            query_params={"citation": citation},
            citation_count=len(citing_cases),
            extra_context={
                "incomplete_data": citing_cases_result.get("incomplete_data", False),
                "warnings": citing_cases_result.get("warnings", []),
            },
            event="citing_cases_fetched",
        )

        # Step 3: First pass - analyze all cases with snippets
        initial_treatments: list[tuple[CourtListenerCase, TreatmentAnalysis]] = []
        for citing_case in citing_cases:
            analysis = classifier.classify_treatment(citing_case, citation)
            initial_treatments.append((citing_case, analysis))

        # Step 4: Identify cases needing full text analysis
        strategy = settings.fetch_full_text_strategy
        cases_for_full_text = []

        for citing_case, initial_analysis in initial_treatments:
            if classifier.should_fetch_full_text(initial_analysis, strategy):
                cases_for_full_text.append((citing_case, initial_analysis))

        log_event(
            logger,
            "Full text selection complete",
            tool_name="check_case_validity",
            request_id=request_id,
            query_params={"citation": citation},
            extra_context={
                "strategy": strategy,
                "selected_for_full_text": len(cases_for_full_text),
            },
        )

        # Step 5: Fetch full text and re-analyze (limited by max_full_text_fetches)
        treatments: list[TreatmentAnalysis] = []
        full_text_count = 0

        for citing_case, initial_analysis in initial_treatments:
            # Check if this case needs full text and we haven't hit the limit
            needs_full_text = any(
                c is citing_case for c, _ in cases_for_full_text
            ) and full_text_count < settings.max_full_text_fetches

            if needs_full_text:
                try:
                    # Extract opinion IDs from the case
                    opinion_ids = [
                        op.get("id")
                        for op in citing_case.get("opinions", [])
                        if op.get("id")
                    ]

                    if opinion_ids:
                        # Fetch full text for first opinion
                        opinion_id = opinion_ids[0]

                        full_text = await client.get_opinion_full_text(
                            opinion_id, request_id=request_id
                        )

                        if full_text:
                            # Re-analyze with full text
                            enhanced_analysis = classifier.classify_treatment(
                                citing_case, citation, full_text=full_text
                            )
                            treatments.append(enhanced_analysis)
                            full_text_count += 1
                            log_event(
                                logger,
                                "Enhanced analysis with full text",
                                tool_name="check_case_validity",
                                request_id=request_id,
                                query_params={"citation": citation},
                                event="full_text_analysis",
                            )
                        else:
                            # No full text available, use initial analysis
                            treatments.append(initial_analysis)
                    else:
                        # No opinion IDs, use initial analysis
                        treatments.append(initial_analysis)

                except Exception as e:
                    log_event(
                        logger,
                        f"Failed to fetch full text: {e}, using snippet analysis",
                        level=logging.WARNING,
                        tool_name="check_case_validity",
                        request_id=request_id,
                        query_params={"citation": citation},
                        event="full_text_error",
                    )
                    treatments.append(initial_analysis)
            else:
                # Use initial analysis
                treatments.append(initial_analysis)

        log_event(
            logger,
            "Completed analysis",
            tool_name="check_case_validity",
            request_id=request_id,
            query_params={"citation": citation},
            citation_count=len(treatments),
            extra_context={"full_text_count": full_text_count},
        )

        # Step 6: Aggregate treatments
        if treatments:
            aggregated = classifier.aggregate_treatments(treatments, citation)

            # Build warnings list
            warnings = []
            for neg_treatment in aggregated.negative_treatments:
                for signal in neg_treatment.signals_found[:2]:  # Top 2 signals
                    warnings.append(
                        {
                            "signal": signal.signal,
                            "case_name": neg_treatment.case_name,
                            "citation": neg_treatment.citation,
                            "date_filed": neg_treatment.date_filed,
                            "excerpt": signal.context,
                        }
                    )

            base_confidence = aggregated.confidence
            if citing_cases_result.get("incomplete_data"):
                base_confidence = max(base_confidence * 0.8, 0.3)

            return {
                "citation": citation,
                "case_name": target_case.get("caseName", "Unknown"),
                "is_good_law": aggregated.is_good_law,
                "confidence": round(base_confidence, 2),
                "summary": aggregated.summary,
                "total_citing_cases": aggregated.total_citing_cases,
                "positive_count": aggregated.positive_count,
                "negative_count": aggregated.negative_count,
                "neutral_count": aggregated.neutral_count,
                "unknown_count": aggregated.unknown_count,
                "warnings": warnings + citing_cases_result.get("warnings", []),
                "failed_requests": citing_cases_result.get("failed_requests", []),
                "incomplete_data": citing_cases_result.get("incomplete_data", False),
                "recommendation": (
                    "Manual review recommended"
                    if not aggregated.is_good_law or aggregated.negative_count > 0
                    else "Case appears reliable"
                ),
            }
        else:
            # No citing cases found
            return {
                "citation": citation,
                "case_name": target_case.get("caseName", "Unknown"),
                "is_good_law": True,
                "confidence": 0.5,
                "summary": "No citing cases found. Unable to determine treatment.",
                "total_citing_cases": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "unknown_count": 0,
                "warnings": citing_cases_result.get("warnings", []),
                "failed_requests": citing_cases_result.get("failed_requests", []),
                "incomplete_data": citing_cases_result.get("incomplete_data", True),
                "recommendation": "Case has not been cited. Validity uncertain.",
            }

    # log_operation will capture errors


async def get_citing_cases_impl(
    citation: str,
    treatment_filter: str | None = None,
    limit: int = 20,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Get cases that cite a given citation, optionally filtered by treatment type.

    Args:
        citation: The citation to find citing cases for
        treatment_filter: Optional filter: "positive", "negative", or "neutral"
        limit: Maximum number of results to return (default 20)

    Returns:
        Dictionary containing citing cases with treatment analysis
    """
    client = get_client()

    with log_operation(
        logger,
        tool_name="get_citing_cases",
        request_id=request_id,
        query_params={"citation": citation, "treatment_filter": treatment_filter, "limit": limit},
        event="get_citing_cases",
    ):
        # Find citing cases
        citing_cases_result = await client.find_citing_cases(
            citation, limit=limit, request_id=request_id
        )
        citing_cases = citing_cases_result["results"]

        # Analyze treatment
        treatments = []
        for citing_case in citing_cases:
            analysis = classifier.classify_treatment(citing_case, citation)

            # Apply filter if specified
            if treatment_filter:
                filter_lower = treatment_filter.lower()
                if filter_lower == "positive" and analysis.treatment_type.value != "positive":
                    continue
                elif filter_lower == "negative" and analysis.treatment_type.value != "negative":
                    continue
                elif filter_lower == "neutral" and analysis.treatment_type.value != "neutral":
                    continue

            treatments.append(
                {
                    "case_name": analysis.case_name,
                    "citation": analysis.citation,
                    "date_filed": analysis.date_filed,
                    "treatment": analysis.treatment_type.value,
                    "confidence": round(analysis.confidence, 2),
                    "signals": [s.signal for s in analysis.signals_found],
                    "excerpt": analysis.excerpt,
                }
            )

        log_event(
            logger,
            "Citing cases analyzed",
            tool_name="get_citing_cases",
            request_id=request_id,
            query_params={"citation": citation, "treatment_filter": treatment_filter},
            citation_count=len(treatments),
        )

        return {
            "citation": citation,
            "total_found": len(citing_cases),
            "citing_cases": treatments,
            "filter_applied": treatment_filter,
            "incomplete_data": citing_cases_result.get("incomplete_data", False),
            "warnings": citing_cases_result.get("warnings", []),
            "failed_requests": citing_cases_result.get("failed_requests", []),
        }


# Create treatment tools server
treatment_server = FastMCP(
    name="Treatment Analysis Tools",
    instructions="Tools for analyzing case treatment and validity (Shepardizing alternative)",
)


@treatment_server.tool()
@tool_logging("check_case_validity")
async def check_case_validity(
    citation: str, request_id: str | None = None
) -> TreatmentResult:
    """Check if a case is still good law by analyzing citing cases.

    This tool provides a free alternative to Shepard's Citations and KeyCite by:
    1. Finding all cases that cite the target case
    2. Analyzing treatment signals (overruled, questioned, followed, etc.)
    3. Providing a confidence-scored validity assessment

    Args:
        citation: Legal citation to check (e.g., "410 U.S. 113" or "Roe v. Wade")

    Returns:
        Dictionary containing:
        - is_good_law: Boolean indicating if case appears to be good law
        - confidence: Float 0-1 confidence score
        - summary: Human-readable summary
        - total_citing_cases: Number of citing cases analyzed
        - positive_count: Number of positive treatments
        - negative_count: Number of negative treatments
        - neutral_count: Number of neutral citations
        - negative_treatments: List of cases with negative treatment
        - warnings: List of specific warnings if validity is questionable

    Example:
        >>> await check_case_validity("410 U.S. 113")
        {
            "is_good_law": False,
            "confidence": 0.95,
            "summary": "Case overruled by Dobbs v. Jackson...",
            "negative_count": 1,
            ...
        }
    """
    return await check_case_validity_impl(citation, request_id=request_id)


@treatment_server.tool()
@tool_logging("get_citing_cases")
async def get_citing_cases(
    citation: str,
    treatment_filter: str | None = None,
    limit: int = 20,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Get cases that cite a given citation, optionally filtered by treatment type.

    Args:
        citation: The citation to find citing cases for
        treatment_filter: Optional filter: "positive", "negative", or "neutral"
        limit: Maximum number of results to return (default 20)

    Returns:
        Dictionary containing:
        - citation: The target citation
        - total_found: Total number of citing cases
        - citing_cases: List of citing cases with treatment analysis
        - filter_applied: The filter that was applied, if any

    Example:
        >>> await get_citing_cases("410 U.S. 113", treatment_filter="negative")
        {
            "citation": "410 U.S. 113",
            "total_found": 50,
            "citing_cases": [...],
            "filter_applied": "negative"
        }
    """
    return await get_citing_cases_impl(
        citation, treatment_filter, limit, request_id=request_id
    )
