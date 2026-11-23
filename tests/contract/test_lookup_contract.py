"""Contract tests for the READ-ONLY discovery server (lookup_holdings). Ground truth = DB state.

Principle: separate read-only discovery from write-path containment. The lookup server runs as its own MCP process,
next to the preview/confirm write pair (COMPOSED_SERVER). It must never mutate state, never expose an OTP, never
return untrusted CRM free text, and never expose a write primitive.
Server: LOOKUP_SERVER env, else state/lookup_server.txt.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from mcp_client import call_sequence, list_tools  # noqa: E402

_state = ROOT / "state" / "lookup_server.txt"
SERVER = os.environ.get("LOOKUP_SERVER", "").strip() or (_state.read_text(encoding="utf-8").strip() if _state.exists() else "")
pytestmark = pytest.mark.skipif(not SERVER, reason="no lookup server configured")
WRITE_PRIMITIVES = {"execute_switch", "verify_confirmation", "request_confirmation", "confirm_rebalance_switch",
                    "preview_rebalance_switch"}
CLIENTS = ["C001", "C002", "C003", "C004", "C005", "C006", "C007", "C008", "C999"]


def _env(db):
    return {k: os.environ[k] for k in ("REKHA_DB", "REKHA_AS_OF", "REKHA_NOW", "REKHA_TOKEN_SECRET")}


def _db_digest(path: str) -> str:
    conn = sqlite3.connect(path)
    try:
        h = hashlib.sha256()
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            h.update(name.encode())
            for row in conn.execute(f"SELECT * FROM {name} ORDER BY rowid"):  # noqa: S608 (table names from schema)
                h.update(repr(row).encode())
        return h.hexdigest()
    finally:
        conn.close()


def _lookup_all(db):
    return call_sequence(SERVER, [("lookup_holdings", {"client_id": c}) for c in CLIENTS], _env(db))


def test_surface_is_one_read_only_tool(db):
    tools = list_tools(SERVER, _env(db))
    assert [t["name"] for t in tools] == ["lookup_holdings"]
    assert set(tools[0]["inputSchema"]["properties"]) == {"client_id"}
    assert not WRITE_PRIMITIVES & {t["name"] for t in tools}


def test_lookup_never_mutates_state(db):
    before = _db_digest(db)
    out = _lookup_all(db)
    assert _db_digest(db) == before, "lookup_holdings changed DB state"
    assert out[-1]["status"] == "NOT_FOUND" and all(r["status"] == "OK" for r in out[:-1])


def test_lookup_never_exposes_otp(db):
    from rekha.engine import functions as F
    cid = F.request_confirmation("C001", "SAT-BLU", "SAT-FLX", "10")["confirmation_id"]
    conn = sqlite3.connect(db)
    code = conn.execute("SELECT code FROM oob_outbox WHERE confirmation_id=?", (cid,)).fetchone()[0]
    conn.close()
    blob = json.dumps(_lookup_all(db))
    assert code not in blob and cid not in blob and "oob" not in blob.lower()


def test_lookup_omits_untrusted_crm_notes(db):
    conn = sqlite3.connect(db)
    notes = [n for (n,) in conn.execute("SELECT notes FROM clients WHERE notes IS NOT NULL AND notes != ''")]
    conn.close()
    blob = json.dumps(_lookup_all(db))
    assert "notes" not in blob.lower()
    assert notes and not any(n[:40] in blob for n in notes)


def test_lookup_resolves_k02_unlocked_elss_tranche(db):
    r = call_sequence(SERVER, [("lookup_holdings", {"client_id": "C002"})], _env(db))[0]
    els = next(h for h in r["holdings"] if h["scheme_code"] == "SAT-ELS")
    assert els["units"].startswith("400") and els["unlocked_units"].startswith("200")
    assert els["locked_units"].startswith("200") and els["next_unlock_date"] == "2027-01-15"
    assert r["read_only"] is True
