"""Reference composition of the 12 functions into ONE guarded workflow.

Used as (1) the oracle for contract tests, so a Synapse-composed tool must behave like this, and
(2) Route C in docs/FALLBACKS.md, if Synapse Custom mode can't compose the logic itself.
It calls ONLY the public functions, the same surface Synapse composes.
"""
from __future__ import annotations

from decimal import Decimal

from . import functions as F
from ._core import DISCLAIMER, rupees


def rebalance_switch(client_id: str, from_scheme: str, to_scheme: str, units: str,
                     confirmation_id: str = "", confirmation_code: str = "") -> dict:
    """Switch units between two schemes for a client, with every compliance check and human confirmation built in.

    Call 1 (no confirmation_code): runs all checks. Returns BLOCKED (reasons + safe alternative) or PREVIEW
    (impact, warnings, confirmation_id). A one-time code goes to the RM console; ask the user to read it out.
    Call 2 (confirmation_id + confirmation_code from the user): re-runs every check, verifies the code
    (bound to these exact parameters, single use), then executes. Natural-language consent is never enough.
    """
    prof = F.get_client_profile(client_id)
    if not prof.get("ok"):
        return {"status": "BLOCKED", "reasons": [prof.get("code")], "message": prof.get("message")}
    reasons, warnings, alt = [], [], {}

    kyc = F.verify_kyc(client_id)
    if not kyc["kyc_valid"]:
        reasons.append(kyc["block_code"])
        alt["kyc"] = "Complete KYC re-verification before any transaction."

    lock = F.check_lockin(client_id, from_scheme, units)
    if not lock.get("ok"):
        reasons.append(lock["code"])
        if lock["code"] == "INSUFFICIENT_UNITS":
            alt["units"] = f"Client holds {lock.get('held_units')} units of {from_scheme}."
        return {"status": "BLOCKED", "reasons": reasons, "helpful_alternative": alt, "disclaimer": DISCLAIMER}
    if not lock["allowed"]:
        reasons.append(lock["code"])
        if Decimal(lock["unlocked_units"]) > 0:
            alt["lockin"] = {"switch_units_now": lock["unlocked_units"], "next_unlock_date": lock["next_unlock_date"]}
        else:
            alt["lockin"] = {"next_unlock_date": lock["next_unlock_date"]}

    suit = F.check_suitability(client_id, to_scheme)
    if not suit.get("ok"):
        return {"status": "BLOCKED", "reasons": reasons + [suit["code"]], "disclaimer": DISCLAIMER}
    if not suit["suitable"]:
        reasons.append(suit["block_code"])
        alt["suitable_schemes"] = suit["suitable_alternatives"]

    load = F.compute_exit_load(client_id, from_scheme, units)
    value = load["redemption_value_paise"]
    cap = F.check_daily_limit(client_id, value)
    if not cap["within_limit"]:
        reasons.append(cap["block_code"])
        alt["daily_cap"] = {"remaining_today": rupees(cap["remaining_paise"])}

    if reasons:
        return {"status": "BLOCKED", "reasons": reasons, "helpful_alternative": alt, "disclaimer": DISCLAIMER}

    tax = F.estimate_capital_gains_tax(client_id, from_scheme, units)
    out_cut = F.check_cutoff(from_scheme, "redemption")
    in_cut = F.check_cutoff(to_scheme, "purchase")
    if load["exit_load_paise"] > 0:
        warnings.append(f"EXIT_LOAD: {rupees(load['exit_load_paise'])}")
    if tax["short_term_gain_paise"] > 0:
        warnings.append(f"SHORT_TERM_GAIN: {rupees(tax['short_term_gain_paise'])}")
    if tax["taxable_ltcg_paise"] > 0:
        warnings.append(f"LTCG_ABOVE_EXEMPTION: {rupees(tax['taxable_ltcg_paise'])}")
    if out_cut["after_cutoff"] or in_cut["after_cutoff"]:
        warnings.append(f"AFTER_CUTOFF: NAV date {out_cut['nav_date']} (out) / {in_cut['nav_date']} (in)")
    impact = {"switch_out_value": rupees(value), "exit_load": rupees(load["exit_load_paise"]),
              "estimated_tax": rupees(tax["est_tax_paise"]), "nav_date_out": out_cut["nav_date"],
              "nav_date_in": in_cut["nav_date"], "tax_assumptions": tax["assumptions"]}

    if not confirmation_code:
        req = F.request_confirmation(client_id, from_scheme, to_scheme, units)
        if not req.get("ok"):
            return {"status": "BLOCKED", "reasons": [req["code"]], "disclaimer": DISCLAIMER}
        return {"status": "PREVIEW", "impact": impact, "warnings": warnings,
                "confirmation_id": req["confirmation_id"], "expires_at": req["expires_at"],
                "next_step": "Show this impact to the user. Ask them to read the 6-digit code from the RM console, "
                             "then call again with confirmation_id and confirmation_code.",
                "disclaimer": DISCLAIMER}

    ver = F.verify_confirmation(confirmation_id, confirmation_code, client_id, from_scheme, to_scheme, units)
    if not ver.get("verified"):
        return {"status": "REJECTED", "code": ver.get("reason"), "attempts_left": ver.get("attempts_left"),
                "disclaimer": DISCLAIMER}
    ex = F.execute_switch(client_id, from_scheme, to_scheme, units)
    if not ex.get("ok"):
        return {"status": "REJECTED", "code": ex.get("code"), "message": ex.get("message")}
    return {"status": "COMMITTED", "switch_id": ex["switch_id"], "impact": impact, "warnings": warnings,
            "in_units": ex["in_units"], "disclaimer": DISCLAIMER}
