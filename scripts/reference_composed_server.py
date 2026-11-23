"""Reference composed MCP server wrapping engine/workflow.py.

Purpose: (1) validates the contract test suite itself; (2) the demo safety net if Synapse output is
unusable (Route C in docs/FALLBACKS.md must still expose it via Synapse; see FALLBACKS).
Run: python scripts/reference_composed_server.py   (stdio)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mcp.server.fastmcp import FastMCP  # noqa: E402

from rekha.engine.workflow import rebalance_switch  # noqa: E402

mcp = FastMCP("rekha-reference-composed")
mcp.add_tool(rebalance_switch, name="rebalance_switch", description=rebalance_switch.__doc__)

if __name__ == "__main__":
    mcp.run()
