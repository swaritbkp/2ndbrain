"""Discover tool-capable Nemotron (or configured) models on OpenRouter and resolve the roles.

Writes state/models.json: {"available": [...], "resolved": {arena, attacker, synapse, sweep}, "substitutions": [...]}
A configured model that doesn't exist or doesn't support tools is replaced by the best tool-capable Nemotron
model, and the substitution is recorded (never silently).
Usage: python scripts/openrouter_models.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
PREFER = ["nemotron-3.5-super", "nemotron-3-ultra", "nemotron-3.5-lightning", "nemotron"]   # strongest first


def main() -> int:
    try:
        r = httpx.get("https://openrouter.ai/api/v1/models", timeout=30)
        r.raise_for_status()
        models = r.json()["data"]
    except Exception as e:
        print(f"MODEL LIST FAILED: {type(e).__name__}: {e}")
        return 1
    by_id = {m["id"]: m for m in models}
    tools_ok = lambda mid: mid in by_id and "tools" in (by_id[mid].get("supported_parameters") or [])  # noqa: E731
    nemo = sorted((m for m in models if "nemotron" in m["id"].lower() and tools_ok(m["id"])), key=lambda m: m["id"])
    allow_free = os.environ.get("ARENA_ALLOW_FREE", "0") == "1"

    def best() -> str | None:
        for p in PREFER:
            for m in nemo:
                if p in m["id"] and (allow_free or not m["id"].endswith(":free")):
                    return m["id"]
        return nemo[0]["id"] if nemo else None

    resolved, subs = {}, []
    for role, env in [("arena", "ARENA_MODEL"), ("attacker", "ATTACKER_MODEL"), ("synapse", "SYNAPSE_MODEL")]:
        want = os.environ.get(env, "").strip() or (resolved.get("arena", "") if role == "attacker" else "")
        if want and tools_ok(want):
            resolved[role] = want
        else:
            pick = best()
            resolved[role] = pick or ""
            subs.append({"role": role, "wanted": want, "used": pick, "why": "missing or no tool support"})
    sweep = [s.strip() for s in os.environ.get("ARENA_SWEEP_MODELS", "").split(",") if s.strip()]
    resolved["sweep"] = ",".join(s for s in sweep if tools_ok(s))
    for s in sweep:
        if not tools_ok(s):
            subs.append({"role": "sweep", "wanted": s, "used": None, "why": "missing or no tool support (dropped)"})
    out = {"available_tool_capable_nemotron": [{"id": m["id"], "context": m.get("context_length"),
                                               "pricing": m.get("pricing")} for m in nemo],
           "resolved": resolved, "substitutions": subs}
    (ROOT / "state").mkdir(exist_ok=True)
    (ROOT / "state" / "models.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"resolved": resolved, "substitutions": subs}, indent=2))
    return 0 if resolved.get("arena") else 1


if __name__ == "__main__":
    sys.exit(main())
