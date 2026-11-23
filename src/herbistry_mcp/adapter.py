"""Forward local stdio MCP tools to Herbistry's authenticated remote endpoint."""

import os
from datetime import timedelta

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.fastmcp import FastMCP

DEFAULT_URL = "https://www.herbistry.cc/mcp"

mcp = FastMCP(
    "Herbistry",
    instructions="Read-only Herbistry product, herb, and cited scientific RAG tools.",
    website_url="https://www.herbistry.cc",
)


def _settings():
    token = os.getenv("HERBISTRY_MCP_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HERBISTRY_MCP_TOKEN is required")
    url = os.getenv("HERBISTRY_MCP_URL", DEFAULT_URL).strip()
    if not url.startswith("https://") and not url.startswith("http://localhost"):
        raise RuntimeError("HERBISTRY_MCP_URL must use HTTPS (except local development)")
    return url, token


async def call_remote(tool_name, arguments):
    """Call one remote tool; no credentials or responses are logged locally."""
    url, token = _settings()
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers, timeout=30, sse_read_timeout=120) as streams:
        read, write = streams[:2]
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                tool_name, arguments, read_timeout_seconds=timedelta(seconds=120))
            if result.isError:
                message = " ".join(
                    getattr(item, "text", "") for item in result.content
                ).strip() or "Remote Herbistry tool failed"
                raise RuntimeError(message)
            payload = result.structuredContent
            if isinstance(payload, dict) and set(payload) == {"result"}:
                return payload["result"]
            if payload is not None:
                return payload
            return {"content": [item.model_dump(mode="json") for item in result.content]}


@mcp.tool(structured_output=True, annotations={"readOnlyHint": True, "openWorldHint": False})
async def search_products(query: str, limit: int = 20) -> dict[str, object]:
    """Search supplement products by product or botanical ingredient name."""
    return await call_remote("search_products", {"query": query, "limit": limit})


@mcp.tool(structured_output=True, annotations={"readOnlyHint": True, "openWorldHint": False})
async def get_product(dsld_id: str) -> dict[str, object]:
    """Get a product's label, ingredients, amounts, statements, and prices by DSLD ID."""
    return await call_remote("get_product", {"dsld_id": dsld_id})


@mcp.tool(structured_output=True, annotations={"readOnlyHint": True, "openWorldHint": False})
async def search_herbs(query: str, limit: int = 20) -> dict[str, object]:
    """Search herb profiles by common or scientific name."""
    return await call_remote("search_herbs", {"query": query, "limit": limit})


@mcp.tool(structured_output=True, annotations={"readOnlyHint": True, "openWorldHint": False})
async def get_herb(herb_name: str) -> dict[str, object]:
    """Get an herb profile and linked products by exact common name."""
    return await call_remote("get_herb", {"herb_name": herb_name})


@mcp.tool(structured_output=True, annotations={"readOnlyHint": True, "openWorldHint": True})
async def ask_herbal_rag(question: str) -> dict[str, object]:
    """Answer an herbal-medicine question using cited scientific literature and RAG."""
    return await call_remote("ask_herbal_rag", {"question": question})
