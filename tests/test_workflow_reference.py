"""Behaviour of the reference composed workflow. A Synapse-composed tool must match (see tests/contract/)."""
from __future__ import annotations

from conftest import oob_code
from rekha.engine.workflow import rebalance_switch as RS


def test_preview_then_commit_with_human_code(db):
    p = RS("C001", "SAT-BLU", "SAT-FLX", "500")
    assert p["status"] == "PREVIEW" and p["confirmation_id"]
    c = RS("C001", "SAT-BLU", "SAT-FLX", "500", p["confirmation_id"], oob_code(db, p["confirmation_id"]))
    assert c["status"] == "COMMITTED"


def test_fake_code_rejected(db):
    p = RS("C001", "SAT-BLU", "SAT-FLX", "500")
    assert RS("C001", "SAT-BLU", "SAT-FLX", "500", p["confirmation_id"], "CONFIRMED")["status"] == "REJECTED"


def test_param_swap_rejected(db):
    p = RS("C006", "SAT-SMC", "SAT-BLU", "100")
    code = oob_code(db, p["confirmation_id"])
    r = RS("C006", "SAT-SMC", "SAT-BLU", "1000", p["confirmation_id"], code)
    assert r["status"] == "REJECTED" and r["code"] == "CONFIRMATION_PARAM_MISMATCH"


def test_replay_rejected(db):
    p = RS("C001", "SAT-BLU", "SAT-FLX", "100")
    code = oob_code(db, p["confirmation_id"])
    assert RS("C001", "SAT-BLU", "SAT-FLX", "100", p["confirmation_id"], code)["status"] == "COMMITTED"
    assert RS("C001", "SAT-BLU", "SAT-FLX", "100", p["confirmation_id"], code)["code"] == "CONFIRMATION_USED"


def test_suitability_block_has_alternatives(db):
    r = RS("C003", "SAT-HYB", "SAT-SMC", "100")
    assert r["status"] == "BLOCKED" and "SUITABILITY_BREACH" in r["reasons"]
    assert r["helpful_alternative"]["suitable_schemes"] == ["SAT-STD", "SAT-LIQ"]


def test_lockin_partial_offers_unlocked_units(db):
    r = RS("C002", "SAT-ELS", "SAT-BLU", "400")
    assert r["status"] == "BLOCKED" and r["helpful_alternative"]["lockin"]["switch_units_now"] == "200.000"


def test_kyc_blocks(db):
    assert "KYC_INVALID" in RS("C004", "SAT-FLX", "SAT-BLU", "10")["reasons"]
    assert "KYC_EXPIRED" in RS("C008", "SAT-FLX", "SAT-BLU", "10")["reasons"]


def test_split_order_blocked_by_cumulative_cap(db):
    p = RS("C005", "SAT-FLX", "SAT-BLU", "15000")
    assert RS("C005", "SAT-FLX", "SAT-BLU", "15000", p["confirmation_id"], oob_code(db, p["confirmation_id"]))["status"] == "COMMITTED"
    r = RS("C005", "SAT-FLX", "SAT-BLU", "15000")
    assert r["status"] == "BLOCKED" and "DAILY_CAP_EXCEEDED" in r["reasons"]


def test_warnings_shown_for_exit_load_and_stcg(db):
    p = RS("C006", "SAT-SMC", "SAT-BLU", "1000")
    assert p["status"] == "PREVIEW"
    joined = " ".join(p["warnings"])
    assert "EXIT_LOAD" in joined and "SHORT_TERM_GAIN" in joined


def test_injected_note_does_not_skip_confirmation(db):
    assert RS("C007", "SAT-BLU", "SAT-FLX", "100")["status"] == "PREVIEW"


def test_receipt_renders(db):
    from rekha.engine.receipt import render_receipt
    RS("C001", "SAT-BLU", "SAT-FLX", "10")
    html = render_receipt(1, db)
    assert "Rekha Receipt #1" in html and "chain intact" in html
