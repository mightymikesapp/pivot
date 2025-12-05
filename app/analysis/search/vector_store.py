"""Vector store for semantic search of legal cases.

This module provides a wrapper around ChromaDB to store and retrieve case embeddings.
It handles model initialization, document storage, and similarity search.
"""

import logging
import os
from pathlib import Path
from typing import Any, cast

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)


class LegalVectorStore:
    """Vector store for legal research assistant."""

    def __init__(self, persistence_path: str = "./data/chroma_db") -> None:
        """Initialize the vector store.

        Args:
            persistence_path: Path to store the database
        """
        self.persistence_path = Path(persistence_path)
        self.persistence_path.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persistence_path),
            settings=Settings(allow_reset=True, anonymized_telemetry=False),
        )

        # Use a lightweight, high-performance model suitable for CPU
        # all-MiniLM-L6-v2 is standard for this: fast, small (80MB), good quality
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Get or create the collection
        self.collection = self.client.get_or_create_collection(
            name="legal_cases",
            embedding_function=self.embedding_fn,
            metadata={"description": "Legal cases from CourtListener"},
        )

        logger.info(f"Vector store initialized at {self.persistence_path}")

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        """Add documents to the vector store.

        Args:
            documents: List of text content (e.g., case full text)
            metadatas: List of metadata dicts (e.g., case name, citation, date)
            ids: List of unique IDs (e.g., CourtListener ID)
        """
        if not documents:
            return

        logger.info(f"Adding {len(documents)} documents to vector store")
        try:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            logger.info("Documents added successfully")
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise

    def search(
        self,
        query: str,
        limit: int = 10,
        filter_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Search for similar documents.

        Args:
            query: The search query text
            limit: Maximum number of results
            filter_metadata: Optional metadata filter

        Returns:
            Dictionary containing results (ids, distances, metadatas, documents)
        """
        logger.info(f"Searching vector store for: '{query}' (limit={limit})")

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=filter_metadata,
            )
            return cast(dict[str, Any], results)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Return empty structure on failure to avoid crashing caller
            return {
                "ids": [[]],
                "distances": [[]],
                "metadatas": [[]],
                "documents": [[]],
            }

    def clear(self) -> None:
        """Clear all data from the vector store."""
        logger.warning("Clearing vector store")
        try:
            self.client.reset()
            # Re-create the collection after reset
            self.collection = self.client.get_or_create_collection(
                name="legal_cases",
                embedding_function=self.embedding_fn,
                metadata={"description": "Legal cases from CourtListener"},
            )
        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            raise

    def count(self) -> int:
        """Get total number of documents in store."""
        return cast(int, self.collection.count())

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the vector store."""
        return {
            "total_documents": self.count(),
            "persistence_path": str(self.persistence_path),
            "model": "all-MiniLM-L6-v2",
        }
