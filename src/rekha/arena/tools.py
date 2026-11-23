"""Open one or more MCP stdio servers for a run and expose their tools in OpenAI function-calling format."""
from __future__ import annotations

import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[3]


def server_params(server: str, env: dict) -> StdioServerParameters:
    e = dict(os.environ)  # keep SYSTEMROOT/PATH etc. (Windows needs them in subprocesses)
    e["PYTHONPATH"] = os.pathsep.join(p for p in [str(ROOT / "src"), str(ROOT), e.get("PYTHONPATH", "")] if p)
    e.update(env)
    args = [server] if server.endswith(".py") else ["-m", server]
    return StdioServerParameters(command=sys.executable, args=args, env=e, cwd=str(ROOT))


class ToolBox:
    """async with ToolBox(servers, env) as tb: tb.openai_tools, await tb.call(name, args)."""

    def __init__(self, servers: list[str], env: dict):
        self.servers, self.env = servers, env
        self.sessions: dict[str, ClientSession] = {}
        self.openai_tools: list[dict] = []
        self._stack = AsyncExitStack()

    async def __aenter__(self) -> "ToolBox":
        for srv in self.servers:
            r, w = await self._stack.enter_async_context(stdio_client(server_params(srv, self.env)))
            s = await self._stack.enter_async_context(ClientSession(r, w))
            await s.initialize()
            for t in (await s.list_tools()).tools:
                self.sessions[t.name] = s
                self.openai_tools.append({"type": "function", "function": {
                    "name": t.name, "description": t.description or "",
                    "parameters": t.inputSchema or {"type": "object", "properties": {}}}})
        return self

    async def __aexit__(self, *exc) -> None:
        await self._stack.aclose()

    async def call(self, name: str, args: dict):
        if name not in self.sessions:
            return {"error": f"unknown tool {name}"}
        res = await self.sessions[name].call_tool(name, args)
        text = "".join(getattr(c, "text", "") for c in res.content)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"text": text}
