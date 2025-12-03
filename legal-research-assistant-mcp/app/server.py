"""Legal Research Assistant MCP Server.

This server provides advanced legal research capabilities including:
- Treatment analysis (Shepardizing alternative)
- Citation network visualization
- Quote verification
- Semantic case search

Built on top of CourtListener MCP using the wrapper/orchestrator pattern.
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from fastmcp import FastMCP

from app.config import settings
from app.tools.network import network_server
from app.tools.treatment import treatment_server
from app.tools.verification import verification_server

# Configure logging
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp: FastMCP[Any] = FastMCP(
    name="Legal Research Assistant MCP",
    instructions=(
        "Advanced legal research MCP providing treatment analysis, citation network visualization, "
        "quote verification, and semantic case search. Built on top of CourtListener MCP using the "
        "wrapper/orchestrator pattern. Available tools include: case validity checking (Shepardizing alternative), "
        "quote verification, citation network visualization, and semantic search capabilities."
    ),
)


@mcp.tool()
def health_check() -> dict[str, Any]:
    """Check the health status of the Legal Research Assistant MCP server.

    Returns:
        Dictionary containing server status and configuration info
    """
    logger.info("Health check requested")

    return {
        "status": "healthy",
        "version": "0.1.0",
        "server_name": "Legal Research Assistant MCP",
        "timestamp": datetime.now(UTC).isoformat(),
        "capabilities": [
            "treatment_analysis",
            "citation_networks",
            "quote_verification",
            "semantic_search (planned)",
        ],
        "config": {
            "courtlistener_mcp_url": settings.courtlistener_mcp_url,
            "max_citing_cases": settings.max_citing_cases,
            "network_max_depth": settings.network_max_depth,
        },
        "python_version": sys.version.split()[0],
    }


@mcp.tool()
def status() -> dict[str, str]:
    """Get server status.

    Returns:
        Server status message
    """
    return {
        "status": "operational",
        "message": "Legal Research Assistant MCP is running",
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def setup() -> None:
    """Set up the server by importing tool modules."""
    logger.info("Setting up Legal Research Assistant MCP server")

    # Import treatment analysis tools
    await mcp.import_server(treatment_server)
    logger.info("Imported treatment analysis tools")

    # Import quote verification tools
    await mcp.import_server(verification_server)
    logger.info("Imported quote verification tools")

    # Import citation network tools
    await mcp.import_server(network_server)
    logger.info("Imported citation network analysis tools")

    logger.info("Server setup complete")


# Run setup when module is imported
asyncio.run(setup())


async def main() -> None:
    """Run the Legal Research Assistant MCP server."""
    logger.info("Starting Legal Research Assistant MCP server")
    logger.info(f"Configuration: {settings.model_dump()}")

    try:
        # Run with stdio transport (default for MCP servers)
        await mcp.run_async(
            transport="stdio",
            log_level=settings.log_level.lower(),
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


if __name__ == "__main__":
    logger.info("Legal Research Assistant MCP starting")
    asyncio.run(main())
