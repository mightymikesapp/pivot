"""Tests for the CacheManager."""

import time

import pytest

from app.cache import CacheManager, CacheType


@pytest.fixture
def cache_dir(tmp_path):
    """Create a temporary directory for cache."""
    return tmp_path / "cache"


@pytest.fixture
def cache_manager(cache_dir):
    """Create a cache manager instance."""
    return CacheManager(base_dir=cache_dir)


def test_cache_initialization(cache_manager, cache_dir):
    """Test that cache directories are created."""
    assert cache_dir.exists()
    assert (cache_dir / "metadata").exists()
    assert (cache_dir / "text").exists()
    assert (cache_dir / "search").exists()


def test_cache_key_generation(cache_manager):
    """Test consistent key generation."""
    params1 = {"q": "test", "limit": 10}
    params2 = {"limit": 10, "q": "test"}
    params3 = {"q": "other"}

    key1 = cache_manager._build_key(params1)
    key2 = cache_manager._build_key(params2)
    key3 = cache_manager._build_key(params3)

    assert key1 == key2  # Order shouldn't matter
    assert key1 != key3


def test_cache_set_get_metadata(cache_manager):
    """Test setting and getting metadata."""
    key = {"id": 123}
    data = {"case_name": "Test Case", "id": 123}

    cache_manager.set(CacheType.METADATA, key, data)
    retrieved = cache_manager.get(CacheType.METADATA, key)

    assert retrieved == data
    assert cache_manager.stats["hits"] == 1
    assert cache_manager.stats["misses"] == 0


def test_cache_set_get_text(cache_manager):
    """Test setting and getting text."""
    key = {"id": 123, "field": "text"}
    text = "This is the opinion text."

    cache_manager.set(CacheType.TEXT, key, text)
    retrieved = cache_manager.get(CacheType.TEXT, key)

    assert retrieved == text


def test_cache_miss(cache_manager):
    """Test cache miss."""
    key = {"id": 999}
    retrieved = cache_manager.get(CacheType.METADATA, key)

    assert retrieved is None
    assert cache_manager.stats["misses"] == 1


def test_cache_ttl_expiration(cache_manager, monkeypatch):
    """Test that expired items are ignored."""
    key = {"id": 123}
    data = {"data": "old"}

    # Set item
    cache_manager.set(CacheType.SEARCH, key, data)

    # Verify it's there
    assert cache_manager.get(CacheType.SEARCH, key) == data

    # Fast forward time beyond TTL (Search TTL is 3600s)
    future_time = time.time() + 4000

    # Mock path.stat() to return old time, but we need to mock time.time()
    # Actually, CacheManager checks time.time() - stat.st_mtime.
    # So we can just patch time.time() to be in the future.
    monkeypatch.setattr(time, "time", lambda: future_time)

    retrieved = cache_manager.get(CacheType.SEARCH, key)
    assert retrieved is None
    assert cache_manager.stats["misses"] == 1  # 1 miss from expiration (plus previous hits aren't counted in this assertion context if we check count)


def test_cache_clear(cache_manager):
    """Test clearing the cache."""
    cache_manager.set(CacheType.METADATA, "k1", {})
    cache_manager.set(CacheType.TEXT, "k2", "txt")

    assert cache_manager.get(CacheType.METADATA, "k1") is not None

    # Clear metadata only
    cache_manager.clear(CacheType.METADATA)
    assert cache_manager.get(CacheType.METADATA, "k1") is None
    assert cache_manager.get(CacheType.TEXT, "k2") is not None

    # Clear all
    cache_manager.clear()
    assert cache_manager.get(CacheType.TEXT, "k2") is None


def test_cache_stats(cache_manager):
    """Test stats reporting."""
    cache_manager.set(CacheType.TEXT, "k1", "A" * 100)
    cache_manager.get(CacheType.TEXT, "k1") # Hit
    cache_manager.get(CacheType.TEXT, "k2") # Miss

    stats = cache_manager.get_stats()

    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["files"] == 1
    assert stats["size_bytes"] >= 100
