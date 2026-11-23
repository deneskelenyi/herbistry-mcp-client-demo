#!/usr/bin/env python3
"""Example: search for a supplement and retrieve its Herbistry product label."""

import argparse
import asyncio
import json
import os
from datetime import timedelta

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def payload(result):
    if result.isError:
        text = " ".join(getattr(item, "text", "") for item in result.content)
        raise RuntimeError(text or "Herbistry tool failed")
    data = result.structuredContent or {
        "content": [item.model_dump(mode="json") for item in result.content]
    }
    if isinstance(data, dict) and set(data) == {"result"}:
        return data["result"]
    return data


async def run(args):
    token = os.getenv("HERBISTRY_MCP_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set HERBISTRY_MCP_TOKEN before running this example.")
    url = os.getenv("HERBISTRY_MCP_URL", "https://www.herbistry.cc/mcp")
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers, timeout=30, sse_read_timeout=120) as streams:
        read, write = streams[:2]
        async with ClientSession(read, write) as session:
            await session.initialize()
            search = await session.call_tool(
                "search_products", {"query": args.query, "limit": 5},
                read_timeout_seconds=timedelta(seconds=30))
            results = payload(search)["results"]
            if not results:
                raise SystemExit(f"No products found for {args.query!r}")
            match = results[0]
            label = await session.call_tool(
                "get_product", {"dsld_id": match["dsld_id"]},
                read_timeout_seconds=timedelta(seconds=30))
            print(json.dumps({
                "search_match": match,
                "product_label": payload(label),
            }, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="turmeric", help="Product or botanical ingredient search")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
