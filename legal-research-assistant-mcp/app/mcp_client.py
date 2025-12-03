"""Client for communicating with CourtListener API.

This module provides a client for accessing CourtListener data directly through their API.
While we call it an MCP client for architectural clarity, it communicates with the CourtListener
API directly since MCP-to-MCP communication patterns are still evolving.
"""

import asyncio
import logging
from typing import Any

import httpx

from app.cache import CacheType, get_cache_manager
from app.logging_utils import log_event, log_operation
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class CourtListenerClient:
    """Client for CourtListener API access."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the CourtListener client."""

        self.settings = settings or get_settings()
        self.base_url = self.settings.courtlistener_base_url.rstrip("/") + "/"
        self.api_key = self.settings.courtlistener_api_key
        self.retry_attempts = max(1, self.settings.courtlistener_retry_attempts)
        self.backoff = self.settings.courtlistener_retry_backoff
        self.cache_manager = get_cache_manager()

        self.client = httpx.AsyncClient(
            base_url=self.base_url, timeout=self.settings.courtlistener_timeout
        )

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

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Perform an HTTP request with retry and backoff."""

        last_exc: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                should_retry = attempt < self.retry_attempts and (status is None or status >= 500)

                logger.warning(
                    "CourtListener request failed (attempt %s/%s): %s", attempt, self.retry_attempts, exc
                )

                if not should_retry:
                    logger.error("CourtListener request failed without remaining retries")
                    raise

                backoff_time = self.backoff * (2 ** (attempt - 1))
                await asyncio.sleep(backoff_time)

        if last_exc:
            raise last_exc
        raise RuntimeError("Request failed without raising an exception")

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
            # Check cache
            cached_result = self.cache_manager.get(CacheType.SEARCH, params)
            if cached_result is not None:
                return cached_result

            try:
                response = await self._request(
                    "GET",
                    "search/",
                    params=params,
                    headers=self._get_headers(),
                )
                result = response.json()

                # Write cache
                self.cache_manager.set(CacheType.SEARCH, params, result)

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
        cache_key = {"opinion_id": opinion_id}

        # Check cache
        cached_opinion = self.cache_manager.get(CacheType.METADATA, cache_key)
        if cached_opinion:
            return cached_opinion

        with log_operation(
            logger,
            tool_name="get_opinion",
            request_id=request_id,
            query_params=cache_key,
            event="courtlistener_get_opinion",
        ):
            try:
                response = await self._request(
                    "GET",
                    f"opinions/{opinion_id}/",
                    headers=self._get_headers(),
                )
                data = response.json()

                # Write cache
                self.cache_manager.set(CacheType.METADATA, cache_key, data)

                log_event(
                    logger,
                    "Opinion retrieved",
                    tool_name="get_opinion",
                    request_id=request_id,
                    query_params=cache_key,
                )
                return data
            except httpx.HTTPError as e:
                log_event(
                    logger,
                    f"Error fetching opinion {opinion_id}: {e}",
                    level=logging.ERROR,
                    tool_name="get_opinion",
                    request_id=request_id,
                    query_params=cache_key,
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
        cache_key = {"opinion_id": opinion_id, "field": "full_text"}

        # Check cache
        cached_text = self.cache_manager.get(CacheType.TEXT, cache_key)
        if cached_text:
            return cached_text

        with log_operation(
            logger,
            tool_name="get_opinion_full_text",
            request_id=request_id,
            query_params={"opinion_id": opinion_id},
            event="courtlistener_full_text",
        ):
            try:
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
                        # Write cache
                        self.cache_manager.set(CacheType.TEXT, cache_key, text)
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
            except Exception as e:
                log_event(
                    logger,
                    f"Error getting full text for opinion {opinion_id}: {e}",
                    level=logging.ERROR,
                    tool_name="get_opinion_full_text",
                    request_id=request_id,
                    query_params={"opinion_id": opinion_id},
                    event="courtlistener_full_text_error",
                )
                raise

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

        # lookup_citation is essentially a search, so we could cache it,
        # but the logic inside performs post-processing on search results.
        # We should cache the underlying search call if possible, or just cache the result here.
        # Given we have CacheType.SEARCH, let's cache the final result.

        cache_key = {"citation_lookup": citation}
        cached_result = self.cache_manager.get(CacheType.SEARCH, cache_key)
        if cached_result:
             return cached_result

        with log_operation(
            logger,
            tool_name="lookup_citation",
            request_id=request_id,
            query_params=params,
            event="lookup_citation",
        ):
            try:
                response = await self._request(
                    "GET",
                    "search/",
                    params=params,
                    headers=self._get_headers(),
                )
                data = response.json()

                if not data.get("results"):
                    return {"error": "Citation not found", "citation": citation}

                # Try to find the case that HAS this citation (not just mentions it)
                # Look for the citation in the case's own citation list
                result_to_return = None
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
                            result_to_return = result
                            break

                if not result_to_return:
                     # Fallback: if no exact match found, return oldest result
                    log_event(
                        logger,
                        "No exact citation match, returning oldest result",
                        level=logging.WARNING,
                        tool_name="lookup_citation",
                        request_id=request_id,
                        query_params=params,
                        event="lookup_citation_fallback",
                    )
                    result_to_return = data["results"][0]

                self.cache_manager.set(CacheType.SEARCH, cache_key, result_to_return)
                return result_to_return

            except httpx.HTTPError as e:
                log_event(
                    logger,
                    f"Error looking up citation {citation}: {e}",
                    level=logging.ERROR,
                    tool_name="lookup_citation",
                    request_id=request_id,
                    query_params=params,
                    event="lookup_citation_error",
                )
                raise

    async def find_citing_cases(
        self,
        citation: str,
        limit: int = 100,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Find cases that cite a given citation.

        Args:
            citation: The citation to find citing cases for
            limit: Maximum number of citing cases to return

        Returns:
            List of citing cases with context
        """
        cache_key = {"citing_cases": citation, "limit": limit}
        cached_results = self.cache_manager.get(CacheType.SEARCH, cache_key)
        if cached_results is not None:
            return cached_results

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
            aggregated_results: list[dict[str, Any]] = []
            failed_requests: list[dict[str, Any]] = []
            warnings: list[str] = []
            confidence = 1.0

            for query in query_attempts:
                params = {
                    "q": query,
                    "type": "o",  # Opinion type
                    "order_by": "dateFiled desc",  # Most recent first
                    "hit": min(limit, 100),
                }

                try:
                    response = await self._request(
                        "GET", "search/", params=params, headers=self._get_headers()
                    )

                    data = response.json()
                    results = data.get("results", [])
                    if results:
                        aggregated_results.extend(results)
                        log_event(
                            logger,
                            "Found citing cases",
                            tool_name="find_citing_cases",
                            request_id=request_id,
                            query_params=params,
                            citation_count=len(results),
                            event="find_citing_cases_success",
                        )
                        if len(aggregated_results) >= limit:
                            break
                    else:
                        warning_msg = (
                            f"Query '{query}' yielded no results; continuing with fallback searches."
                        )
                        warnings.append(warning_msg)
                        log_event(
                            logger,
                            warning_msg,
                            level=logging.WARNING,
                            tool_name="find_citing_cases",
                            request_id=request_id,
                            query_params=params,
                            event="find_citing_cases_retry",
                        )
                except httpx.HTTPError as e:
                    status_code = (
                        e.response.status_code if isinstance(e, httpx.HTTPStatusError) else None
                    )
                    failed_requests.append(
                        {
                            "url": f"{self.base_url}search/",
                            "params": params,
                            "status": status_code,
                            "message": str(e),
                        }
                    )
                    confidence = max(confidence - 0.2, 0.3)
                    warning_msg = f"Query '{query}' failed with error: {e}; continuing with fallback searches."
                    warnings.append(warning_msg)
                    log_event(
                        logger,
                        warning_msg,
                        level=logging.ERROR,
                        tool_name="find_citing_cases",
                        request_id=request_id,
                        query_params=params,
                        event="find_citing_cases_retry_error",
                    )
                    continue

            # Deduplicate results while preserving order
            seen_ids: set[Any] = set()
            deduped_results: list[dict[str, Any]] = []
            for result in aggregated_results:
                identifier = result.get("id") or result.get("absolute_url") or id(result)
                if identifier in seen_ids:
                    continue
                seen_ids.add(identifier)
                deduped_results.append(result)

            if deduped_results:
                deduped_results = deduped_results[:limit]
                self.cache_manager.set(
                    CacheType.SEARCH,
                    cache_key,
                    {
                        "results": deduped_results,
                        "warnings": warnings,
                        "failed_requests": failed_requests,
                        "incomplete_data": bool(failed_requests),
                        "confidence": confidence,
                    },
                )

            incomplete_data = bool(failed_requests)
            if not deduped_results:
                warnings.append("No citing cases were found across all query attempts.")
                incomplete_data = True
                confidence = min(confidence, 0.5)

            log_event(
                logger,
                "Completed citing case search",
                tool_name="find_citing_cases",
                request_id=request_id,
                query_params={"citation": citation, "limit": limit},
                citation_count=len(deduped_results),
                event="find_citing_cases_complete",
            )

            return {
                "results": deduped_results,
                "warnings": warnings,
                "failed_requests": failed_requests,
                "incomplete_data": incomplete_data,
                "confidence": confidence,
            }


# Global client instance
_client: CourtListenerClient | None = None


def get_client(settings: Settings | None = None) -> CourtListenerClient:
    """Get or create the global CourtListener client.

    Returns:
        CourtListener client instance
    """
    global _client
    if _client is None:
        _client = CourtListenerClient(settings)
    return _client
