"""pytest plugin used ONLY by scripts/mutation_test.py (-p mutation_plugin).

tests/conftest.py clears REKHA_MUTANT in the db fixture (hermetic tests). For mutation runs we re-apply the mutant
AFTER fixture setup, right before each test body, so the whole suite runs against the weakened engine. Tests are
not modified; tests that set their own mutant via monkeypatch still win (they set it inside the body).
"""

from __future__ import annotations

import os

import pytest

_MUTANT = os.environ.get("MUTATION_UNDER_TEST", "")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    old = os.environ.get("REKHA_MUTANT")
    if _MUTANT:
        os.environ["REKHA_MUTANT"] = _MUTANT
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("REKHA_MUTANT", None)
        else:
            os.environ["REKHA_MUTANT"] = old
