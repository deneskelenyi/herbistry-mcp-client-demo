#!/usr/bin/env python3
"""Example: discover and call Herbistry's hosted MCP tools."""

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
            tools = await session.list_tools()
            print("Available tools:", ", ".join(tool.name for tool in tools.tools))
            herbs = await session.call_tool(
                "search_herbs", {"query": args.herb, "limit": 5},
                read_timeout_seconds=timedelta(seconds=30))
            print("\nHerb search:\n" + json.dumps(payload(herbs), indent=2))
            answer = await session.call_tool(
                "ask_herbal_rag", {"question": args.question},
                read_timeout_seconds=timedelta(seconds=120))
            print("\nCited RAG response:\n" + json.dumps(payload(answer), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--herb", default="turmeric", help="Herb search query")
    parser.add_argument(
        "--question", default="What does the evidence say about turmeric and inflammation?",
        help="Question for the Herbistry RAG tool")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
