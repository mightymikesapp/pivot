"""Tests for MCP server."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from app.server import mcp, health_check, status

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_server_setup():
    """Test server initialization."""
    assert mcp.name == "Legal Research Assistant MCP"

@pytest.mark.asyncio
async def test_health_check():
    """Test health check tool."""
    # Use .fn() to access the original function for testing
    result = health_check.fn()
    assert result["status"] == "healthy"
    assert "capabilities" in result
    assert "config" in result
    assert result["version"] == "0.1.0"

@pytest.mark.asyncio
async def test_status():
    """Test status tool."""
    # Use .fn() to access the original function for testing
    result = status.fn()
    assert result["status"] == "operational"
    assert "timestamp" in result

@pytest.mark.asyncio
async def test_main():
    """Test main function execution (basic path)."""
    with patch("app.server.mcp.run_async") as mock_run:
        from app.server import main
        await main()
        mock_run.assert_called_once()

@pytest.mark.asyncio
async def test_main_error():
    """Test main function error handling."""
    with patch("app.server.mcp.run_async", side_effect=Exception("Setup failed")):
        from app.server import main
        with pytest.raises(Exception, match="Setup failed"):
            await main()
