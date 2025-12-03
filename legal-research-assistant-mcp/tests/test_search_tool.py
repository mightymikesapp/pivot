
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.tools.search import semantic_search

@pytest.mark.asyncio
async def test_semantic_search():
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
