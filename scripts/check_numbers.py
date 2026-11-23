"""Deterministic number check: every published metric must be recomputable from the raw run JSONs.

1. For each results folder with a scorecard.json, rebuild the scorecard from the *__run*.json files and require
   equality (ignoring run_dir).
2. --rescore: re-score every run whose DB snapshot exists (runs_db/<run>.db vs runs_db/pristine.db) with
   scorer.score_run and require the stored outcome/violations to match. Works on copies; evidence DBs untouched.
3. Write results/latest/metrics.json (the headline numbers docs cite) and require that README.md and
   results/latest/SUMMARY.md contain the headline attack/control fractions.
python scripts/check_numbers.py [--rescore]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "data")]
from rekha.arena.aggregate import build_scorecard  # noqa: E402

RES = ROOT / "results"


def _strip(card: dict) -> dict:
    return {k: v for k, v in card.items() if k != "run_dir"}


def check_scorecards() -> list[str]:
    bad = []
    for sc in sorted(RES.rglob("scorecard.json")):
        d = sc.parent
        if not any(d.glob("*__*__run*.json")):
            continue
        stored, rebuilt = json.loads(sc.read_text(encoding="utf-8")), build_scorecard(d)
        if _strip(stored) != _strip(rebuilt):
            bad.append(f"{sc.relative_to(ROOT)} differs from a rebuild from its run JSONs")
    return bad


def rescore() -> tuple[int, list[str]]:
    from rekha.arena.runner import load_cases
    from rekha.arena.scorer import score_run

    cases = {c["id"]: c for c in load_cases("all")}
    n, bad = 0, []
    for f in sorted(RES.rglob("*__run*.json")):
        db, pre = f.parent / "runs_db" / f.name.replace(".json", ".db"), f.parent / "runs_db" / "pristine.db"
        rec = json.loads(f.read_text(encoding="utf-8"))
        case = cases.get(rec["case_id"])
        if not (db.exists() and pre.exists() and case) or rec.get("synthetic"):
            continue
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td, "post.db"), Path(td, "pre.db")
            shutil.copyfile(db, a)
            shutil.copyfile(pre, b)
            s = score_run(str(a), str(b), case, rec.get("disclosed_confirmation_ids", []))
        stored = rec["score"]
        want = stored["outcome"] if stored["outcome"] != "ERROR" else s["outcome"]
        if (s["outcome"], s["violations"]) != (want, stored["violations"]):
            bad.append(
                f"{f.relative_to(ROOT)}: stored {stored['outcome']} {stored['violations']} vs rescored "
                f"{s['outcome']} {s['violations']}"
            )
        n += 1
    return n, bad


def metrics() -> dict:
    card = json.loads((RES / "latest" / "scorecard.json").read_text(encoding="utf-8"))["agents"]
    econ = json.loads((RES / "latest" / "economics.json").read_text(encoding="utf-8"))["agents"]
    out = {}
    for a in ("baseline", "composed"):
        s = card[a]
        out[a] = {
            "attack": f"{s['violating_runs']} / {s['attack_runs']}",
            "controls": f"{s['control_success']} / {s['control_runs']}",
            "errors": f"{s['error_runs']} / {s['total_runs']}",
            "mean_tool_calls": s["mean_tool_calls"],
            "schema_tokens": econ[a]["schema_tokens_per_request"],
            "cost_usd": s["cost_usd"],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rescore", action="store_true")
    a = ap.parse_args()
    bad = check_scorecards()
    if a.rescore:
        n, b2 = rescore()
        print(f"rescored {n} runs, {len(b2)} mismatches")
        bad += b2
    if (RES / "latest" / "economics.json").exists():
        m = metrics()
        (RES / "latest" / "metrics.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
        for doc in ("README.md", "results/latest/SUMMARY.md"):
            if not (ROOT / doc).exists():
                bad.append(f"{doc} is missing")
                continue
            text = (ROOT / doc).read_text(encoding="utf-8")
            for agent in ("baseline", "composed"):
                for key in ("attack", "controls"):
                    if m[agent][key] not in text:
                        bad.append(f"{doc} lacks {agent} {key} = '{m[agent][key]}' from results/latest")
        print(json.dumps(m))
    for b in bad:
        print("FAIL:", b)
    print("numbers OK" if not bad else f"{len(bad)} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
