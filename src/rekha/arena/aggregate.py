"""Aggregate per-run result JSONs into scorecard.json (schema: docs/SCORING.md)."""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def build_scorecard(run_dir: str | Path) -> dict:
    run_dir = Path(run_dir)
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(run_dir.glob("*__*__run*.json"))]
    by_agent: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        by_agent[r["agent"]].append(r)
    card = {"run_dir": str(run_dir), "models": sorted({r["model"] for r in runs}), "agents": {}}
    for agent, rs in sorted(by_agent.items()):
        attacks = [r for r in rs if r["kind"] == "attack" and r["score"]["outcome"] != "ERROR"]
        controls = [r for r in rs if r["kind"] == "control" and r["score"]["outcome"] != "ERROR"]
        errors = [r for r in rs if r["score"]["outcome"] == "ERROR"]
        errored_any = [r for r in rs if r["score"]["outcome"] == "ERROR" or r.get("error")]
        viol = [r for r in attacks if r["score"]["outcome"] == "VIOLATION"]
        types = Counter(v for r in attacks for v in r["score"]["violations"])
        ctrl_ok = [r for r in controls if r["score"]["outcome"] == "SAFE"]
        calls = [r["tool_calls"] for r in rs if r["score"]["outcome"] != "ERROR"]
        lat = [r["latency_ms"] for r in rs if r["score"]["outcome"] != "ERROR"]
        card["agents"][agent] = {
            "attack_runs": len(attacks), "violating_runs": len(viol),
            "violation_rate": round(len(viol) / len(attacks), 4) if attacks else None,
            "violations_by_type": dict(sorted(types.items())),
            "control_runs": len(controls), "control_success": len(ctrl_ok),
            "control_success_rate": round(len(ctrl_ok) / len(controls), 4) if controls else None,
            "total_runs": len(rs),
            "error_runs": len(errors),
            "error_rate": round(len(errors) / len(rs), 4) if rs else None,
            "runs_with_errors_incl_scored_violations": len(errored_any),
            "attack_runs_incl_errors": sum(r["kind"] == "attack" for r in rs),
            "control_runs_incl_errors": sum(r["kind"] == "control" for r in rs),
            "cost_usd": round(sum(r.get("cost_usd", 0) for r in rs), 4),
            "mean_tool_calls": round(statistics.mean(calls), 2) if calls else None,
            "p50_latency_ms": int(statistics.median(lat)) if lat else None,
            "prompt_tokens": sum(r.get("prompt_tokens", 0) for r in rs),
            "completion_tokens": sum(r.get("completion_tokens", 0) for r in rs),
            "by_case": _by_case(rs),
        }
    return card


def _by_case(rs: list[dict]) -> dict:
    out: dict[str, dict] = defaultdict(lambda: {"runs": 0, "violations": 0, "outcomes": []})
    for r in rs:
        c = out[r["case_id"]]
        c["runs"] += 1
        c["violations"] += r["score"]["outcome"] == "VIOLATION"
        c["outcomes"].append(r["score"]["outcome"])
    return dict(sorted(out.items()))


if __name__ == "__main__":
    import sys
    d = sys.argv[1]
    card = build_scorecard(d)
    Path(d, "scorecard.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(json.dumps({a: {k: v for k, v in s.items() if k != "by_case"} for a, s in card["agents"].items()}, indent=2))
