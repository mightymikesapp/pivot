"""Management command entrypoints for administrative tasks."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, Sequence

from app.cache import CacheType, get_cache_manager
from app.logging_utils import log_event

logger = logging.getLogger(__name__)


def _handle_cache_clear(args: argparse.Namespace) -> dict[str, Any]:
    """Clear cache contents for a specific type or all types."""
    manager = get_cache_manager()
    cache_type: CacheType | None = None

    if args.type:
        try:
            cache_type = CacheType(args.type)
        except ValueError:
            valid_types = ", ".join(t.value for t in CacheType)
            raise ValueError(f"Invalid cache type: {args.type}. Valid types: {valid_types}")

    cleared = manager.clear(cache_type)
    log_event(
        logger,
        "Cache cleared",
        tool_name="management",
        event="cache_cleared",
        extra_context={
            "target_type": cache_type.value if cache_type else "all",
            "files_cleared": cleared,
        },
    )

    return {
        "status": "success",
        "files_cleared": cleared,
        "target": cache_type.value if cache_type else "all",
    }


def _handle_cache_stats(_: argparse.Namespace) -> dict[str, Any]:
    """Return cache statistics."""
    manager = get_cache_manager()
    stats = manager.get_stats()

    log_event(
        logger,
        "Cache stats requested",
        tool_name="management",
        event="cache_stats",
        extra_context={"stats": stats},
    )
    return stats


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser."""
    parser = argparse.ArgumentParser(description="Management commands for the MCP server")
    subparsers = parser.add_subparsers(dest="command", required=True)

    clear_parser = subparsers.add_parser("cache:clear", help="Clear cached CourtListener responses")
    clear_parser.add_argument(
        "--type",
        choices=[t.value for t in CacheType],
        help="Optional cache type to clear (metadata, text, search)",
    )
    clear_parser.set_defaults(handler=_handle_cache_clear)

    stats_parser = subparsers.add_parser("cache:stats", help="Show cache statistics")
    stats_parser.set_defaults(handler=_handle_cache_stats)

    return parser


def run(argv: Sequence[str] | None = None) -> int:
    """Execute a management command.

    Args:
        argv: Optional argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code integer (0 for success, non-zero for errors).
    """
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 1

    try:
        result = handler(args)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
