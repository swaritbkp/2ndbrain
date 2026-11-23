"""PreToolUse guard: safety only, never style. Exit 2 = block (the message goes back to the agent).

Blocks: reading/writing .env, writes outside the project, hand-edits of Synapse-generated servers,
git push, recursive deletes outside the project, dumping the environment, pipe-to-shell, synapse init.
(The driver ALSO verifies integrity independently via scripts/verify_phase.py, so other agents can't silently bypass it.)
"""
from __future__ import annotations

import json
import os
import re
import sys

try:
    evt = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool, inp = evt.get("tool_name", ""), evt.get("tool_input", {}) or {}
root = os.path.abspath(os.getcwd())


def block(msg: str) -> None:
    print(f"BLOCKED by guard: {msg}", file=sys.stderr)
    sys.exit(2)


if tool in ("Edit", "Write", "MultiEdit", "Read"):
    raw = inp.get("file_path", "") or ""
    path = os.path.abspath(os.path.join(root, raw))
    base = os.path.basename(path)
    if base == ".env":
        block(".env is secret; code loads it via python-dotenv. Use scripts/env_check.py for SET/UNSET.")
    if tool != "Read":
        if not path.startswith(root):
            block(f"writes outside the project are not allowed: {path}")
        rel = os.path.relpath(path, root).replace("\\", "/")
        generated = base == "synapse_auto_server.py" or (
            base.endswith("_server.py") and (rel.count("/") == 0 or rel.startswith("probe/")))
        if generated and os.path.exists(path):
            block("Synapse-generated servers must not be hand-edited. Change the engine or the -q text and rebuild via scripts/synapse_build.py.")

if tool == "Bash":
    cmd = inp.get("command", "") or ""
    rules = [
        (r"\bgit\s+push\b", "no git push in unattended runs"),
        (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*\s+(/|~|[A-Za-z]:[\\/]|\.\.)", "recursive delete outside the project"),
        (r"Remove-Item[^|]*-Recurse[^|]*([A-Za-z]:\\|\.\.\\)", "recursive delete outside the project"),
        (r"\b(cat|type|more|less|head|tail|Get-Content|grep)\b[^|;&]*(^|[\s/\\])\.env\b(?!\.example)", "reading .env is not allowed"),
        (r"^\s*(printenv|env|set)\s*$", "dumping the environment may leak keys"),
        (r"(curl|wget|iwr|Invoke-WebRequest)[^|]*\|\s*(sh|bash|iex|powershell)", "piping downloads into a shell"),
        (r"\bsynapse\s+init\b", "synapse init is not used (local builds only)"),
        (r"--dangerously-skip-permissions", "nested permission bypass"),
    ]
    for pat, why in rules:
        if re.search(pat, cmd, flags=re.IGNORECASE):
            block(why)
sys.exit(0)
