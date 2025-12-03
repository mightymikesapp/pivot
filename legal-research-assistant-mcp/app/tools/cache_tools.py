"""Cache management tools for the MCP server.

This module provides tools for monitoring and managing the application's cache.
"""

from typing import Any

from fastmcp import FastMCP

from app.cache import CacheType, get_cache_manager
from app.logging_utils import log_event

# Create a sub-server for cache tools
cache_server = FastMCP("Cache Tools")


@cache_server.tool()
def cache_stats() -> dict[str, Any]:
    """Get current cache statistics.

    Returns:
        Dictionary containing cache hits, misses, file count, and size.
    """
    manager = get_cache_manager()
    stats = manager.get_stats()

    log_event(
        logger=None,  # fastmcp handles logging if needed, or we can import logger
        event="cache_stats_requested",
        message="Cache statistics retrieved",
        stats=stats
    )
    return stats


@cache_server.tool()
def cache_clear(type: str | None = None) -> dict[str, Any]:
    """Clear the cache.

    Args:
        type: Specific cache type to clear ('metadata', 'text', 'search').
              If omitted, clears all cache.

    Returns:
        Summary of cleared files.
    """
    manager = get_cache_manager()

    target_type = None
    if type:
        try:
            target_type = CacheType(type.lower())
        except ValueError:
            return {
                "error": f"Invalid cache type: {type}. Valid types are: {[t.value for t in CacheType]}"
            }

    count = manager.clear(target_type)

    message = f"Cleared {count} files from {'all' if not type else type} cache"
    log_event(
        logger=None,
        event="cache_cleared",
        message=message,
        count=count,
        target=type
    )

    return {
        "status": "success",
        "message": message,
        "files_cleared": count
    }
