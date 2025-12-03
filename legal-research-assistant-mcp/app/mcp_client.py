"""Client for communicating with CourtListener API.

This module provides a client for accessing CourtListener data directly through their API.
While we call it an MCP client for architectural clarity, it communicates with the CourtListener
API directly since MCP-to-MCP communication patterns are still evolving.
"""

import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from app.logging_utils import log_event, log_operation

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class CourtListenerClient:
    """Client for CourtListener API access."""

    BASE_URL = "https://www.courtlistener.com/api/rest/v4/"
    TIMEOUT = 30.0

    def __init__(self) -> None:
        """Initialize the CourtListener client."""
        self.api_key = os.getenv("COURT_LISTENER_API_KEY")
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)

        if self.api_key:
            logger.info("CourtListener API key found")
        else:
            logger.warning("No CourtListener API key found - some features may be limited")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests.

        Returns:
            Headers dictionary with authentication if API key is available
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Token {self.api_key}"
        return headers

    async def search_opinions(
        self,
        q: str,
        court: str | None = None,
        case_name: str | None = None,
        judge: str | None = None,
        filed_after: str | None = None,
        filed_before: str | None = None,
        cited_gt: int | None = None,
        cited_lt: int | None = None,
        order_by: str | None = None,
        limit: int = 20,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Search for legal opinions.

        Args:
            q: Search query string
            court: Court identifier (e.g., 'scotus', 'ca9')
            case_name: Case name to search for
            judge: Judge name to search for
            filed_after: Date in YYYY-MM-DD format
            filed_before: Date in YYYY-MM-DD format
            cited_gt: Minimum citation count
            cited_lt: Maximum citation count
            order_by: Field to order by (e.g., 'dateFiled desc', 'score desc')
            limit: Maximum number of results

        Returns:
            Dictionary with search results
        """
        params: dict[str, Any] = {
            "q": q,
            "type": "o",  # Opinion type for V4 API
            "order_by": order_by or "score desc",
        }

        if court:
            params["court"] = court
        if case_name:
            params["case_name"] = case_name
        if judge:
            params["judge"] = judge
        if filed_after:
            params["filed_after"] = filed_after
        if filed_before:
            params["filed_before"] = filed_before
        if cited_gt is not None:
            params["cited_gt"] = cited_gt
        if cited_lt is not None:
            params["cited_lt"] = cited_lt

        # Use 'hit' parameter like the official MCP
        params["hit"] = min(limit, 100)

        with log_operation(
            logger,
            tool_name="search_opinions",
            request_id=request_id,
            query_params=params,
            event="courtlistener_search",
        ):
            try:
                response = await self.client.get(
                    f"{self.BASE_URL}search/",
                    params=params,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                result = response.json()
                log_event(
                    logger,
                    "Opinion search completed",
                    tool_name="search_opinions",
                    request_id=request_id,
                    query_params=params,
                    citation_count=len(result.get("results", [])),
                )
                return result
            except httpx.HTTPError as e:
                log_event(
                    logger,
                    f"Error searching opinions: {e}",
                    level=logging.ERROR,
                    tool_name="search_opinions",
                    request_id=request_id,
                    query_params=params,
                    event="courtlistener_search_error",
                )
                raise

    async def get_opinion(
        self, opinion_id: int, request_id: str | None = None
    ) -> dict[str, Any]:
        """Get detailed information about a specific opinion.

        Args:
            opinion_id: The CourtListener opinion ID

        Returns:
            Dictionary with opinion details including full text
        """
        with log_operation(
            logger,
            tool_name="get_opinion",
            request_id=request_id,
            query_params={"opinion_id": opinion_id},
            event="courtlistener_get_opinion",
        ):
            try:
                response = await self.client.get(
                    f"{self.BASE_URL}opinions/{opinion_id}/",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                log_event(
                    logger,
                    "Opinion retrieved",
                    tool_name="get_opinion",
                    request_id=request_id,
                    query_params={"opinion_id": opinion_id},
                )
                return response.json()
            except httpx.HTTPError as e:
                log_event(
                    logger,
                    f"Error fetching opinion {opinion_id}: {e}",
                    level=logging.ERROR,
                    tool_name="get_opinion",
                    request_id=request_id,
                    query_params={"opinion_id": opinion_id},
                    event="courtlistener_get_opinion_error",
                )
                raise

    async def get_opinion_full_text(
        self, opinion_id: int, request_id: str | None = None
    ) -> str:
        """Get the full text of a specific opinion.

        Args:
            opinion_id: The CourtListener opinion ID

        Returns:
            Full text of the opinion (plain text format)
        """
        with log_operation(
            logger,
            tool_name="get_opinion_full_text",
            request_id=request_id,
            query_params={"opinion_id": opinion_id},
            event="courtlistener_full_text",
        ):
            opinion = await self.get_opinion(opinion_id, request_id=request_id)

            # Try different text fields in order of preference
            text_fields = [
                "plain_text",  # Plain text version (most useful)
                "html_lawbox",  # HTML with citations
                "html",  # Standard HTML
                "html_columbia",  # Columbia HTML
                "html_anon_2020",  # Anonymized HTML
            ]

            for field in text_fields:
                if opinion.get(field):
                    text = opinion[field]
                    log_event(
                        logger,
                        f"Retrieved {len(text)} chars of text from field '{field}'",
                        tool_name="get_opinion_full_text",
                        request_id=request_id,
                        query_params={"opinion_id": opinion_id},
                        event="courtlistener_full_text",
                    )
                    return text

            # Fallback to empty string if no text available
            log_event(
                logger,
                f"No text content found for opinion {opinion_id}",
                level=logging.WARNING,
                tool_name="get_opinion_full_text",
                request_id=request_id,
                query_params={"opinion_id": opinion_id},
                event="courtlistener_full_text_missing",
            )
            return ""

    async def lookup_citation(
        self, citation: str, request_id: str | None = None
    ) -> dict[str, Any]:
        """Look up a case by citation.

        Args:
            citation: Legal citation (e.g., "410 U.S. 113")

        Returns:
            Dictionary with case information
        """
        params = {
            "q": f'"{citation}"',
            "type": "o",  # Opinion type
            "order_by": "dateFiled asc",  # Oldest first (original case, not citing cases)
            "hit": 20,  # Get more results to find the right one
        }

        with log_operation(
            logger,
            tool_name="lookup_citation",
            request_id=request_id,
            query_params=params,
            event="lookup_citation",
        ):
            response = await self.client.get(
                f"{self.BASE_URL}search/",
                params=params,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("results"):
                return {"error": "Citation not found", "citation": citation}

            # Try to find the case that HAS this citation (not just mentions it)
            # Look for the citation in the case's own citation list
            for result in data["results"]:
                case_citations = result.get("citation", [])
                if isinstance(case_citations, list):
                    # Normalize citations for comparison
                    normalized_citations = [c.replace(" ", "").lower() for c in case_citations]
                    target = citation.replace(" ", "").lower()

                    if any(target in nc or nc in target for nc in normalized_citations):
                        log_event(
                            logger,
                            "Found matching case",
                            tool_name="lookup_citation",
                            request_id=request_id,
                            query_params=params,
                            event="lookup_citation_match",
                        )
                        return result

            # Fallback: if no exact match found, return oldest result
            # (likely the original case)
            log_event(
                logger,
                "No exact citation match, returning oldest result",
                level=logging.WARNING,
                tool_name="lookup_citation",
                request_id=request_id,
                query_params=params,
                event="lookup_citation_fallback",
            )
            return data["results"][0]

    async def find_citing_cases(
        self,
        citation: str,
        limit: int = 100,
        request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find cases that cite a given citation.

        Args:
            citation: The citation to find citing cases for
            limit: Maximum number of citing cases to return

        Returns:
            List of citing cases with context
        """
        query_attempts = [
            f'"{citation}"',  # Simple quoted search - finds cases mentioning citation
            citation,  # Unquoted
        ]

        with log_operation(
            logger,
            tool_name="find_citing_cases",
            request_id=request_id,
            query_params={"citation": citation, "limit": limit},
            event="find_citing_cases",
        ):
            for query in query_attempts:
                params = {
                    "q": query,
                    "type": "o",  # Opinion type
                    "order_by": "dateFiled desc",  # Most recent first
                    "hit": min(limit, 100),
                }

                response = await self.client.get(
                    f"{self.BASE_URL}search/",
                    params=params,
                    headers=self._get_headers(),
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    log_event(
                        logger,
                        "Found citing cases",
                        tool_name="find_citing_cases",
                        request_id=request_id,
                        query_params=params,
                        citation_count=len(results),
                        event="find_citing_cases_success",
                    )
                    return results
                else:
                    log_event(
                        logger,
                        f"Query '{query}' failed with status {response.status_code}, trying next...",
                        level=logging.WARNING,
                        tool_name="find_citing_cases",
                        request_id=request_id,
                        query_params=params,
                        event="find_citing_cases_retry",
                    )
                    continue

            # If all attempts failed, return empty list with log
            log_event(
                logger,
                f"All query attempts failed for citation: {citation}",
                level=logging.ERROR,
                tool_name="find_citing_cases",
                request_id=request_id,
                query_params={"citation": citation, "limit": limit},
                event="find_citing_cases_error",
            )
            return []


# Global client instance
_client: CourtListenerClient | None = None


def get_client() -> CourtListenerClient:
    """Get or create the global CourtListener client.

    Returns:
        CourtListener client instance
    """
    global _client
    if _client is None:
        _client = CourtListenerClient()
    return _client
