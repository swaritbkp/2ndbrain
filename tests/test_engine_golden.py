"""Golden tests for the 12 engine functions. These encode the spec: if an edit breaks one, the edit is wrong."""
from __future__ import annotations

import inspect

import pytest

from conftest import oob_code
from rekha.engine import _core as C
from rekha.engine import functions as F


def test_public_surface_is_exactly_12_typed_functions():
    assert len(F.PUBLIC_FUNCTIONS) == 12
    for name in F.PUBLIC_FUNCTIONS:
        fn = getattr(F, name)
        sig = inspect.signature(fn)
        assert fn.__doc__ and len(fn.__doc__.strip().splitlines()[0]) > 10, name
        for p in sig.parameters.values():
            assert p.annotation in ("str", "int"), f"{name}.{p.name} must be str/int"


def test_rupees_indian_format():
    assert C.rupees(50000000) == "₹5,00,000.00"
    assert C.rupees(123456789) == "₹12,34,567.89"
    assert C.rupees(99) == "₹0.99"


# 1 profile
def test_profile_ok_and_notes_untrusted(db):
    r = F.get_client_profile("C007")
    assert r["ok"] and r["client"]["risk_profile"] == "MODERATE"
    assert "SYSTEM:" in r["notes_untrusted"] and "untrusted" in r["notes_warning"]


def test_profile_unknown(db):
    assert F.get_client_profile("C999")["code"] == "UNKNOWN_CLIENT"


# 2 kyc
@pytest.mark.parametrize("cid,valid,code", [("C001", True, None), ("C004", False, "KYC_INVALID"), ("C008", False, "KYC_EXPIRED")])
def test_kyc(db, cid, valid, code):
    r = F.verify_kyc(cid)
    assert r["kyc_valid"] is valid and r["block_code"] == code


def test_kyc_mutant(db, monkeypatch):
    monkeypatch.setenv("REKHA_MUTANT", "no_kyc")
    assert F.verify_kyc("C004")["kyc_valid"] is True


# 3 drift
def test_drift_sums_to_100(db):
    r = F.compute_drift("C001")
    assert abs(sum(r["current_pct"].values()) - 100) < 0.05
    assert set(r["drift_pp"]) == {"EQUITY", "DEBT", "GOLD"}


# 4 lock-in
def test_lockin_partial(db):
    r = F.check_lockin("C002", "SAT-ELS", "400")
    assert r["code"] == "LOCKIN_PARTIAL" and not r["allowed"]
    assert r["unlocked_units"] == "200.000" and r["locked_units"] == "200.000" and r["next_unlock_date"] == "2027-01-15"


def test_lockin_ok_for_unlocked_units(db):
    assert F.check_lockin("C002", "SAT-ELS", "200")["code"] == "LOCKIN_OK"


def test_lockin_non_elss_always_ok(db):
    assert F.check_lockin("C001", "SAT-BLU", "1200")["allowed"]


def test_lockin_errors(db):
    assert F.check_lockin("C002", "SAT-ELS", "401")["code"] == "INSUFFICIENT_UNITS"
    assert F.check_lockin("C002", "SAT-ELS", "-5")["code"] == "BAD_UNITS"
    assert F.check_lockin("C002", "NOPE", "5")["code"] == "UNKNOWN_SCHEME"


def test_lockin_mutant(db, monkeypatch):
    monkeypatch.setenv("REKHA_MUTANT", "no_lockin")
    assert F.check_lockin("C002", "SAT-ELS", "400")["allowed"]


# 5 exit load
def test_exit_load_none_after_a_year(db):
    r = F.compute_exit_load("C001", "SAT-BLU", "500")
    assert r["exit_load_paise"] == 0 and r["redemption_value_paise"] == 4211500


def test_exit_load_one_percent_within_year(db):
    r = F.compute_exit_load("C006", "SAT-SMC", "1000")
    assert r["redemption_value_paise"] == 15542000 and r["exit_load_paise"] == 155420


def test_exit_load_liquid_graded(db):
    r = F.compute_exit_load("C001", "SAT-LIQ", "10")   # held 2 days -> 0.0065%
    assert r["exit_load_paise"] == 185


# 6 tax
def test_tax_ltcg_within_exemption_is_zero(db):
    r = F.estimate_capital_gains_tax("C001", "SAT-BLU", "500")
    assert r["long_term_gain_paise"] == 1161500 and r["est_tax_paise"] == 0


def test_tax_stcg_equity(db):
    r = F.estimate_capital_gains_tax("C006", "SAT-SMC", "1000")
    assert r["short_term_gain_paise"] == 2542000 and r["est_tax_paise"] == 528736   # 20% + 4% cess


def test_tax_ltcg_exemption_already_used(db):
    r = F.estimate_capital_gains_tax("C005", "SAT-FLX", "15000")
    assert r["taxable_ltcg_paise"] == 13125000 and r["est_tax_paise"] == 1706250   # 12.5% + 4% cess


def test_tax_debt_at_assumed_slab(db):
    r = F.estimate_capital_gains_tax("C001", "SAT-STD", "1000")
    assert r["tax_class"] == "debt_specified" and r["est_tax_paise"] == round(1000 * 288 * 0.30 * 1.04)


# 7 suitability
def test_suitability_breach_with_alternatives(db):
    r = F.check_suitability("C003", "SAT-SMC")
    assert not r["suitable"] and r["block_code"] == "SUITABILITY_BREACH"
    assert r["suitable_alternatives"] == ["SAT-STD", "SAT-LIQ"]


def test_suitability_ok(db):
    assert F.check_suitability("C001", "SAT-FLX")["suitable"]


# 8 daily cap
def test_daily_cap_counts_executed_switches(db):
    assert F.check_daily_limit("C005", 85125000)["within_limit"]
    assert F.execute_switch("C005", "SAT-FLX", "SAT-BLU", "15000")["ok"]
    r = F.check_daily_limit("C005", 85125000)
    assert not r["within_limit"] and r["used_today_paise"] == 85125000 and r["block_code"] == "DAILY_CAP_EXCEEDED"


# 9 cut-off
def test_cutoff_before_and_after(db):
    assert F.check_cutoff("SAT-BLU", "redemption") == {"ok": True, "after_cutoff": False, "nav_date": "2026-11-23", "cutoff": "15:00"}
    r = F.check_cutoff("SAT-LIQ", "purchase")
    assert r["after_cutoff"] and r["nav_date"] == "2026-11-24" and r["cutoff"] == "13:30"


def test_cutoff_weekend(db):
    r = F.check_cutoff("SAT-BLU", "redemption", "2026-11-28T10:00:00+05:30")   # Saturday
    assert r["after_cutoff"] and r["nav_date"] == "2026-11-30"


# 10/11 confirmation
def _req(cid="C001", f="SAT-BLU", t="SAT-FLX", u="500"):
    r = F.request_confirmation(cid, f, t, u)
    assert r["ok"]
    return r["confirmation_id"]


def test_request_never_returns_code(db):
    r = F.request_confirmation("C001", "SAT-BLU", "SAT-FLX", "500")
    flat = str(r)
    code = oob_code(db, r["confirmation_id"])
    assert code not in flat and len(code) == 6


def test_verify_right_code_then_replay_rejected(db):
    cid = _req()
    code = oob_code(db, cid)
    assert F.verify_confirmation(cid, code, "C001", "SAT-BLU", "SAT-FLX", "500")["verified"]
    assert F.verify_confirmation(cid, code, "C001", "SAT-BLU", "SAT-FLX", "500")["reason"] == "CONFIRMATION_USED"


def test_verify_param_mismatch(db):
    cid = _req()
    code = oob_code(db, cid)
    assert F.verify_confirmation(cid, code, "C001", "SAT-BLU", "SAT-FLX", "1000")["reason"] == "CONFIRMATION_PARAM_MISMATCH"


def test_verify_wrong_code_locks_after_three(db):
    cid = _req()
    for _ in range(3):
        r = F.verify_confirmation(cid, "000000", "C001", "SAT-BLU", "SAT-FLX", "500")
    assert r["status"] == "LOCKED"
    assert F.verify_confirmation(cid, oob_code(db, cid), "C001", "SAT-BLU", "SAT-FLX", "500")["reason"] == "CONFIRMATION_LOCKED"


def test_verify_expired(db, monkeypatch):
    cid = _req()
    code = oob_code(db, cid)
    monkeypatch.setenv("REKHA_NOW", "2026-11-23T15:20:00+05:30")
    assert F.verify_confirmation(cid, code, "C001", "SAT-BLU", "SAT-FLX", "500")["reason"] == "CONFIRMATION_EXPIRED"


def test_verify_unknown(db):
    assert F.verify_confirmation("CNF-NOPE", "123456", "C001", "SAT-BLU", "SAT-FLX", "500")["reason"] == "CONFIRMATION_UNKNOWN"


@pytest.mark.parametrize("mutant,call", [
    ("no_code_check", lambda cid, code: F.verify_confirmation(cid, "000000", "C001", "SAT-BLU", "SAT-FLX", "500")),
    ("no_param_binding", lambda cid, code: F.verify_confirmation(cid, code, "C001", "SAT-BLU", "SAT-FLX", "900")),
])
def test_confirmation_mutants_weaken(db, monkeypatch, mutant, call):
    cid = _req()
    code = oob_code(db, cid)
    monkeypatch.setenv("REKHA_MUTANT", mutant)
    assert call(cid, code)["verified"]


def test_single_use_mutant(db, monkeypatch):
    cid = _req()
    code = oob_code(db, cid)
    F.verify_confirmation(cid, code, "C001", "SAT-BLU", "SAT-FLX", "500")
    monkeypatch.setenv("REKHA_MUTANT", "no_single_use")
    assert F.verify_confirmation(cid, code, "C001", "SAT-BLU", "SAT-FLX", "500")["verified"]


# 12 execute
def test_execute_moves_units_fifo_and_audits(db):
    r = F.execute_switch("C002", "SAT-ELS", "SAT-BLU", "150")
    assert r["ok"]
    from rekha.engine.db import connect
    conn = connect(db)
    lots = conn.execute("SELECT allotment_date, units FROM lots WHERE client_id='C002' AND scheme_code='SAT-ELS' ORDER BY allotment_date").fetchall()
    conn.close()
    assert [(x[0], x[1]) for x in lots][0] == ("2023-03-15", "50.000")   # oldest lot fully consumed first
    assert C.verify_audit_chain(db)["valid"]


def test_execute_platform_rejects_locked_elss(db):
    assert F.execute_switch("C002", "SAT-ELS", "SAT-BLU", "300")["code"] == "PLATFORM_REJECTED_LOCKIN"


def test_execute_does_not_check_distributor_rules(db):
    """By design: KYC/suitability/cap/confirmation are the orchestrator's job."""
    assert F.execute_switch("C004", "SAT-FLX", "SAT-BLU", "10")["ok"]          # KYC on hold, still executes
    assert F.execute_switch("C003", "SAT-HYB", "SAT-SMC", "10")["ok"]          # unsuitable, still executes


def test_audit_chain_detects_tamper(db):
    F.execute_switch("C001", "SAT-BLU", "SAT-FLX", "10")
    F.execute_switch("C001", "SAT-BLU", "SAT-FLX", "10")
    from rekha.engine.db import connect
    conn = connect(db)
    conn.execute("UPDATE audit_log SET detail_json='{}' WHERE id=1")
    conn.close()
    r = C.verify_audit_chain(db)
    assert r["valid"] is False and r["broken_at_id"] == 1
