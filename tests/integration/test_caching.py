"""Integration tests for caching behavior.

Tests cache hit/miss performance, invalidation, and concurrent access.
"""

import time
from pathlib import Path
from threading import Thread
from unittest.mock import patch

import pytest

from app.cache import CacheManager, CacheType


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Fixture providing a temporary cache directory."""
    return tmp_path / "cache"


@pytest.fixture
def cache_manager(temp_cache_dir):
    """Fixture providing a cache manager with temp directory."""
    with patch("app.cache.get_settings") as mock_settings:
        mock_settings.return_value.cache_enabled = True
        mock_settings.return_value.courtlistener_cache_dir = temp_cache_dir
        mock_settings.return_value.courtlistener_ttl_metadata = 3600
        mock_settings.return_value.courtlistener_ttl_text = 7200
        mock_settings.return_value.courtlistener_ttl_search = 1800

        manager = CacheManager(base_dir=temp_cache_dir)
        yield manager


@pytest.mark.integration
def test_cache_hit_performance(cache_manager):
    """Test cache hit performance benefits."""
    # Set a value in cache
    test_key = {"citation": "410 U.S. 113", "court": "scotus"}
    test_data = {
        "caseName": "Roe v. Wade",
        "dateFiled": "1973-01-22",
        "opinions": [{"id": 1}],
    }

    cache_manager.set(CacheType.METADATA, test_key, test_data)

    # First read should be a hit
    assert cache_manager.get(CacheType.METADATA, test_key) == test_data
    assert cache_manager.stats["hits"] == 1

    # Second read should also be a hit
    assert cache_manager.get(CacheType.METADATA, test_key) == test_data
    assert cache_manager.stats["hits"] == 2
    assert cache_manager.stats["misses"] == 0

    # Different key should be a miss
    different_key = {"citation": "505 U.S. 833"}
    assert cache_manager.get(CacheType.METADATA, different_key) is None
    assert cache_manager.stats["misses"] == 1


@pytest.mark.integration
def test_cache_invalidation(cache_manager):
    """Test cache invalidation by TTL expiration."""
    test_key = {"citation": "410 U.S. 113"}
    test_data = {"caseName": "Roe v. Wade"}

    cache_manager.set(CacheType.METADATA, test_key, test_data)

    # Get should work immediately
    assert cache_manager.get(CacheType.METADATA, test_key) == test_data
    assert cache_manager.stats["hits"] == 1

    # Manually expire the cache entry by mocking time
    cache_file = list((cache_manager.base_dir / CacheType.METADATA.value).glob("*.json"))[0]
    with patch("app.cache.time.time", return_value=time.time() + 4000):
        result = cache_manager.get(CacheType.METADATA, test_key)

    # Should miss due to TTL expiration
    assert result is None
    assert cache_manager.stats["misses"] >= 1
    # File should be deleted (lazy deletion)
    assert not cache_file.exists()


@pytest.mark.integration
def test_concurrent_cache_access():
    """Test cache behavior under concurrent access."""
    cache_dir = Path("/tmp/test_cache_concurrent")
    cache_dir.mkdir(exist_ok=True)

    with patch("app.cache.get_settings") as mock_settings:
        mock_settings.return_value.cache_enabled = True
        mock_settings.return_value.courtlistener_cache_dir = cache_dir
        mock_settings.return_value.courtlistener_ttl_metadata = 3600
        mock_settings.return_value.courtlistener_ttl_text = 7200
        mock_settings.return_value.courtlistener_ttl_search = 1800

        managers = [CacheManager(base_dir=cache_dir) for _ in range(3)]

        # Shared data
        test_key = {"citation": "410 U.S. 113"}
        test_data = {"caseName": "Roe v. Wade", "dateFiled": "1973-01-22"}
        results = []

        def write_and_read(manager, thread_id):
            """Thread worker that writes and reads from cache."""
            manager.set(CacheType.METADATA, test_key, {**test_data, "thread_id": thread_id})
            time.sleep(0.01)  # Small delay
            result = manager.get(CacheType.METADATA, test_key)
            results.append((thread_id, result))

        # Create threads
        threads = [
            Thread(target=write_and_read, args=(managers[i], i))
            for i in range(3)
        ]

        # Run threads
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should have successfully read the cache
        assert len(results) == 3
        assert all(r[1] is not None for r in results)

        # Cleanup
        import shutil
        shutil.rmtree(cache_dir, ignore_errors=True)


@pytest.mark.integration
def test_cache_clear_by_type(cache_manager):
    """Test clearing cache by specific type."""
    # Set data in multiple cache types
    metadata_key = {"citation": "410 U.S. 113"}
    metadata = {"caseName": "Roe v. Wade"}

    text_key = {"opinion_id": 123}
    text_data = "This is the full text of the opinion..."

    search_key = {"query": "abortion rights"}
    search_results = {"results": [{"id": 1}]}

    cache_manager.set(CacheType.METADATA, metadata_key, metadata)
    cache_manager.set(CacheType.TEXT, text_key, text_data)
    cache_manager.set(CacheType.SEARCH, search_key, search_results)

    # Verify all are cached
    assert cache_manager.get(CacheType.METADATA, metadata_key) == metadata
    assert cache_manager.get(CacheType.TEXT, text_key) == text_data
    assert cache_manager.get(CacheType.SEARCH, search_key) == search_results

    # Clear only metadata
    cleared = cache_manager.clear(CacheType.METADATA)
    assert cleared > 0

    # Metadata should be gone, others should remain
    assert cache_manager.get(CacheType.METADATA, metadata_key) is None
    assert cache_manager.get(CacheType.TEXT, text_key) == text_data
    assert cache_manager.get(CacheType.SEARCH, search_key) == search_results

    # Clear all
    cleared = cache_manager.clear()
    assert cleared >= 2

    # All should be gone now
    assert cache_manager.get(CacheType.TEXT, text_key) is None
    assert cache_manager.get(CacheType.SEARCH, search_key) is None


@pytest.mark.integration
def test_cache_stats_tracking(cache_manager):
    """Test cache statistics tracking."""
    stats = cache_manager.get_stats()

    assert stats["enabled"] is True
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["files"] == 0
    assert stats["size_bytes"] == 0

    # Add some data
    cache_manager.set(CacheType.METADATA, {"citation": "410 U.S. 113"}, {"name": "Roe"})
    cache_manager.set(CacheType.TEXT, {"opinion_id": 123}, "Text content here")

    # Hit the cache
    cache_manager.get(CacheType.METADATA, {"citation": "410 U.S. 113"})
    cache_manager.get(CacheType.TEXT, {"opinion_id": 123})

    # Miss
    cache_manager.get(CacheType.METADATA, {"citation": "999 U.S. 999"})

    stats = cache_manager.get_stats()

    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["files"] == 2
    assert stats["size_bytes"] > 0
    assert stats["size_mb"] >= 0


@pytest.mark.integration
def test_cache_with_disabled_cache(temp_cache_dir):
    """Test behavior when caching is disabled."""
    with patch("app.cache.get_settings") as mock_settings:
        mock_settings.return_value.cache_enabled = False
        mock_settings.return_value.courtlistener_cache_dir = temp_cache_dir
        mock_settings.return_value.courtlistener_ttl_metadata = 3600
        mock_settings.return_value.courtlistener_ttl_text = 7200
        mock_settings.return_value.courtlistener_ttl_search = 1800

        manager = CacheManager(base_dir=temp_cache_dir)

        # Set should do nothing
        manager.set(CacheType.METADATA, {"test": "key"}, {"test": "data"})

        # Get should always return None
        assert manager.get(CacheType.METADATA, {"test": "key"}) is None

        # Stats should show no activity
        stats = manager.get_stats()
        assert stats["enabled"] is False
        assert stats["files"] == 0
        assert stats["hits"] == 0


@pytest.mark.integration
def test_cache_key_normalization(cache_manager):
    """Test that cache keys are properly normalized."""
    # Different orderings of same data should produce same key
    key1 = {"citation": "410 U.S. 113", "court": "scotus"}
    key2 = {"court": "scotus", "citation": "410 U.S. 113"}
    key3 = {"CITATION": "410 u.s. 113", "COURT": "SCOTUS"}  # Different case

    data = {"caseName": "Roe v. Wade"}

    cache_manager.set(CacheType.METADATA, key1, data)

    # All variations should retrieve the same cached value
    assert cache_manager.get(CacheType.METADATA, key2) == data
    assert cache_manager.get(CacheType.METADATA, key3) == data

    # Should all be cache hits
    assert cache_manager.stats["hits"] == 3


@pytest.mark.integration
def test_cache_different_types(cache_manager):
    """Test caching different data types correctly."""
    # Metadata (JSON)
    metadata_key = "metadata_test"
    metadata = {"id": 1, "name": "Test", "tags": ["a", "b"]}
    cache_manager.set(CacheType.METADATA, metadata_key, metadata)

    retrieved_metadata = cache_manager.get(CacheType.METADATA, metadata_key)
    assert retrieved_metadata == metadata
    assert isinstance(retrieved_metadata, dict)

    # Text
    text_key = "text_test"
    text_content = "This is long text content with multiple lines.\nAnd paragraphs."
    cache_manager.set(CacheType.TEXT, text_key, text_content)

    retrieved_text = cache_manager.get(CacheType.TEXT, text_key)
    assert retrieved_text == text_content
    assert isinstance(retrieved_text, str)

    # Search results (JSON)
    search_key = "search_test"
    search_data = {
        "results": [
            {"id": 1, "score": 0.95},
            {"id": 2, "score": 0.87},
        ],
        "total": 2,
    }
    cache_manager.set(CacheType.SEARCH, search_key, search_data)

    retrieved_search = cache_manager.get(CacheType.SEARCH, search_key)
    assert retrieved_search == search_data


@pytest.mark.integration
def test_cache_error_resilience(cache_manager):
    """Test cache behavior when errors occur during operations."""
    test_key = "error_test"
    test_data = {"test": "data"}

    cache_manager.set(CacheType.METADATA, test_key, test_data)

    # Corrupt the cache file
    cache_files = list((cache_manager.base_dir / CacheType.METADATA.value).glob("*.json"))
    assert len(cache_files) > 0

    cache_file = cache_files[0]
    with open(cache_file, "w") as f:
        f.write("INVALID JSON{{{")

    # Should handle gracefully and return None
    result = cache_manager.get(CacheType.METADATA, test_key)
    assert result is None
    assert cache_manager.stats["errors"] > 0
