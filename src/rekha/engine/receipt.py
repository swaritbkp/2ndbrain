"""Rekha Receipt (F3): a printable HTML record of one audited event, with its chain hashes."""
from __future__ import annotations

import html
import json

from ._core import DISCLAIMER, verify_audit_chain
from .db import connect


def render_receipt(audit_id: int, db_path: str | None = None) -> str:
    conn = connect(db_path)
    try:
        r = conn.execute("SELECT * FROM audit_log WHERE id=?", (audit_id,)).fetchone()
        if not r:
            return f"<p>No audit row {audit_id}</p>"
        detail = json.loads(r["detail_json"])
    finally:
        conn.close()
    chain = verify_audit_chain(db_path)
    rows = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>" for k, v in detail.items())
    ok = "✓ chain intact" if chain.get("valid") else f"✗ chain broken at row {chain.get('broken_at_id')}"
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Rekha Receipt #{r['id']}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;color:#1b1b1b}}
table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #ddd;padding:.4rem;text-align:left}}
th{{width:35%;color:#555}}code{{font-size:.8rem;word-break:break-all}}.foot{{color:#777;font-size:.85rem}}</style></head>
<body><h1>Rekha Receipt #{r['id']}</h1>
<p><b>{html.escape(r['action'])}</b> · {html.escape(r['code'])} · client {html.escape(str(r['client_id']))} · {html.escape(r['ts'])}</p>
<table>{rows}</table>
<p>Previous hash: <code>{r['prev_hash']}</code><br>Row hash: <code>{r['row_hash']}</code><br>{ok}</p>
<p class="foot">{DISCLAIMER}</p></body></html>"""
