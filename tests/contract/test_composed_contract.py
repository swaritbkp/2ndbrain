"""Contract tests for the COMPOSED server (Synapse-generated or reference). Ground truth = DB state.

Point it at the server(s):  COMPOSED_SERVER=rebalance_switch_server.py  (comma-separate for Route B)
Validated here against scripts/reference_composed_server.py. Skips if COMPOSED_SERVER is unset.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import oob_code  # noqa: E402
from mcp_client import call_sequence, list_tools  # noqa: E402

SERVERS = [s.strip() for s in os.environ.get("COMPOSED_SERVER", "").split(",") if s.strip()]
pytestmark = pytest.mark.skipif(not SERVERS, reason="COMPOSED_SERVER not set")


def _env(db):
    return {k: os.environ[k] for k in ("REKHA_DB", "REKHA_AS_OF", "REKHA_NOW", "REKHA_TOKEN_SECRET")}


@pytest.fixture()
def surface(db):
    tools = {}
    for srv in SERVERS:
        for t in list_tools(srv, _env(db)):
            tools[t["name"]] = (srv, t)
    return tools


def _props(t):
    return list((t["inputSchema"] or {}).get("properties", {}).keys())


def _pick(props, *needles, exclude=()):
    for n in needles:
        for p in props:
            if n in p.lower() and not any(x in p.lower() for x in exclude):
                return p
    return None


def _tools(surface):
    """Return (preview_tool, confirm_tool); the same tool for Route A."""
    with_code = [n for n, (_, t) in surface.items() if _pick(_props(t), "code", exclude=("scheme",))]
    without = [n for n in surface if n not in with_code]
    confirm = with_code[0]
    preview = confirm if (len(surface) == 1 or not without) else without[0]
    return preview, confirm


def _args(surface, name, client, frm, to, units, cid=None, code=None):
    _, t = surface[name]
    props = _props(t)
    a = {}
    a[_pick(props, "client")] = client
    a[_pick(props, "from")] = frm
    a[_pick(props, "to_scheme", "to")] = to
    a[_pick(props, "unit")] = units
    if cid is not None:
        a[_pick(props, "confirmation_id", "_id")] = cid
    if code is not None:
        a[_pick(props, "code", exclude=("scheme",))] = code
    return {k: v for k, v in a.items() if k}


def _call(surface, db, name, args, env_over=None):
    srv, _ = surface[name]
    env = _env(db)
    env.update(env_over or {})
    return call_sequence(srv, [(name, args)], env)[0]


def _count(db, table):
    from rekha.engine.db import connect
    c = connect(db)
    try:
        return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        c.close()


def _cid(resp) -> str:
    m = re.search(r"CNF-[0-9A-F]{12}", json.dumps(resp))
    assert m, f"no confirmation id in preview: {resp}"
    return m.group(0)


def _preview(surface, db, client, frm, to, units):
    p, _ = _tools(surface)
    return _call(surface, db, p, _args(surface, p, client, frm, to, units))


def _confirm(surface, db, client, frm, to, units, cid, code, env_over=None):
    _, c = _tools(surface)
    return _call(surface, db, c, _args(surface, c, client, frm, to, units, cid, code), env_over)


# ---- surface ----
def test_surface_hides_primitives(surface):
    assert 1 <= len(surface) <= 2, f"expected 1 tool (Route A) or 2 (Route B), got {list(surface)}"
    assert not any(n in surface for n in ("execute_switch", "verify_confirmation", "request_confirmation"))


# ---- happy path + confirmation integrity ----
def test_preview_creates_confirmation_but_no_switch(surface, db):
    r = _preview(surface, db, "C001", "SAT-BLU", "SAT-FLX", "500")
    _cid(r)
    assert _count(db, "confirmations") == 1 and _count(db, "switches") == 0


def test_preview_never_leaks_code(surface, db):
    r = _preview(surface, db, "C001", "SAT-BLU", "SAT-FLX", "500")
    assert oob_code(db, _cid(r)) not in json.dumps(r)


def test_fake_code_does_not_commit(surface, db):
    cid = _cid(_preview(surface, db, "C001", "SAT-BLU", "SAT-FLX", "500"))
    _confirm(surface, db, "C001", "SAT-BLU", "SAT-FLX", "500", cid, "CONFIRMED")
    _confirm(surface, db, "C001", "SAT-BLU", "SAT-FLX", "500", cid, "000000")
    assert _count(db, "switches") == 0


def test_real_code_commits_exactly_once_and_replay_fails(surface, db):
    cid = _cid(_preview(surface, db, "C001", "SAT-BLU", "SAT-FLX", "500"))
    code = oob_code(db, cid)
    _confirm(surface, db, "C001", "SAT-BLU", "SAT-FLX", "500", cid, code)
    assert _count(db, "switches") == 1
    _confirm(surface, db, "C001", "SAT-BLU", "SAT-FLX", "500", cid, code)
    assert _count(db, "switches") == 1


def test_param_swap_rejected(surface, db):
    cid = _cid(_preview(surface, db, "C006", "SAT-SMC", "SAT-BLU", "100"))
    _confirm(surface, db, "C006", "SAT-SMC", "SAT-BLU", "1000", cid, oob_code(db, cid))
    assert _count(db, "switches") == 0


def test_expired_confirmation_rejected(surface, db):
    cid = _cid(_preview(surface, db, "C001", "SAT-BLU", "SAT-FLX", "500"))
    _confirm(surface, db, "C001", "SAT-BLU", "SAT-FLX", "500", cid, oob_code(db, cid), {"REKHA_NOW": "2026-11-23T15:30:00+05:30"})
    assert _count(db, "switches") == 0


# ---- hard blocks: no confirmation is even issued ----
@pytest.mark.parametrize("client,frm,to,units,hint", [
    ("C004", "SAT-FLX", "SAT-BLU", "10", "KYC"),
    ("C008", "SAT-FLX", "SAT-BLU", "10", "KYC"),
    ("C003", "SAT-HYB", "SAT-SMC", "100", "SAT-STD"),
    ("C002", "SAT-ELS", "SAT-BLU", "400", "200"),
])
def test_hard_blocks_issue_no_confirmation(surface, db, client, frm, to, units, hint):
    r = _preview(surface, db, client, frm, to, units)
    assert _count(db, "confirmations") == 0 and _count(db, "switches") == 0
    assert hint in json.dumps(r), f"block should explain / offer alternative ({hint}): {r}"


def test_cumulative_cap_blocks_second_order(surface, db):
    cid = _cid(_preview(surface, db, "C005", "SAT-FLX", "SAT-BLU", "15000"))
    _confirm(surface, db, "C005", "SAT-FLX", "SAT-BLU", "15000", cid, oob_code(db, cid))
    assert _count(db, "switches") == 1
    _preview(surface, db, "C005", "SAT-FLX", "SAT-BLU", "15000")
    assert _count(db, "confirmations") == 1


def test_recheck_at_commit_time(surface, db):
    """Two previews fit the cap separately; after the first commits, the second must be refused at commit."""
    c1 = _cid(_preview(surface, db, "C005", "SAT-FLX", "SAT-BLU", "15000"))
    c2 = _cid(_preview(surface, db, "C005", "SAT-FLX", "SAT-BLU", "15000"))
    _confirm(surface, db, "C005", "SAT-FLX", "SAT-BLU", "15000", c1, oob_code(db, c1))
    _confirm(surface, db, "C005", "SAT-FLX", "SAT-BLU", "15000", c2, oob_code(db, c2))
    assert _count(db, "switches") == 1


def test_soft_warnings_surface_in_preview(surface, db):
    r = json.dumps(_preview(surface, db, "C006", "SAT-SMC", "SAT-BLU", "1000")).upper()
    assert "EXIT" in r and ("SHORT" in r or "STCG" in r)


def test_injected_crm_note_is_ignored(surface, db):
    _preview(surface, db, "C007", "SAT-BLU", "SAT-FLX", "100")
    assert _count(db, "switches") == 0
