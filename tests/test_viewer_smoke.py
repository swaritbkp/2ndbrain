"""Viewer smoke: helpers load fixtures + smoke results; the audit/tamper helpers work; streamlit serves."""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from rekha.engine._core import verify_audit_chain
from rekha.viewer import data as D

ROOT = Path(__file__).resolve().parents[1]


def test_fixture_and_smoke_sources_load():
    srcs = D.sources()
    fx = [v for k, v in srcs.items() if "synthetic" in k]
    assert fx, srcs
    runs = D.load_runs(fx[0])
    assert runs and D.is_synthetic(runs)
    assert {"baseline", "composed"} <= set(D.load_scorecard(fx[0])["agents"])
    for d in srcs.values():
        for r in D.load_runs(d):
            assert "score" in r and "turns" in r
        cases = {r["case_id"] for r in D.load_runs(d)}
        c = sorted(cases)[0]
        assert any(D.pair(D.load_runs(d), c, 1).values())


def test_demo_db_chain_and_tamper(monkeypatch, tmp_path):
    monkeypatch.setenv("REKHA_TOKEN_SECRET", "test-secret")
    db = D.demo_db()
    assert verify_audit_chain(db)["valid"]
    assert any(r["action"] == "SWITCH_EXECUTED" for r in D.audit_rows(db))
    tdb, edited = D.tamper_copy(db)
    res = verify_audit_chain(tdb)
    assert edited and not res["valid"] and res["broken_at_id"] == edited
    assert verify_audit_chain(db)["valid"]  # original untouched


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.mark.skipif(shutil.which("streamlit") is None and not (Path(sys.executable).parent / "streamlit.exe").exists()
                    and not (Path(sys.executable).parent / "streamlit").exists(), reason="streamlit CLI missing")
def test_streamlit_serves():
    port = _free_port()
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), env.get("PYTHONPATH", "")])
    p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "src/rekha/viewer/app.py"),
                          "--server.headless", "true", "--server.port", str(port), "--browser.gatherUsageStats", "false"],
                         cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ok = False
        for _ in range(40):
            time.sleep(0.5)
            try:
                if httpx.get(f"http://127.0.0.1:{port}/_stcore/health", timeout=2).status_code == 200:
                    ok = True
                    break
            except httpx.HTTPError:
                pass
        assert ok, "streamlit did not serve within 20 s"
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()


@pytest.mark.parametrize("page", ["Arena replay", "Scorecard", "Audit & receipts", "Extras"])
def test_every_page_renders_without_exceptions(page, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("REKHA_TOKEN_SECRET", "test-secret")
    for src_label in D.sources():
        at = AppTest.from_file(str(ROOT / "src/rekha/viewer/app.py"), default_timeout=60).run()
        at.sidebar.selectbox[0].set_value(src_label).run()
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, (page, src_label, [e.value for e in at.exception])
        assert any(D.DISCLAIMER in c.value for c in at.caption)
