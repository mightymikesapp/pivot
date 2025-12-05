"""Semantic search tool for legal cases.

This module implements the "Smart Scout" strategy:
1. Fetch candidates from CourtListener (broad keyword search)
2. Fetch full text for candidates
3. Embed and store in local vector store
4. Perform semantic search to re-rank and find best matches
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from app.logging_config import tool_logging
from app.mcp_client import get_client
from app.mcp_types import ToolPayload

if TYPE_CHECKING:  # pragma: no cover
    from app.analysis.search.vector_store import LegalVectorStore

# Initialize tool
search_server: FastMCP[ToolPayload] = FastMCP("Legal Research Search")

_vector_store_instance: "LegalVectorStore | None" = None


def get_vector_store() -> LegalVectorStore:
    """Lazily initialize and return the LegalVectorStore instance.
    
    This allows tests to inject a mock before this is called.
    """
    global _vector_store_instance

    if _vector_store_instance is None:
        # Runtime import to avoid circular dependencies or initialization costs
        from app.analysis.search.vector_store import LegalVectorStore

        _vector_store_instance = LegalVectorStore(persistence_path="./data/chroma_db")

    return _vector_store_instance


def set_vector_store(store: LegalVectorStore) -> None:
    """Override the vector store instance (for testing)."""
    global _vector_store_instance
    _vector_store_instance = store


logger = logging.getLogger(__name__)


async def _fetch_full_text_safe(client: Any, case_id: str) -> tuple[str, str | None]:
    """Helper to fetch full text safely and return (id, text)."""
    try:
        full_text = await client.get_opinion_full_text(int(case_id))
        return case_id, full_text
    except Exception as e:
        logger.warning(f"Failed to fetch text for case {case_id}: {e}")
        return case_id, None


@search_server.tool()
@tool_logging("semantic_search")
async def semantic_search(query: str, limit: int = 10) -> dict[str, Any]:
    """Perform a semantic search for legal cases.

    Uses a "Smart Scout" strategy:
    1. Broadly searches CourtListener API for candidates
    2. Fetches full text and indexes them locally
    3. Performs vector similarity search to find conceptually relevant cases

    Args:
        query: Conceptual search query (e.g., "landlord liability for dog bites")
        limit: Number of results to return

    Returns:
        Dictionary with re-ranked search results and statistics
    """
    client = get_client()
    vector_store = get_vector_store()

    # Step 1: Broad Sweep - Search CourtListener
    candidate_limit = max(20, limit * 3)
    logger.info(f"Step 1: Fetching {candidate_limit} candidates for query: {query}")

    search_results = await client.search_opinions(
        q=query,
        limit=candidate_limit,
        order_by="score desc"
    )

    candidates = search_results.get("results", [])
    logger.info(f"Found {len(candidates)} candidates")

    # Step 2 & 3: Enrichment & Indexing
    candidate_ids = [str(c["id"]) for c in candidates]
    
    # Check existing to avoid re-fetching
    # Note: In a real app, we'd want a bulk check method on the store
    # For now, we'll assume we need to check validity or existence
    # Chroma doesn't have a cheap "exists" for a list easily exposed in this wrapper,
    # but we can query IDs.
    
    # Optimization: Fetch existing IDs first
    existing_records = vector_store.collection.get(ids=candidate_ids, include=[])
    existing_ids = set(existing_records["ids"]) if existing_records else set()
    
    cases_to_fetch = []
    case_map = {str(c["id"]): c for c in candidates}
    
    for cid in candidate_ids:
        if cid not in existing_ids:
            cases_to_fetch.append(cid)

    logger.info(f"Need to fetch full text for {len(cases_to_fetch)} new cases")

    # Batch fetch full texts
    full_text_fetches = 0
    documents = []
    metadatas = []
    ids = []
    
    # Fetch in batches of 5 to respect rate limits gracefully
    batch_size = 5
    for i in range(0, len(cases_to_fetch), batch_size):
        batch_ids = cases_to_fetch[i : i + batch_size]
        tasks = [_fetch_full_text_safe(client, cid) for cid in batch_ids]
        results = await asyncio.gather(*tasks)
        
        for cid, text in results:
            if text:
                full_text_fetches += 1
                case = case_map[cid]
                
                metadata = {
                    "case_name": case.get("caseName", "Unknown"),
                    "citation": case.get("citation", [""])[0] if case.get("citation") else "",
                    "date_filed": case.get("dateFiled", ""),
                    "court": case.get("court", ""),
                    "original_score": case.get("score", 0.0),
                }
                
                documents.append(text)
                metadatas.append(metadata)
                ids.append(cid)

    # Upsert to vector store
    if documents:
        logger.info(f"Step 3: Indexing {len(documents)} new cases")
        vector_store.add_documents(documents, metadatas, ids)

    # Step 4: Semantic Search (Re-ranking)
    logger.info("Step 4: Running semantic search")
    results = vector_store.search(query, limit=limit)

    # Step 5: Format Results
    formatted_results = []

    if results["ids"] and results["ids"][0]:
        num_results = len(results["ids"][0])
        for i in range(num_results):
            formatted_results.append({
                "case_name": results["metadatas"][0][i].get("case_name"),
                "citation": results["metadatas"][0][i].get("citation"),
                "similarity_score": 1.0 - results["distances"][0][i],
                "date_filed": results["metadatas"][0][i].get("date_filed"),
                "court": results["metadatas"][0][i].get("court"),
                "id": results["ids"][0][i],
            })

    return {
        "query": query,
        "results": formatted_results,
        "stats": {
            "candidates_found": len(candidates),
            "full_texts_fetched": full_text_fetches,
            "indexed_count": len(documents),
            "total_library_size": vector_store.count()
        }
    }


@search_server.tool()
@tool_logging("purge_memory")
def purge_memory() -> str:
    """Clear the local semantic search library (memory).

    Use this to free up disk space or start fresh.
    """
    vector_store = get_vector_store()
    count_before = vector_store.count()
    vector_store.clear()
    return f"Memory purged. Removed {count_before} cases from local library."


@search_server.tool()
@tool_logging("get_library_stats")
def get_library_stats() -> dict[str, Any]:
    """Get statistics about the local semantic search library."""
    vector_store = get_vector_store()
    return vector_store.get_stats()
