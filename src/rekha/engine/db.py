"""SQLite schema + connection. REKHA_DB selects the database file (the arena uses a fresh copy per run)."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
  client_id TEXT PRIMARY KEY, name TEXT NOT NULL, city TEXT, rm_name TEXT,
  risk_profile TEXT NOT NULL, kyc_status TEXT NOT NULL, kyc_valid_till TEXT NOT NULL,
  target_equity_pct REAL, target_debt_pct REAL, target_gold_pct REAL,
  fy_ltcg_realised_paise INTEGER NOT NULL DEFAULT 0, notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS lots (
  lot_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT NOT NULL, scheme_code TEXT NOT NULL,
  allotment_date TEXT NOT NULL, units TEXT NOT NULL, cost_nav_paise INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS switches (
  switch_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, from_scheme TEXT NOT NULL, to_scheme TEXT NOT NULL,
  units TEXT NOT NULL, out_value_paise INTEGER NOT NULL, exit_load_paise INTEGER NOT NULL,
  stamp_duty_paise INTEGER NOT NULL, in_units TEXT NOT NULL, executed_at TEXT NOT NULL, as_of TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS confirmations (
  confirmation_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, from_scheme TEXT NOT NULL, to_scheme TEXT NOT NULL,
  units TEXT NOT NULL, params_hash TEXT NOT NULL, code_hash TEXT NOT NULL, created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL, verified_at TEXT
);
-- Out-of-band channel (the "RM console"). NO tool ever reads this table; only the human (or the arena's simulated human) does.
CREATE TABLE IF NOT EXISTS oob_outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT, confirmation_id TEXT NOT NULL, code TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, client_id TEXT, action TEXT NOT NULL, code TEXT NOT NULL,
  detail_json TEXT NOT NULL, prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL
);
"""


def db_path() -> str:
    return os.environ.get("REKHA_DB", str(_ROOT / "data" / "rekha.db"))


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or db_path(), timeout=10, isolation_level=None)  # autocommit; explicit BEGIN for writes
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
