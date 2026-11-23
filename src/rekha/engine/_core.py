"""Private helpers. Not part of the public tool surface (Synapse should compose functions.py only)."""
from __future__ import annotations

import calendar
import hashlib
import hmac
import json
import os
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

from . import config
from .db import connect

UNIT_Q = Decimal("0.001")
GENESIS = "0" * 64
DISCLAIMER = "Fictional data. Indicative estimate only. Not tax or investment advice."


# ---------- errors ----------
def err(code: str, message: str, **extra) -> dict:
    return {"ok": False, "code": code, "message": message, **extra}


# ---------- clock ----------
def tz() -> timezone:
    off = config.rules().get("timezone_offset", "+05:30")
    sign = 1 if off[0] == "+" else -1
    h, m = int(off[1:3]), int(off[4:6])
    return timezone(sign * timedelta(hours=h, minutes=m))


def now() -> datetime:
    """Current time (IST). REKHA_NOW (ISO datetime) freezes it for tests and arena runs."""
    fixed = os.environ.get("REKHA_NOW", "").strip()
    if fixed:
        dt = datetime.fromisoformat(fixed)
        return dt if dt.tzinfo else dt.replace(tzinfo=tz())
    return datetime.now(tz())


def resolve_as_of(as_of: str) -> date:
    s = (as_of or os.environ.get("REKHA_AS_OF", "")).strip()
    return date.fromisoformat(s[:10]) if s else now().date()


def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def next_business_day(d: date) -> date:
    days = set(config.rules().get("business_days", [0, 1, 2, 3, 4]))
    d = d + timedelta(days=1)
    while d.weekday() not in days:
        d += timedelta(days=1)
    return d


def is_business_day(d: date) -> bool:
    return d.weekday() in set(config.rules().get("business_days", [0, 1, 2, 3, 4]))


def parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


# ---------- numbers ----------
def parse_units(units: str) -> Decimal | None:
    try:
        u = Decimal(str(units).strip()).quantize(UNIT_Q, rounding=ROUND_DOWN)
    except (InvalidOperation, ValueError):
        return None
    return u if u > 0 else None


def paise(x: Decimal) -> int:
    return int(x.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def rupees(p: int) -> str:
    """Indian grouping, e.g. 50000000 paise -> '₹5,00,000.00'."""
    neg, p = p < 0, abs(p)
    r, ps = divmod(p, 100)
    s = str(r)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return f"{'-' if neg else ''}₹{s}.{ps:02d}"


# ---------- reference data ----------
def scheme(code: str) -> dict | None:
    return config.schemes().get(code)


def client_row(conn, client_id: str):
    return conn.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,)).fetchone()


def fifo_take(conn, client_id: str, scheme_code: str, units: Decimal) -> tuple[list[tuple[dict, Decimal]], Decimal]:
    """Return ([(lot, units_taken)], total_held) in FIFO order. Doesn't modify anything."""
    rows = conn.execute(
        "SELECT * FROM lots WHERE client_id=? AND scheme_code=? ORDER BY allotment_date, lot_id",
        (client_id, scheme_code),
    ).fetchall()
    held = sum((Decimal(r["units"]) for r in rows), Decimal("0"))
    out, left = [], units
    for r in rows:
        if left <= 0:
            break
        u = Decimal(r["units"])
        take = min(u, left)
        out.append((dict(r), take))
        left -= take
    return out, held


# ---------- hashing / secrets ----------
def secret() -> bytes:
    return os.environ.get("REKHA_TOKEN_SECRET", "dev-only-secret-change-me").encode()


def params_hash(client_id: str, from_scheme: str, to_scheme: str, units: Decimal) -> str:
    msg = f"{client_id}|{from_scheme}|{to_scheme}|{units}"
    return hmac.new(secret(), msg.encode(), hashlib.sha256).hexdigest()


def code_hash(confirmation_id: str, code: str) -> str:
    return hmac.new(secret(), f"{confirmation_id}|{code}".encode(), hashlib.sha256).hexdigest()


# ---------- audit chain (F3) ----------
def _canon(ts: str, client_id: str | None, action: str, code: str, detail_json: str) -> str:
    return json.dumps([ts, client_id, action, code, detail_json], separators=(",", ":"), ensure_ascii=False)


def audit(conn, client_id: str | None, action: str, code: str, detail: dict) -> int:
    """Append a hash-chained audit row. Caller controls the transaction."""
    last = conn.execute("SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    prev = last["row_hash"] if last else GENESIS
    ts = now().isoformat()
    dj = json.dumps(detail, sort_keys=True, ensure_ascii=False, default=str)
    rh = hashlib.sha256((prev + _canon(ts, client_id, action, code, dj)).encode()).hexdigest()
    cur = conn.execute(
        "INSERT INTO audit_log(ts, client_id, action, code, detail_json, prev_hash, row_hash) VALUES (?,?,?,?,?,?,?)",
        (ts, client_id, action, code, dj, prev, rh),
    )
    return int(cur.lastrowid)


def verify_audit_chain(db_path: str | None = None) -> dict:
    """Recompute every hash. Any edited, deleted or reordered row breaks the chain."""
    conn = connect(db_path)
    try:
        prev, n = GENESIS, 0
        for r in conn.execute("SELECT * FROM audit_log ORDER BY id"):
            expect = hashlib.sha256((prev + _canon(r["ts"], r["client_id"], r["action"], r["code"], r["detail_json"])).encode()).hexdigest()
            if r["prev_hash"] != prev or r["row_hash"] != expect:
                return {"ok": True, "valid": False, "broken_at_id": r["id"], "rows_checked": n}
            prev, n = r["row_hash"], n + 1
        return {"ok": True, "valid": True, "rows_checked": n, "head": prev}
    finally:
        conn.close()
