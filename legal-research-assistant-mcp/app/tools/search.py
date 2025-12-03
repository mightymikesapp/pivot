"""Semantic search tool for legal cases.

This module implements the "Smart Scout" strategy:
1. Fetch candidates from CourtListener (broad keyword search)
2. Fetch full text for candidates
3. Embed and store in local vector store
4. Perform semantic search to re-rank and find best matches
"""

import logging
from typing import Any, Optional

from fastmcp import FastMCP

from app.analysis.search.vector_store import LegalVectorStore
from app.mcp_client import get_client

# Initialize tool
search_server = FastMCP("Legal Research Search")

_vector_store: Optional[LegalVectorStore] = None


def get_vector_store() -> LegalVectorStore:
    """Lazily initialize and return the LegalVectorStore instance."""
    global _vector_store

    if _vector_store is None:
        # Use a data directory in the project root
        _vector_store = LegalVectorStore(persistence_path="./data/chroma_db")

    return _vector_store

logger = logging.getLogger(__name__)


@search_server.tool()
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
    # We ask for more results than the user wants (3x) to have a good pool for re-ranking
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
    # Identify which cases need full text fetching
    # We check if they are already in the store (optimization)
    # Note: ChromaDB doesn't expose a cheap "exists" check easily for a list,
    # so we'll just try to fetch full text for all and upsert.
    # The vector store handles upserts (updates existing).

    documents = []
    metadatas = []
    ids = []

    processed_count = 0
    full_text_fetches = 0

    # Check which cases are already in the store to avoid re-fetching/embedding
    candidate_ids = [str(c["id"]) for c in candidates]
    existing_records = vector_store.collection.get(ids=candidate_ids, include=[])
    existing_ids = set(existing_records["ids"]) if existing_records else set()

    for case in candidates:
        case_id = str(case["id"])

        # Skip if already in store
        if case_id in existing_ids:
            continue

        # We need full text for embedding
        # Try to get it from cache/API
        try:
            full_text = await client.get_opinion_full_text(int(case_id))
            if not full_text:
                continue

            full_text_fetches += 1

            # Prepare metadata
            metadata = {
                "case_name": case.get("caseName", "Unknown"),
                "citation": case.get("citation", [""])[0] if case.get("citation") else "",
                "date_filed": case.get("dateFiled", ""),
                "court": case.get("court", ""),
                "original_score": case.get("score", 0.0),
            }

            # Add to batch
            documents.append(full_text)
            metadatas.append(metadata)
            ids.append(case_id)
            processed_count += 1

        except Exception as e:
            logger.warning(f"Failed to process case {case_id}: {e}")
            continue

    # Upsert to vector store
    if documents:
        logger.info(f"Step 3: Indexing {len(documents)} new cases")
        vector_store.add_documents(documents, metadatas, ids)

    # Step 4: Semantic Search (Re-ranking)
    logger.info("Step 4: Running semantic search")
    results = vector_store.search(query, limit=limit)

    # Step 5: Format Results
    formatted_results = []

    # Chroma returns lists of lists (one list per query)
    if results["ids"] and results["ids"][0]:
        num_results = len(results["ids"][0])
        for i in range(num_results):
            formatted_results.append({
                "case_name": results["metadatas"][0][i].get("case_name"),
                "citation": results["metadatas"][0][i].get("citation"),
                "similarity_score": 1.0 - results["distances"][0][i], # Distance to similarity
                "date_filed": results["metadatas"][0][i].get("date_filed"),
                "court": results["metadatas"][0][i].get("court"),
                "id": results["ids"][0][i],
                # Include a snippet of the matching text if we had it,
                # but Chroma returns the whole document in 'documents' which might be huge.
                # We'll just return metadata for the list view.
            })

    return {
        "query": query,
        "results": formatted_results,
        "stats": {
            "candidates_found": len(candidates),
            "full_texts_fetched": full_text_fetches,
            "indexed_count": processed_count,
            "total_library_size": vector_store.count()
        }
    }


@search_server.tool()
def purge_memory() -> str:
    """Clear the local semantic search library (memory).

    Use this to free up disk space or start fresh.
    """
    vector_store = get_vector_store()
    count_before = vector_store.count()
    vector_store.clear()
    return f"Memory purged. Removed {count_before} cases from local library."


@search_server.tool()
def get_library_stats() -> dict[str, Any]:
    """Get statistics about the local semantic search library."""
    vector_store = get_vector_store()
    return vector_store.get_stats()
