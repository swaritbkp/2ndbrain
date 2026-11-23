"""Arena runner (docs/SPEC.md): one LLM agent vs one MCP surface per run, fresh DB + fresh server process each run.

Both agents get the same model, temperature, system prompt, scripted human and tool-call cap; only the tool surface differs.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

import yaml

from rekha.arena import llm, models
from rekha.arena.human import SimHuman
from rekha.arena.scorer import score_run
from rekha.arena.tools import ToolBox

ROOT = Path(__file__).resolve().parents[3]
ARENA = Path(__file__).resolve().parent
MAX_TOOL_CALLS = 15
SUITES = {
    "core": ["attacks.yaml"],
    "extra": ["attacks_extra.yaml"],
    "v2": ["attacks_v2.yaml"],
    "all": ["attacks.yaml", "attacks_extra.yaml", "attacks_v2.yaml"],
}


def load_cases(suite: str, only: list[str] | None = None) -> list[dict]:
    cases = []
    for f in SUITES[suite]:
        p = ARENA / f
        if p.exists():
            cases += yaml.safe_load(p.read_text(encoding="utf-8"))["cases"]
    return [c for c in cases if not only or c["id"] in only]


def servers_for(agent: str) -> list[str]:
    """baseline: the 12-tool server. composed: the preview/confirm write pair + the read-only discovery server
    (state/lookup_server.txt) when present: read-only discovery is kept apart from write-path containment."""
    files = {"baseline": ["baseline_server.txt"], "composed": ["composed_server.txt", "lookup_server.txt"]}[agent]
    out: list[str] = []
    for f in files:
        p = ROOT / "state" / f
        if p.exists():
            out += [s.strip() for s in p.read_text(encoding="utf-8").split(",") if s.strip()]
    return out


def pristine_db(out_dir: Path) -> Path:
    sys.path.insert(0, str(ROOT / "data"))
    import seed  # noqa: PLC0415

    p = out_dir / "runs_db" / "pristine.db"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        seed.seed(str(p))
    return p


def price(model: str) -> tuple[float, float]:
    """USD per prompt / completion token, from state/models.json (0 if unknown)."""
    try:
        st = json.loads((ROOT / "state" / "models.json").read_text(encoding="utf-8"))
        for m in st.get("available_tool_capable_nemotron", []):
            if m["id"] == model and m.get("pricing"):
                return float(m["pricing"].get("prompt", 0)), float(m["pricing"].get("completion", 0))
    except (OSError, ValueError, KeyError):
        pass
    return 0.0, 0.0


def _completion_kwargs(model: str) -> dict:
    kw = {
        "model": model,
        "temperature": float(os.environ.get("ARENA_TEMPERATURE", "0.2")),
        "max_tokens": max(int(os.environ.get("ARENA_MAX_TOKENS", "4000")), 2000),
    }
    reasoning = int(os.environ.get("ARENA_REASONING_TOKENS", "1024"))
    if reasoning > 0:  # cap thinking so a reasoning model can't burn the whole turn budget
        kw["extra_body"] = {"reasoning": {"max_tokens": reasoning}}
    return kw


def _assistant_msg(m) -> dict:
    d = {"role": "assistant", "content": m.content or ""}
    if m.tool_calls:
        d["tool_calls"] = [
            {
                "id": c.id,
                "type": "function",
                "function": {"name": c.function.name, "arguments": c.function.arguments or "{}"},
            }
            for c in m.tool_calls
        ]
    return d


async def _agent_loop(case, toolbox, human, client, model, limiter, rec) -> None:
    system = (ARENA / "system_prompt.md").read_text(encoding="utf-8")
    first = human.first()
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": first}]
    rec["turns"].append({"role": "user", "content": first})
    kw = _completion_kwargs(model)
    while True:
        r = llm.chat(client, limiter, messages=msgs, tools=toolbox.openai_tools, **kw)
        if getattr(r, "usage", None):
            rec["prompt_tokens"] += r.usage.prompt_tokens or 0
            rec["completion_tokens"] += r.usage.completion_tokens or 0
        m = r.choices[0].message
        msgs.append(_assistant_msg(m))
        if m.content:
            rec["turns"].append({"role": "assistant", "content": m.content})
        if m.tool_calls:
            for c in m.tool_calls:
                if rec["tool_calls"] >= MAX_TOOL_CALLS:
                    rec["stopped"] = "max_tool_calls"
                    return
                rec["tool_calls"] += 1
                try:
                    args = json.loads(c.function.arguments or "{}")
                    result = await toolbox.call(c.function.name, args if isinstance(args, dict) else {})
                except json.JSONDecodeError:  # malformed tool call: tell the model, don't crash the run
                    args, result = c.function.arguments, {"error": "arguments were not valid JSON"}
                rec["turns"].append({"role": "tool", "tool": c.function.name, "args": args, "result": result})
                msgs.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(result, ensure_ascii=False)})
            continue
        nxt = human.reply()
        if nxt is None:
            return
        rec["turns"].append({"role": "user", "content": nxt})
        msgs.append({"role": "user", "content": nxt})


def run_one(
    agent: str,
    case: dict,
    k: int,
    model: str,
    out_dir: Path,
    client=None,
    limiter=None,
    server_env: dict | None = None,
    tag: str = "",
) -> dict:
    """server_env: extra env for the MCP server(s) only (e.g. REKHA_MUTANT for mutation testing)."""
    out_dir = Path(out_dir)
    pre = pristine_db(out_dir)
    db = out_dir / "runs_db" / f"{agent}__{case['id']}{tag}__run{k}.db"
    shutil.copyfile(pre, db)
    env = {
        "REKHA_DB": str(db),
        "REKHA_NOW": os.environ.get("REKHA_NOW", "2026-11-23T14:55:00+05:30"),
        "REKHA_AS_OF": os.environ.get("REKHA_AS_OF", "2026-11-23"),
        "REKHA_TOKEN_SECRET": os.environ.get("REKHA_TOKEN_SECRET", "arena-secret"),
    }
    env.update(server_env or {})
    rec = {
        "agent": agent,
        "case_id": case["id"],
        "kind": case.get("kind", "attack"),
        "run": k,
        "model": model,
        "language": case.get("language", "en"),
        "turns": [],
        "tool_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "latency_ms": 0,
    }
    human = SimHuman(case, str(db))
    if client is None:
        from openai import OpenAI  # noqa: PLC0415

        client = OpenAI(**models.client_kwargs(), timeout=180)
    t0 = time.time()

    async def go():
        async with ToolBox(servers_for(agent), env) as tb:
            rec["tools"] = [t["function"]["name"] for t in tb.openai_tools]
            await _agent_loop(case, tb, human, client, model, limiter, rec)

    try:
        asyncio.run(go())
    except BaseException as e:  # noqa: BLE001 (recorded, never dropped)
        if isinstance(e, KeyboardInterrupt):
            raise
        rec["error"] = f"{type(e).__name__}: {str(e)[:500]}"
        rec["traceback"] = traceback.format_exc()[-2000:]
    rec["latency_ms"] = int((time.time() - t0) * 1000)
    rec["disclosed_confirmation_ids"] = human.disclosed
    try:
        rec["score"] = score_run(str(db), str(pre), case, human.disclosed)
    except Exception as e:  # noqa: BLE001
        rec["score"] = {"outcome": "ERROR", "violations": [], "scoring_error": f"{type(e).__name__}: {e}"}
    # An error never hides a violation that already happened; otherwise the run is ERROR.
    if "error" in rec and rec["score"]["outcome"] != "VIOLATION":
        rec["score"]["outcome"] = "ERROR"
    kw = _completion_kwargs(model)
    rec["settings"] = {
        "temperature": kw["temperature"],
        "max_tokens": kw["max_tokens"],
        "reasoning_max_tokens": kw.get("extra_body", {}).get("reasoning", {}).get("max_tokens", 0),
        "max_tool_calls": MAX_TOOL_CALLS,
    }
    pin, pout = price(model)
    rec["cost_usd"] = round(rec["prompt_tokens"] * pin + rec["completion_tokens"] * pout, 6)
    return rec


def run_suite(
    suite: str, agents: list[str], runs: int, model: str, out: str, cases: list[str] | None = None, client=None
) -> dict:
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    token_budget = int(os.environ.get("ARENA_TOKEN_BUDGET", "4000000"))
    usd_budget = float(os.environ.get("ARENA_USD_BUDGET", "10"))
    limiter = llm.RateLimiter(int(os.environ.get("ARENA_RPM", "20")))
    worker = os.environ.get("ARENA_WORKER", "")
    meta_f = out_dir / (f"run_meta_{worker}.json" if worker else "run_meta.json")
    meta = json.loads(meta_f.read_text(encoding="utf-8")) if meta_f.exists() else {"tokens": 0, "cost_usd": 0.0}
    kw = _completion_kwargs(model)
    meta.update(
        {
            "suite": suite,
            "agents": agents,
            "runs": runs,
            "model": model,
            "partial": False,
            "skipped": [],
            "temperature": kw["temperature"],
            "max_tokens": kw["max_tokens"],
            "reasoning_max_tokens": kw.get("extra_body", {}).get("reasoning", {}).get("max_tokens", 0),
            "max_tool_calls": MAX_TOOL_CALLS,
        }
    )
    for case in load_cases(suite, cases):
        for k in range(1, runs + 1):
            for agent in agents:
                f = out_dir / f"{agent}__{case['id']}__run{k}.json"
                if f.exists():
                    continue  # resumable
                lock = f.with_suffix(".lock")
                try:  # parallel workers: claim the run exclusively (stale locks: delete *.lock and rerun)
                    os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                except FileExistsError:
                    continue
                if meta["tokens"] >= token_budget or meta["cost_usd"] >= usd_budget:
                    lock.unlink(missing_ok=True)
                    meta["partial"] = True
                    meta["skipped"].append(f.name)
                    continue
                try:
                    rec = run_one(agent, case, k, model, out_dir, client=client, limiter=limiter)
                    f.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
                finally:
                    lock.unlink(missing_ok=True)  # only after the result exists, so no other worker re-claims it
                meta["tokens"] += rec["prompt_tokens"] + rec["completion_tokens"]
                meta["cost_usd"] = round(meta["cost_usd"] + rec["cost_usd"], 6)
                print(
                    f"{f.name}: {rec['score']['outcome']} calls={rec['tool_calls']} "
                    f"cost=${rec['cost_usd']:.4f}{' ERR ' + rec['error'][:120] if 'error' in rec else ''}",
                    flush=True,
                )
                meta_f.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    meta_f.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta
