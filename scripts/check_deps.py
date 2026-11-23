"""Import every dependency the project uses. Run in phase 00 and the clean-room check."""
from __future__ import annotations

import importlib
import sys

MODULES = ["yaml", "dotenv", "httpx", "openai", "mcp", "mcp.server.fastmcp", "fastapi", "uvicorn", "pydantic",
           "streamlit", "pandas", "pptx", "tiktoken", "pytest"]
bad = []
for m in MODULES:
    try:
        importlib.import_module(m)
    except Exception as e:
        bad.append(f"{m}: {type(e).__name__}: {e}")
print("all imports ok" if not bad else "\n".join(bad))
sys.exit(1 if bad else 0)
