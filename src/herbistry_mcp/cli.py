"""Console entry point for MCP hosts that launch local stdio servers."""

import os

from .adapter import mcp


def main():
    if not os.getenv("HERBISTRY_MCP_TOKEN"):
        raise SystemExit("Set HERBISTRY_MCP_TOKEN to the token issued by your Herbistry administrator.")
    mcp.run(transport="stdio")
