from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "data"))

DEMO_NOW = "2026-11-23T14:55:00+05:30"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Fresh seeded DB per test with a frozen clock (2026-11-23 14:55 IST)."""
    import seed
    path = str(tmp_path / "rekha.db")
    seed.seed(path)
    monkeypatch.setenv("REKHA_DB", path)
    monkeypatch.setenv("REKHA_AS_OF", "2026-11-23")
    monkeypatch.setenv("REKHA_NOW", DEMO_NOW)
    monkeypatch.setenv("REKHA_TOKEN_SECRET", "test-secret")
    monkeypatch.delenv("REKHA_MUTANT", raising=False)
    return path


def oob_code(db_path: str, confirmation_id: str) -> str:
    """What the HUMAN sees on the RM console. Test/harness only. No tool exposes this."""
    from rekha.engine.db import connect
    conn = connect(db_path)
    try:
        return conn.execute("SELECT code FROM oob_outbox WHERE confirmation_id=?", (confirmation_id,)).fetchone()["code"]
    finally:
        conn.close()
