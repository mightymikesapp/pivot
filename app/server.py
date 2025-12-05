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
from app.logging_config import tool_logging
from app.logging_utils import log_event
from app.mcp_types import ToolPayload
from app.tools.cache_tools import cache_server
from app.tools.network import network_server
from app.tools.research import research_server
from app.tools.search import search_server
from app.tools.treatment import treatment_server
from app.tools.verification import verification_server

# Configure logging
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp: FastMCP[ToolPayload] = FastMCP(
    name="Legal Research Assistant MCP",
    instructions=(
        "Advanced legal research MCP providing treatment analysis, citation network visualization, "
        "quote verification, and semantic case search. Built on top of CourtListener MCP using the "
        "wrapper/orchestrator pattern. Available tools include: case validity checking (Shepardizing alternative), "
        "quote verification, citation network visualization, and semantic search capabilities."
    ),
)


@mcp.tool()
@tool_logging("health_check")
def health_check() -> dict[str, Any]:
    """Check the health status of the Legal Research Assistant MCP server.

    Returns:
        Dictionary containing server status and configuration info
    """
    log_event(logger, "Health check requested", tool_name="health_check", event="health_check")

    return {
        "status": "healthy",
        "version": "0.1.0",
        "server_name": "Legal Research Assistant MCP",
        "timestamp": datetime.now(UTC).isoformat(),
        "capabilities": [
            "treatment_analysis",
            "citation_networks",
            "quote_verification",
            "semantic_search",
        ],
        "config": {
            "courtlistener_mcp_url": settings.courtlistener_mcp_url,
            "max_citing_cases": settings.max_citing_cases,
            "network_max_depth": settings.network_max_depth,
        },
        "python_version": sys.version.split()[0],
    }


@mcp.tool()
@tool_logging("status")
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
    log_event(
        logger,
        "Setting up Legal Research Assistant MCP server",
        tool_name="server",
        event="server_setup",
    )

    # Import cache management tools
    await mcp.import_server(cache_server)
    log_event(
        logger,
        "Imported cache management tools",
        tool_name="server",
        event="server_setup",
    )

    # Import treatment analysis tools
    await mcp.import_server(treatment_server)
    log_event(
        logger,
        "Imported treatment analysis tools",
        tool_name="server",
        event="server_setup",
    )

    # Import quote verification tools
    await mcp.import_server(verification_server)
    log_event(
        logger,
        "Imported quote verification tools",
        tool_name="server",
        event="server_setup",
    )

    # Import citation network tools
    await mcp.import_server(network_server)
    log_event(
        logger,
        "Imported citation network analysis tools",
        tool_name="server",
        event="server_setup",
    )

    # Import research orchestration tools
    await mcp.import_server(research_server)
    log_event(
        logger,
        "Imported research orchestration tools",
        tool_name="server",
        event="server_setup",
    )

    # Import semantic search tools
    await mcp.import_server(search_server)
    log_event(
        logger,
        "Imported semantic search tools",
        tool_name="server",
        event="server_setup",
    )

    log_event(logger, "Server setup complete", tool_name="server", event="server_setup")


async def main() -> None:
    """Run the Legal Research Assistant MCP server."""
    logger.info("Starting Legal Research Assistant MCP server")
    logger.info(f"Configuration: {settings.model_dump()}")

    # Perform server setup
    await setup()

    try:
        # Run with stdio transport (default for MCP servers)
        await mcp.run_async(
            transport="stdio",
            log_level=settings.log_level.lower(),
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


def cli() -> None:
    """CLI entry point for the legal-research-mcp command."""
    logger.info("Legal Research Assistant MCP starting")
    asyncio.run(main())


if __name__ == "__main__":
    cli()
