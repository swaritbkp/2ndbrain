"""Viewer data helpers (no Streamlit import, so they are unit-testable)."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DISCLAIMER = "Fictional data. Indicative estimate only. Not tax or investment advice."
EXTRAS = {
    "Mutation matrix": "mutation.json",
    "Adaptive lineage": "adaptive.json",
    "Economics": "economics.json",
    "Language parity": "language.json",
}


def sources() -> dict[str, Path]:
    """Label -> directory holding *__*__run*.json. Live results first, then the synthetic fixtures."""
    out: dict[str, Path] = {}
    res = ROOT / "results"
    if res.exists():
        for d in sorted((p for p in res.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True):
            if any(d.glob("*__*__run*.json")):
                out[f"results/{d.name}"] = d
    fx = ROOT / "fixtures" / "sample_results"
    if fx.exists():
        out["fixtures/sample_results (synthetic sample)"] = fx
    return out


def load_runs(d: Path) -> list[dict]:
    runs = []
    for p in sorted(Path(d).glob("*__*__run*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        r["_file"] = p.name
        runs.append(r)
    return runs


def load_scorecard(d: Path) -> dict | None:
    p = Path(d) / "scorecard.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    from rekha.arena.aggregate import build_scorecard

    return build_scorecard(d) if any(Path(d).glob("*__*__run*.json")) else None


def pair(runs: list[dict], case_id: str, k: int) -> dict[str, dict | None]:
    return {
        a: next((r for r in runs if r["agent"] == a and r["case_id"] == case_id and r["run"] == k), None)
        for a in ("baseline", "composed")
    }


def run_db(d: Path, run: dict) -> Path | None:
    p = Path(d) / "runs_db" / run["_file"].replace(".json", ".db")
    return p if p.exists() else None


def is_synthetic(runs: list[dict]) -> bool:
    return any(r.get("synthetic") for r in runs)


def demo_db() -> str:
    """A temp DB with one confirmed switch (seed + reference workflow), for the audit/receipt page."""
    sys.path.insert(0, str(ROOT / "data"))
    import seed  # noqa: PLC0415

    td = tempfile.mkdtemp(prefix="rekha_demo_")
    path = os.path.join(td, "demo.db")
    seed.seed(path)
    os.environ.update(
        {
            "REKHA_DB": path,
            "REKHA_AS_OF": os.environ.get("REKHA_AS_OF", "2026-11-23"),
            "REKHA_NOW": os.environ.get("REKHA_NOW", "2026-11-23T14:55:00+05:30"),
        }
    )
    os.environ.setdefault("REKHA_TOKEN_SECRET", "viewer-demo")
    from rekha.engine.workflow import rebalance_switch as RS  # noqa: PLC0415

    p = RS("C001", "SAT-BLU", "SAT-FLX", "500")
    conn = sqlite3.connect(path)
    code = conn.execute("SELECT code FROM oob_outbox WHERE confirmation_id=?", (p["confirmation_id"],)).fetchone()[0]
    conn.close()
    RS("C001", "SAT-BLU", "SAT-FLX", "500", p["confirmation_id"], code)
    return path


def audit_rows(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [
            dict(r) for r in conn.execute("SELECT id, ts, client_id, action, code, row_hash FROM audit_log ORDER BY id")
        ]
    finally:
        conn.close()


def tamper_copy(db_path: str, row_id: int | None = None) -> tuple[str, int | None]:
    """Copy the DB and edit one audit row's detail (default: the last row); returns (copy path, edited id)."""
    td = tempfile.mkdtemp(prefix="rekha_tamper_")
    dst = os.path.join(td, "tampered.db")
    shutil.copyfile(db_path, dst)
    conn = sqlite3.connect(dst)
    try:
        q = "SELECT id, detail_json FROM audit_log " + ("WHERE id=?" if row_id else "ORDER BY id DESC LIMIT 1")
        row = conn.execute(q, (row_id,) if row_id else ()).fetchone()
        if not row:
            return dst, None
        d = json.loads(row[1])
        d["units"] = "9999" if "units" in d else d.get("units")
        d["tampered"] = True
        conn.execute("UPDATE audit_log SET detail_json=? WHERE id=?", (json.dumps(d), row[0]))
        conn.commit()
        return dst, row[0]
    finally:
        conn.close()


def extras(d: Path) -> dict[str, dict]:
    out = {}
    for label, fname in EXTRAS.items():
        for base in (Path(d), ROOT / "results" / "latest"):
            p = base / fname
            if p.exists():
                out[label] = json.loads(p.read_text(encoding="utf-8"))
                break
    return out


def kpis(d: Path) -> dict | None:
    """Headline deltas for the KPI strip: violations, controls, tool calls, schema tokens (economics.json if present)."""
    card = load_scorecard(d)
    if not card or not {"baseline", "composed"} <= set(card["agents"]):
        return None
    b, c = card["agents"]["baseline"], card["agents"]["composed"]
    econ = {}
    for base in (Path(d), ROOT / "results" / "latest"):
        p = base / "economics.json"
        if p.exists():
            econ = json.loads(p.read_text(encoding="utf-8")).get("agents", {})
            break
    return {
        "attack": (f"{b['violating_runs']}/{b['attack_runs']}", f"{c['violating_runs']}/{c['attack_runs']}"),
        "controls": (f"{b['control_success']}/{b['control_runs']}", f"{c['control_success']}/{c['control_runs']}"),
        "calls": (b.get("mean_tool_calls"), c.get("mean_tool_calls")),
        "schema": (
            econ.get("baseline", {}).get("schema_tokens_per_request"),
            econ.get("composed", {}).get("schema_tokens_per_request"),
        ),
        "errors": (b.get("error_runs", 0), c.get("error_runs", 0)),
    }


def why(rec: dict) -> list[str]:
    """Plain-language reasons for a run's outcome, from the score and the tool results (no model text)."""
    out = [
        f"{e['code']} on switch {e.get('switch_id', e.get('audit_id', '?'))}"
        for e in rec["score"].get("violation_events", [])
    ]
    for t in rec["turns"]:
        r = t.get("result") if t["role"] == "tool" else None
        if isinstance(r, dict) and r.get("status") in ("BLOCKED", "REJECTED"):
            codes = r.get("reasons") or [r.get("code")]
            out.append(f"{t['tool']} → {r['status']} ({', '.join(str(x) for x in codes if x)})")
        elif isinstance(r, dict) and r.get("status") in ("COMMITTED", "EXECUTED"):
            out.append(f"{t['tool']} → {r['status']} {r.get('switch_id', '')}".strip())
    if rec["score"]["outcome"] == "FALSE_BLOCK":
        out.append("control expected a commit; none happened")
    return out or ["no state change"]


def case_titles() -> dict[str, str]:
    try:
        from rekha.arena.runner import load_cases

        return {c["id"]: c.get("title", "") for c in load_cases("all")}
    except Exception:  # noqa: BLE001 (viewer must render without the arena package)
        return {}
