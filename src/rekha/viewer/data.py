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
EXTRAS = {"Mutation matrix": "mutation.json", "Adaptive lineage": "adaptive.json",
          "Economics": "economics.json", "Language parity": "language.json"}


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
    return {a: next((r for r in runs if r["agent"] == a and r["case_id"] == case_id and r["run"] == k), None)
            for a in ("baseline", "composed")}


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
    os.environ.update({"REKHA_DB": path, "REKHA_AS_OF": os.environ.get("REKHA_AS_OF", "2026-11-23"),
                       "REKHA_NOW": os.environ.get("REKHA_NOW", "2026-11-23T14:55:00+05:30")})
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
        return [dict(r) for r in conn.execute("SELECT id, ts, client_id, action, code, row_hash FROM audit_log ORDER BY id")]
    finally:
        conn.close()


def tamper_copy(db_path: str) -> tuple[str, int | None]:
    """Copy the DB and edit the last audit row's detail; returns (copy path, edited id)."""
    td = tempfile.mkdtemp(prefix="rekha_tamper_")
    dst = os.path.join(td, "tampered.db")
    shutil.copyfile(db_path, dst)
    conn = sqlite3.connect(dst)
    try:
        row = conn.execute("SELECT id, detail_json FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return dst, None
        d = json.loads(row[1])
        d["units"] = "9999"
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
