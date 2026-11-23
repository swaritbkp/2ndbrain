"""Tiny sync helpers around the MCP stdio client (used by contract tests and scripts)."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def _params(server: str, env: dict | None) -> StdioServerParameters:
    e = dict(os.environ)
    e["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT), e.get("PYTHONPATH", "")])
    e.update(env or {})
    if server.endswith(".py"):
        return StdioServerParameters(command=sys.executable, args=[server], env=e, cwd=str(ROOT))
    return StdioServerParameters(command=sys.executable, args=["-m", server], env=e, cwd=str(ROOT))


def list_tools(server: str, env: dict | None = None) -> list[dict]:
    async def go():
        async with stdio_client(_params(server, env)) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                return [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in (await s.list_tools()).tools]
    return asyncio.run(go())


def call_sequence(server: str, calls: list[tuple[str, dict]], env: dict | None = None) -> list[dict]:
    """Run several tool calls in ONE server session; returns parsed JSON (or {'text': ...})."""
    async def go():
        out = []
        async with stdio_client(_params(server, env)) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                for name, args in calls:
                    res = await s.call_tool(name, args)
                    text = "".join(getattr(c, "text", "") for c in res.content)
                    try:
                        out.append(json.loads(text))
                    except json.JSONDecodeError:
                        out.append({"text": text})
        return out
    return asyncio.run(go())


if __name__ == "__main__":
    print(json.dumps(list_tools(sys.argv[1]), indent=2))
