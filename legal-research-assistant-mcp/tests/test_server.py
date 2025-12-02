"""Tests for MCP server."""

from app.server import mcp


def test_server_setup():
    """Test server initialization."""
    assert mcp.name == "Legal Research Assistant MCP"

# Not testing main() execution as it requires stdin interaction which is hard to mock correctly with FastMCP's run_async
