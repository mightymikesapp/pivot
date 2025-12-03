
import pytest
from unittest.mock import MagicMock, patch
from app.analysis.search.vector_store import LegalVectorStore

class TestLegalVectorStore:
    @pytest.fixture
    def mock_chroma(self):
        with patch("chromadb.PersistentClient") as mock:
            client = MagicMock()
            collection = MagicMock()
            client.get_or_create_collection.return_value = collection
            mock.return_value = client
            yield mock

    @pytest.fixture
    def store(self, mock_chroma):
        # Prevent actual model download during test
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            return LegalVectorStore(persistence_path="./test_db")

    def test_initialization(self, mock_chroma):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            store = LegalVectorStore(persistence_path="./custom_path")
            # Use ANY from unittest.mock, or just don't check the second arg if not needed
            from unittest.mock import ANY
            mock_chroma.assert_called_with(path="custom_path", settings=ANY)

    def test_add_documents(self, store):
        documents = ["doc1", "doc2"]
        metadatas = [{"id": 1}, {"id": 2}]
        ids = ["1", "2"]

        store.add_documents(documents, metadatas, ids)

        store.collection.upsert.assert_called_once_with(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def test_search(self, store):
        store.search("query", limit=5)

        store.collection.query.assert_called_once_with(
            query_texts=["query"],
            n_results=5,
            where=None
        )

    def test_clear(self, store):
        store.clear()
        store.client.reset.assert_called_once()
        store.client.get_or_create_collection.assert_called() # Should re-create

    def test_stats(self, store):
        store.collection.count.return_value = 10
        stats = store.get_stats()
        assert stats["total_documents"] == 10
