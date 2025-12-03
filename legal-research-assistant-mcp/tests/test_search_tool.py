
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from app.tools.search import semantic_search, purge_memory, get_library_stats, get_vector_store


@pytest.mark.asyncio
async def test_semantic_search():
    """Test basic semantic search functionality."""
    # Mock dependencies
    mock_client = AsyncMock()
    mock_vector_store = MagicMock()

    # Mock search results from CourtListener
    mock_client.search_opinions.return_value = {
        "results": [
            {"id": 1, "caseName": "Case A", "score": 10.0},
            {"id": 2, "caseName": "Case B", "score": 5.0}
        ]
    }

    # Mock full text fetching
    mock_client.get_opinion_full_text.side_effect = ["Full text A", "Full text B"]

    # Mock vector store search results
    mock_vector_store.search.return_value = {
        "ids": [["1", "2"]],
        "distances": [[0.1, 0.2]],
        "metadatas": [[
            {"case_name": "Case A", "citation": "1 U.S. 1"},
            {"case_name": "Case B", "citation": "2 U.S. 2"}
        ]]
    }

    with patch("app.tools.search.get_client", return_value=mock_client), \
         patch("app.tools.search.vector_store", mock_vector_store):

        result = await semantic_search.fn("query", limit=2)

        # Verify initial broad search
        mock_client.search_opinions.assert_called_once()

        # Verify full text fetching (2 calls)
        assert mock_client.get_opinion_full_text.call_count == 2

        # Verify indexing
        mock_vector_store.add_documents.assert_called_once()

        # Verify semantic search
        mock_vector_store.search.assert_called_with("query", limit=2)

        # Check result structure
        assert len(result["results"]) == 2
        assert result["results"][0]["case_name"] == "Case A"
        assert result["stats"]["full_texts_fetched"] == 2


@pytest.mark.asyncio
async def test_semantic_search_end_to_end():
    """Test complete semantic search workflow with realistic data."""
    mock_client = AsyncMock()
    mock_vector_store = MagicMock()
    mock_vector_store.count.return_value = 42

    # Simulate 5 candidates found
    candidates = [
        {
            "id": 100 + i,
            "caseName": f"Smith v. State {i}",
            "citation": [f"{i} F.3d {i}00"],
            "dateFiled": "2020-01-01",
            "court": "U.S. Court of Appeals",
            "score": 100.0 - (i * 10)
        }
        for i in range(5)
    ]

    mock_client.search_opinions.return_value = {"results": candidates}
    mock_client.get_opinion_full_text.side_effect = [
        f"Full text for case {i}" for i in range(5)
    ]

    mock_vector_store.collection.get.return_value = {"ids": []}
    mock_vector_store.search.return_value = {
        "ids": [["100", "101", "102"]],
        "distances": [[0.05, 0.10, 0.15]],
        "metadatas": [[
            {
                "case_name": "Smith v. State 0",
                "citation": "0 F.3d 000",
                "date_filed": "2020-01-01",
                "court": "U.S. Court of Appeals",
                "original_score": 100.0
            },
            {
                "case_name": "Smith v. State 1",
                "citation": "1 F.3d 100",
                "date_filed": "2020-01-01",
                "court": "U.S. Court of Appeals",
                "original_score": 90.0
            },
            {
                "case_name": "Smith v. State 2",
                "citation": "2 F.3d 200",
                "date_filed": "2020-01-01",
                "court": "U.S. Court of Appeals",
                "original_score": 80.0
            }
        ]]
    }

    with patch("app.tools.search.get_client", return_value=mock_client), \
         patch("app.tools.search.get_vector_store", return_value=mock_vector_store):

        result = await semantic_search.fn("contract breach", limit=3)

        # Verify complete workflow
        assert result["query"] == "contract breach"
        assert len(result["results"]) == 3
        assert result["stats"]["candidates_found"] == 5
        assert result["stats"]["full_texts_fetched"] == 5
        assert result["stats"]["indexed_count"] == 5
        assert result["stats"]["total_library_size"] == 42

        # Verify result formatting
        assert all("case_name" in r for r in result["results"])
        assert all("similarity_score" in r for r in result["results"])
        assert all("id" in r for r in result["results"])
        assert result["results"][0]["similarity_score"] == pytest.approx(0.95, abs=0.01)


@pytest.mark.asyncio
async def test_semantic_search_with_cache_hits():
    """Test semantic search when some documents are already in cache."""
    mock_client = AsyncMock()
    mock_vector_store = MagicMock()
    mock_vector_store.count.return_value = 100

    # Simulate 5 candidates
    candidates = [
        {"id": i, "caseName": f"Case {i}", "citation": [f"{i} U.S. {i}"], "score": 50.0}
        for i in range(1, 6)
    ]

    mock_client.search_opinions.return_value = {"results": candidates}

    # Only fetch full text for 2 of them (3 already in cache)
    mock_client.get_opinion_full_text.side_effect = ["Text 1", "Text 2"]

    # Mock that IDs 1, 2, 3 already exist in store
    mock_vector_store.collection.get.return_value = {"ids": ["1", "2", "3"]}
    mock_vector_store.search.return_value = {
        "ids": [["4", "5"]],
        "distances": [[0.1, 0.2]],
        "metadatas": [[
            {"case_name": "Case 4", "citation": "4 U.S. 4"},
            {"case_name": "Case 5", "citation": "5 U.S. 5"}
        ]]
    }

    with patch("app.tools.search.get_client", return_value=mock_client), \
         patch("app.tools.search.get_vector_store", return_value=mock_vector_store):

        result = await semantic_search.fn("test query", limit=2)

        # Verify that only new documents were fetched and indexed
        assert mock_client.get_opinion_full_text.call_count == 2
        assert result["stats"]["candidates_found"] == 5
        assert result["stats"]["full_texts_fetched"] == 2
        assert result["stats"]["indexed_count"] == 2


@pytest.mark.asyncio
async def test_semantic_search_error_handling():
    """Test semantic search error handling for various failure scenarios."""
    mock_client = AsyncMock()
    mock_vector_store = MagicMock()

    candidates = [
        {"id": 1, "caseName": "Case 1", "citation": ["1 U.S. 1"], "score": 50.0},
        {"id": 2, "caseName": "Case 2", "citation": ["2 U.S. 2"], "score": 45.0},
        {"id": 3, "caseName": "Case 3", "citation": ["3 U.S. 3"], "score": 40.0}
    ]

    mock_client.search_opinions.return_value = {"results": candidates}

    # Simulate some failures: case 1 succeeds, case 2 fails, case 3 succeeds
    mock_client.get_opinion_full_text.side_effect = [
        "Full text 1",
        Exception("API error"),
        "Full text 3"
    ]

    mock_vector_store.collection.get.return_value = {"ids": []}
    mock_vector_store.search.return_value = {
        "ids": [["1", "3"]],
        "distances": [[0.1, 0.2]],
        "metadatas": [[
            {"case_name": "Case 1", "citation": "1 U.S. 1"},
            {"case_name": "Case 3", "citation": "3 U.S. 3"}
        ]]
    }

    with patch("app.tools.search.get_client", return_value=mock_client), \
         patch("app.tools.search.get_vector_store", return_value=mock_vector_store):

        result = await semantic_search.fn("error test", limit=5)

        # Should continue despite error and process 2 documents
        assert result["stats"]["indexed_count"] == 2
        assert mock_vector_store.add_documents.called
        assert len(result["results"]) == 2


@pytest.mark.asyncio
async def test_semantic_search_with_empty_results():
    """Test semantic search when no candidates or no full text is found."""
    mock_client = AsyncMock()
    mock_vector_store = MagicMock()
    mock_vector_store.count.return_value = 0

    # No candidates found
    mock_client.search_opinions.return_value = {"results": []}
    mock_vector_store.collection.get.return_value = {"ids": []}
    mock_vector_store.search.return_value = {
        "ids": [[]],
        "distances": [[]],
        "metadatas": [[]]
    }

    with patch("app.tools.search.get_client", return_value=mock_client), \
         patch("app.tools.search.get_vector_store", return_value=mock_vector_store):

        result = await semantic_search.fn("no results query", limit=5)

        assert result["stats"]["candidates_found"] == 0
        assert result["stats"]["indexed_count"] == 0
        assert len(result["results"]) == 0


@pytest.mark.asyncio
async def test_semantic_search_limit_expansion():
    """Test that candidate limit is expanded (3x) to allow for re-ranking."""
    mock_client = AsyncMock()
    mock_vector_store = MagicMock()

    mock_client.search_opinions.return_value = {"results": []}
    mock_vector_store.collection.get.return_value = {"ids": []}
    mock_vector_store.search.return_value = {
        "ids": [[]],
        "distances": [[]],
        "metadatas": [[]]
    }

    with patch("app.tools.search.get_client", return_value=mock_client), \
         patch("app.tools.search.get_vector_store", return_value=mock_vector_store):

        # Request limit=5 should request 15 candidates (max(20, 5*3) = 20)
        await semantic_search.fn("query", limit=5)

        # Verify the broad search requested at least candidate_limit
        call_args = mock_client.search_opinions.call_args
        assert call_args.kwargs["limit"] >= 15

        # Request limit=20 should request 60 candidates
        await semantic_search.fn("query", limit=20)

        call_args = mock_client.search_opinions.call_args
        assert call_args.kwargs["limit"] == 60


def test_purge_memory():
    """Test that purge_memory clears the vector store."""
    mock_vector_store = MagicMock()
    mock_vector_store.count.return_value = 50

    with patch("app.tools.search.get_vector_store", return_value=mock_vector_store):
        result = purge_memory()

        # Verify clear was called
        mock_vector_store.clear.assert_called_once()

        # Verify result message
        assert "50" in result
        assert "Memory purged" in result


def test_get_library_stats():
    """Test getting library statistics."""
    mock_vector_store = MagicMock()
    mock_vector_store.get_stats.return_value = {
        "total_documents": 150,
        "persistence_path": "/data/chroma_db",
        "model": "all-MiniLM-L6-v2"
    }

    with patch("app.tools.search.get_vector_store", return_value=mock_vector_store):
        result = get_library_stats()

        assert result["total_documents"] == 150
        assert result["persistence_path"] == "/data/chroma_db"
        assert result["model"] == "all-MiniLM-L6-v2"
        mock_vector_store.get_stats.assert_called_once()


def test_vector_store_lazy_initialization():
    """Test that vector store is lazily initialized on first access."""
    with patch("app.tools.search.vector_store", None):
        # Mock the LegalVectorStore class
        mock_store_instance = MagicMock()

        with patch("app.tools.search.LegalVectorStore", return_value=mock_store_instance) as mock_constructor:
            # Reset global vector_store
            import app.tools.search
            app.tools.search.vector_store = None

            # First call should initialize
            result1 = get_vector_store()
            assert mock_constructor.call_count == 1
            assert result1 == mock_store_instance

            # Second call should return cached instance
            result2 = get_vector_store()
            assert mock_constructor.call_count == 1  # Still 1, not called again
            assert result2 == mock_store_instance


def test_candidate_fetching_and_filtering():
    """Test candidate fetching and filtering logic."""
    mock_client = AsyncMock()
    mock_vector_store = MagicMock()

    # Create mixed candidate set
    candidates = [
        {"id": 1, "caseName": "Valid Case 1", "citation": ["1 U.S. 1"], "score": 100.0},
        {"id": 2, "caseName": "Valid Case 2", "citation": ["2 U.S. 2"], "score": 90.0},
        {"id": 3, "caseName": "Case No Text", "citation": ["3 U.S. 3"], "score": 80.0},
    ]

    mock_client.search_opinions.return_value = {"results": candidates}

    # Case 3 returns empty full text
    mock_client.get_opinion_full_text.side_effect = [
        "Full text 1",
        "Full text 2",
        None  # No full text for case 3
    ]

    mock_vector_store.collection.get.return_value = {"ids": []}
    mock_vector_store.search.return_value = {
        "ids": [["1", "2"]],
        "distances": [[0.1, 0.2]],
        "metadatas": [[
            {"case_name": "Valid Case 1", "citation": "1 U.S. 1"},
            {"case_name": "Valid Case 2", "citation": "2 U.S. 2"}
        ]]
    }

    with patch("app.tools.search.get_client", return_value=mock_client), \
         patch("app.tools.search.get_vector_store", return_value=mock_vector_store):

        import asyncio
        result = asyncio.run(semantic_search.fn("query", limit=2))

        # Should have indexed only 2 documents (case 3 had no full text)
        assert result["stats"]["indexed_count"] == 2
        assert result["stats"]["candidates_found"] == 3
        assert mock_vector_store.add_documents.call_count == 1

        # Verify the docs added
        call_args = mock_vector_store.add_documents.call_args
        documents, metadatas, ids = call_args[0]
        assert len(documents) == 2
        assert len(ids) == 2
        assert "1" in ids
        assert "2" in ids


def test_embedding_batch_processing():
    """Test batch processing of embeddings."""
    mock_client = AsyncMock()
    mock_vector_store = MagicMock()

    # Create a larger batch of candidates
    candidates = [
        {
            "id": i,
            "caseName": f"Case {i}",
            "citation": [f"{i} U.S. {i}"],
            "dateFiled": "2020-01-01",
            "court": "Test Court",
            "score": 100.0 - (i * 5)
        }
        for i in range(10)
    ]

    mock_client.search_opinions.return_value = {"results": candidates}
    mock_client.get_opinion_full_text.side_effect = [
        f"Full text for case {i}" for i in range(10)
    ]

    mock_vector_store.collection.get.return_value = {"ids": []}
    mock_vector_store.search.return_value = {
        "ids": [["0", "1", "2"]],
        "distances": [[0.1, 0.15, 0.2]],
        "metadatas": [[
            {"case_name": f"Case {i}", "citation": f"{i} U.S. {i}"}
            for i in range(3)
        ]]
    }

    with patch("app.tools.search.get_client", return_value=mock_client), \
         patch("app.tools.search.get_vector_store", return_value=mock_vector_store):

        import asyncio
        result = asyncio.run(semantic_search.fn("query", limit=3))

        # Verify all documents were processed in one batch
        assert result["stats"]["indexed_count"] == 10
        assert mock_vector_store.add_documents.call_count == 1

        # Verify batch contents
        call_args = mock_vector_store.add_documents.call_args
        documents, metadatas, ids = call_args[0]
        assert len(documents) == 10
        assert len(metadatas) == 10
        assert len(ids) == 10

        # Verify metadata structure
        for metadata in metadatas:
            assert "case_name" in metadata
            assert "citation" in metadata
            assert "date_filed" in metadata
            assert "court" in metadata
            assert "original_score" in metadata
