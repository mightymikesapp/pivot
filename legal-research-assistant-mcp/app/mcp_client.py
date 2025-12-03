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

        logger.info(f"Searching opinions with params: {params}")

        try:
            response = await self.client.get(
                f"{self.BASE_URL}search/",
                params=params,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error searching opinions: {e}")
            raise

    async def get_opinion(self, opinion_id: int) -> dict[str, Any]:
        """Get detailed information about a specific opinion.

        Args:
            opinion_id: The CourtListener opinion ID

        Returns:
            Dictionary with opinion details including full text
        """
        logger.info(f"Fetching opinion {opinion_id}")

        try:
            response = await self.client.get(
                f"{self.BASE_URL}opinions/{opinion_id}/",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching opinion {opinion_id}: {e}")
            raise

    async def get_opinion_full_text(self, opinion_id: int) -> str:
        """Get the full text of a specific opinion.

        Args:
            opinion_id: The CourtListener opinion ID

        Returns:
            Full text of the opinion (plain text format)
        """
        logger.info(f"Fetching full text for opinion {opinion_id}")

        try:
            opinion = await self.get_opinion(opinion_id)

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
                    logger.info(f"Retrieved {len(text)} chars of text from field '{field}'")
                    return text

            # Fallback to empty string if no text available
            logger.warning(f"No text content found for opinion {opinion_id}")
            return ""

        except httpx.HTTPError as e:
            logger.error(f"Error fetching full text for opinion {opinion_id}: {e}")
            raise

    async def lookup_citation(self, citation: str) -> dict[str, Any]:
        """Look up a case by citation.

        Args:
            citation: Legal citation (e.g., "410 U.S. 113")

        Returns:
            Dictionary with case information
        """
        logger.info(f"Looking up citation: {citation}")

        try:
            # Search for the citation
            params = {
                "q": f'"{citation}"',
                "type": "o",  # Opinion type
                "order_by": "dateFiled asc",  # Oldest first (original case, not citing cases)
                "hit": 20,  # Get more results to find the right one
            }
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
                        logger.info(f"Found matching case: {result.get('caseName')}")
                        return result

            # Fallback: if no exact match found, return oldest result
            # (likely the original case)
            logger.warning("No exact citation match, returning oldest result")
            return data["results"][0]

        except httpx.HTTPError as e:
            logger.error(f"Error looking up citation {citation}: {e}")
            raise

    async def find_citing_cases(
        self,
        citation: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Find cases that cite a given citation.

        Args:
            citation: The citation to find citing cases for
            limit: Maximum number of citing cases to return

        Returns:
            List of citing cases with context
        """
        logger.info(f"Finding cases citing: {citation}")

        try:
            # Try different query syntaxes to find citing cases
            # CourtListener v4 API syntax for citing cases
            query_attempts = [
                f'"{citation}"',  # Simple quoted search - finds cases mentioning citation
                citation,  # Unquoted
            ]

            for query in query_attempts:
                params = {
                    "q": query,
                    "type": "o",  # Opinion type
                    "order_by": "dateFiled desc",  # Most recent first
                    "hit": min(limit, 100),
                }

                logger.info(f"Trying query: {query}")

                response = await self.client.get(
                    f"{self.BASE_URL}search/",
                    params=params,
                    headers=self._get_headers(),
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    logger.info(f"Found {len(results)} results with query: {query}")
                    return results
                else:
                    logger.warning(
                        f"Query '{query}' failed with status {response.status_code}, trying next..."
                    )
                    continue

            # If all attempts failed, raise error
            logger.error(f"All query attempts failed for citation: {citation}")
            return []

        except httpx.HTTPError as e:
            logger.error(f"Error finding citing cases for {citation}: {e}")
            raise


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
