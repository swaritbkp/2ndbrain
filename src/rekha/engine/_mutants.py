"""Guardrail mutation hook for mutation testing (F5). REKHA_MUTANT unset = no effect.

Each mutant disables exactly ONE guardrail. Only scripts/mutation_test.py and tests set it.
"""
from __future__ import annotations

import os

MUTANTS = (
    "no_kyc",              # verify_kyc always valid
    "no_lockin",           # check_lockin always allowed
    "no_suitability",      # check_suitability always suitable
    "no_daily_cap",        # check_daily_limit always within
    "no_code_check",       # verify_confirmation accepts any code
    "no_param_binding",    # verify_confirmation ignores param mismatch
    "no_single_use",       # verify_confirmation accepts an already-used confirmation
)


def active(name: str) -> bool:
    return os.environ.get("REKHA_MUTANT", "") == name
