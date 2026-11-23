"""Baseline: the SAME 12 engine functions as 12 HTTP routes, a thin pass-through with no orchestration.

This is what naive exposure gives you (e.g. Synapse Auto over the internal API). Route docstrings are
the engine docstrings verbatim (fairness rule). Run: uvicorn rekha.baseline.api:app --port 8765
"""
from __future__ import annotations

from fastapi import FastAPI

from rekha.engine import functions as F

app = FastAPI(title="Satluj desk internal API (baseline)", version="1.0")


def _doc(fn):
    def deco(route):
        route.__doc__ = fn.__doc__
        return route
    return deco


@app.get("/clients/{client_id}")
@_doc(F.get_client_profile)
def get_client_profile(client_id: str) -> dict:
    return F.get_client_profile(client_id)


@app.get("/clients/{client_id}/kyc")
@_doc(F.verify_kyc)
def verify_kyc(client_id: str, as_of: str = "") -> dict:
    return F.verify_kyc(client_id, as_of)


@app.get("/clients/{client_id}/drift")
@_doc(F.compute_drift)
def compute_drift(client_id: str) -> dict:
    return F.compute_drift(client_id)


@app.get("/clients/{client_id}/lockin")
@_doc(F.check_lockin)
def check_lockin(client_id: str, scheme_code: str, units: str, as_of: str = "") -> dict:
    return F.check_lockin(client_id, scheme_code, units, as_of)


@app.get("/clients/{client_id}/exit-load")
@_doc(F.compute_exit_load)
def compute_exit_load(client_id: str, scheme_code: str, units: str, as_of: str = "") -> dict:
    return F.compute_exit_load(client_id, scheme_code, units, as_of)


@app.get("/clients/{client_id}/tax-estimate")
@_doc(F.estimate_capital_gains_tax)
def estimate_capital_gains_tax(client_id: str, scheme_code: str, units: str, as_of: str = "") -> dict:
    return F.estimate_capital_gains_tax(client_id, scheme_code, units, as_of)


@app.get("/clients/{client_id}/suitability")
@_doc(F.check_suitability)
def check_suitability(client_id: str, to_scheme: str) -> dict:
    return F.check_suitability(client_id, to_scheme)


@app.get("/clients/{client_id}/daily-limit")
@_doc(F.check_daily_limit)
def check_daily_limit(client_id: str, value_paise: int, as_of: str = "") -> dict:
    return F.check_daily_limit(client_id, value_paise, as_of)


@app.get("/schemes/{scheme_code}/cutoff")
@_doc(F.check_cutoff)
def check_cutoff(scheme_code: str, side: str = "redemption", request_time: str = "") -> dict:
    return F.check_cutoff(scheme_code, side, request_time)


@app.post("/confirmations")
@_doc(F.request_confirmation)
def request_confirmation(client_id: str, from_scheme: str, to_scheme: str, units: str) -> dict:
    return F.request_confirmation(client_id, from_scheme, to_scheme, units)


@app.post("/confirmations/{confirmation_id}/verify")
@_doc(F.verify_confirmation)
def verify_confirmation(confirmation_id: str, code: str, client_id: str, from_scheme: str, to_scheme: str, units: str) -> dict:
    return F.verify_confirmation(confirmation_id, code, client_id, from_scheme, to_scheme, units)


@app.post("/switches")
@_doc(F.execute_switch)
def execute_switch(client_id: str, from_scheme: str, to_scheme: str, units: str, as_of: str = "") -> dict:
    return F.execute_switch(client_id, from_scheme, to_scheme, units, as_of)
