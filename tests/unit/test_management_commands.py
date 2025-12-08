"""Tests for management commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.cache as cache_module
from app.cache import CacheManager, CacheType
from app import management


@pytest.fixture()
def temp_cache_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CacheManager:
    """Provide a cache manager backed by a temporary directory."""
    manager = CacheManager(base_dir=tmp_path / "cache")
    monkeypatch.setattr(cache_module, "_cache_manager", manager)
    return manager


def test_cache_stats_command(temp_cache_manager: CacheManager, capsys: pytest.CaptureFixture[str]) -> None:
    """cache:stats should return JSON stats with file counts."""
    temp_cache_manager.set(CacheType.METADATA, {"id": 1}, {"hello": "world"})

    exit_code = management.run(["cache:stats"])

    captured = capsys.readouterr()
    assert exit_code == 0

    payload = json.loads(captured.out)
    assert payload["files"] == 1
    assert payload["hits"] == 0
    assert payload["misses"] == 0
    assert payload["enabled"] is True


def test_cache_clear_command(temp_cache_manager: CacheManager, capsys: pytest.CaptureFixture[str]) -> None:
    """cache:clear should remove files for the selected cache type."""
    temp_cache_manager.set(CacheType.METADATA, {"id": 2}, {"case": "one"})
    temp_cache_manager.set(CacheType.SEARCH, {"q": "two"}, {"result": "two"})

    exit_code = management.run(["cache:clear", "--type", "metadata"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {"status": "success", "files_cleared": 1, "target": "metadata"}
    assert temp_cache_manager.get(CacheType.METADATA, {"id": 2}) is None
    assert temp_cache_manager.get(CacheType.SEARCH, {"q": "two"}) is not None

    # Clear everything
    exit_code_all = management.run(["cache:clear"])
    captured_all = capsys.readouterr()
    payload_all = json.loads(captured_all.out)

    assert exit_code_all == 0
    assert payload_all["target"] == "all"
    assert temp_cache_manager.get(CacheType.SEARCH, {"q": "two"}) is None


@pytest.mark.parametrize("bad_type", ["invalid", "metadata ", "TEXT"])
def test_cache_clear_invalid_type(
    bad_type: str, temp_cache_manager: CacheManager, capsys: pytest.CaptureFixture[str]
) -> None:
    """Invalid cache type should return a non-zero exit status."""
    exit_code = management.run(["cache:clear", "--type", bad_type])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Invalid cache type" in captured.err
