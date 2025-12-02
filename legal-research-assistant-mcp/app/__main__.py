"""Entry point for running Legal Research Assistant MCP as a module."""

import asyncio

from app.server import main

if __name__ == "__main__":
    asyncio.run(main())
