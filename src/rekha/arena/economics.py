"""F10 tool-surface economics + F8 language parity, from a results folder.

python -m rekha.arena.economics results/latest   → economics.json, language.json in that folder.
Schema tokens use tiktoken cl100k_base as an APPROXIMATION (Nemotron's tokenizer differs); stated in the output.
"""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import tiktoken

from rekha.arena.runner import servers_for
from rekha.arena.tools import ToolBox


def tool_schemas(agent: str) -> list[dict]:
    async def go():
        env = {"REKHA_DB": ":memory:", "REKHA_TOKEN_SECRET": "economics"}
        async with ToolBox(servers_for(agent), env) as tb:
            return tb.openai_tools
    return asyncio.run(go())


def _runs(d: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(d).glob("*__*__run*.json"))]


def economics(d: Path) -> dict:
    enc = tiktoken.get_encoding("cl100k_base")
    runs = _runs(d)
    out = {"tokenizer": "tiktoken cl100k_base (approximation)", "run_dir": str(d), "agents": {}}
    for agent in ("baseline", "composed"):
        tools = tool_schemas(agent)
        ok = [r for r in runs if r["agent"] == agent and r["score"]["outcome"] != "ERROR"]
        out["agents"][agent] = {
            "tools": len(tools), "tool_names": [t["function"]["name"] for t in tools],
            "schema_tokens_per_request": len(enc.encode(json.dumps(tools, ensure_ascii=False))),
            "runs": len(ok),
            "mean_tool_calls": round(statistics.mean(r["tool_calls"] for r in ok), 2) if ok else None,
            "mean_prompt_tokens": round(statistics.mean(r["prompt_tokens"] for r in ok)) if ok else None,
            "mean_completion_tokens": round(statistics.mean(r["completion_tokens"] for r in ok)) if ok else None,
            "p50_latency_ms": int(statistics.median(r["latency_ms"] for r in ok)) if ok else None,
            "mean_cost_usd": round(statistics.mean(r.get("cost_usd", 0) for r in ok), 6) if ok else None,
        }
    return out


def language(d: Path) -> dict:
    runs = [r for r in _runs(d) if r["kind"] == "attack"]
    out: dict = {"run_dir": str(d), "note": "attack runs only; ERROR runs excluded from rates and counted separately",
                 "agents": {}}
    for agent in ("baseline", "composed"):
        g: dict[str, dict] = defaultdict(lambda: {"runs": 0, "violations": 0, "errors": 0})
        for r in runs:
            if r["agent"] != agent:
                continue
            lang = r.get("language", "en")
            if r["score"]["outcome"] == "ERROR":
                g[lang]["errors"] += 1
                continue
            g[lang]["runs"] += 1
            g[lang]["violations"] += r["score"]["outcome"] == "VIOLATION"
        for v in g.values():
            v["violation_rate"] = round(v["violations"] / v["runs"], 4) if v["runs"] else None
        pairs = {}
        for r in runs:
            if r["agent"] == agent and r["case_id"].endswith("-HI"):
                base = r["case_id"][:-3]
                p = pairs.setdefault(base, {"en_violations": 0, "en_runs": 0, "hi_violations": 0, "hi_runs": 0})
                if r["score"]["outcome"] != "ERROR":
                    p["hi_runs"] += 1
                    p["hi_violations"] += r["score"]["outcome"] == "VIOLATION"
        for r in runs:
            if r["agent"] == agent and r["case_id"] in pairs and r["score"]["outcome"] != "ERROR":
                pairs[r["case_id"]]["en_runs"] += 1
                pairs[r["case_id"]]["en_violations"] += r["score"]["outcome"] == "VIOLATION"
        out["agents"][agent] = {"by_language": dict(g), "paired_cases": dict(sorted(pairs.items()))}
    return out


def main(d: str) -> int:
    p = Path(d)
    (p / "economics.json").write_text(json.dumps(economics(p), indent=2), encoding="utf-8")
    (p / "language.json").write_text(json.dumps(language(p), indent=2), encoding="utf-8")
    print(json.dumps({a: {k: v for k, v in s.items() if k != "tool_names"} for a, s in economics(p)["agents"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
