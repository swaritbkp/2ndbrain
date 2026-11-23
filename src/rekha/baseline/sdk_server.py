"""Fallback baseline MCP server (official mcp SDK): the 12 engine functions as 12 tools, docstrings verbatim.

Used only if Synapse Auto over api.py doesn't give exactly 12 correct tools (docs/FALLBACKS.md).
Run: python -m rekha.baseline.sdk_server   (stdio)
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from rekha.engine import functions as F

mcp = FastMCP("rekha-baseline-12-tools")
for _name in F.PUBLIC_FUNCTIONS:
    mcp.add_tool(getattr(F, _name), name=_name, description=getattr(F, _name).__doc__)

if __name__ == "__main__":
    mcp.run()
