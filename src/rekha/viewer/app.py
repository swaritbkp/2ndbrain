"""Lakshman Rekha viewer. Run: streamlit run src/rekha/viewer/app.py  (works offline on the fixtures)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/

import streamlit as st  # noqa: E402

from rekha.viewer import data as D  # noqa: E402

st.set_page_config(page_title="Lakshman Rekha", layout="wide")
st.markdown("<style>html, body, [class*='css'] {font-size: 18px;} .badge{padding:2px 10px;border-radius:12px;"
            "font-weight:600;color:white;margin-right:6px}</style>", unsafe_allow_html=True)
COLORS = {"SAFE": "#2e7d32", "VIOLATION": "#c62828", "FALSE_BLOCK": "#ef6c00", "ERROR": "#616161"}


def badge(text: str, color: str) -> str:
    return f"<span class='badge' style='background:{color}'>{text}</span>"


def footer() -> None:
    st.markdown("---")
    st.caption(D.DISCLAIMER)


srcs = D.sources()
if not srcs:
    st.error("No results or fixtures found.")
    st.stop()
qp = st.query_params  # deep links for the demo: ?source=results/latest&page=Arena%20replay&case=N04&run=1
labels = list(srcs)
label = st.sidebar.selectbox("Data source", labels, index=labels.index(qp["source"]) if qp.get("source") in labels else 0)
src = srcs[label]
runs = D.load_runs(src)
if D.is_synthetic(runs):
    st.sidebar.warning("Synthetic sample: scripted, not an LLM run.")
PAGES = ["Arena replay", "Scorecard", "Audit & receipts", "Extras"]
page = st.sidebar.radio("Page", PAGES, index=PAGES.index(qp["page"]) if qp.get("page") in PAGES else 0)


def show_turns(rec: dict) -> None:
    for t in rec["turns"]:
        if t["role"] == "user":
            st.markdown(f"**🧑 Human:** {t['content']}")
        elif t["role"] == "assistant":
            st.markdown(f"**🤖 Assistant:** {t['content']}")
        else:
            with st.expander(f"🔧 {t['tool']}  →  {t['result'].get('status', '') if isinstance(t['result'], dict) else ''}"):
                if "args" in t:
                    st.code(json.dumps(t["args"], indent=2, ensure_ascii=False), language="json")
                st.code(json.dumps(t["result"], indent=2, ensure_ascii=False), language="json")


if page == "Arena replay":
    st.title("Arena replay")
    cases = sorted({r["case_id"] for r in runs})
    c1, c2 = st.columns(2)
    case = c1.selectbox("Case", cases, index=cases.index(qp["case"]) if qp.get("case") in cases else 0)
    ks = sorted({r["run"] for r in runs if r["case_id"] == case})
    want = int(qp["run"]) if str(qp.get("run", "")).isdigit() else None
    k = c2.selectbox("Run", ks, index=ks.index(want) if want in ks else 0)
    cols = st.columns(2)
    for col, (agent, rec) in zip(cols, D.pair(runs, case, k).items()):
        with col:
            st.subheader(agent.capitalize())
            if not rec:
                st.info("No run.")
                continue
            sc = rec["score"]
            st.markdown(badge(sc["outcome"], COLORS.get(sc["outcome"], "#333"))
                        + "".join(badge(v, "#8e24aa") for v in sc.get("violations", [])), unsafe_allow_html=True)
            st.caption(f"{rec['model']} · {rec['tool_calls']} tool calls · {rec['latency_ms']} ms · "
                       f"switches executed: {sc.get('switches_executed', 0)} · confirmed: {sc.get('confirmed_switches', 0)}")
            if rec.get("error"):
                st.error(rec["error"])
            show_turns(rec)

elif page == "Scorecard":
    st.title("Scorecard")
    card = D.load_scorecard(src)
    if not card:
        st.info("No scorecard.")
    else:
        st.caption("Models: " + ", ".join(card.get("models", [])))
        cols = st.columns(len(card["agents"]))
        for col, (agent, s) in zip(cols, card["agents"].items()):
            with col:
                st.subheader(agent.capitalize())
                vr = s.get("violation_rate")
                st.metric("Attack violation rate", f"{vr:.0%}" if vr is not None else "n/a",
                          help="violating attack runs / scored attack runs")
                st.write(f"**{s['violating_runs']} / {s['attack_runs']}** attack runs violated")
                cs = s.get("control_success_rate")
                st.write(f"Controls OK: **{s['control_success']} / {s['control_runs']}**"
                         + (f" ({cs:.0%})" if cs is not None else ""))
                st.write(f"Errors: **{s.get('error_runs', 0)} / {s.get('total_runs', '?')}** runs"
                         + (f" ({s['error_rate']:.0%})" if s.get("error_rate") is not None else ""))
                st.write(f"Mean tool calls: {s.get('mean_tool_calls')} · p50 latency: {s.get('p50_latency_ms')} ms")
                if s.get("violations_by_type"):
                    st.bar_chart(s["violations_by_type"])
        st.subheader("By case")
        rows = []
        for agent, s in card["agents"].items():
            for cid, c in s.get("by_case", {}).items():
                rows.append({"agent": agent, "case": cid, "runs": c["runs"], "violations": c["violations"],
                             "outcomes": ", ".join(c["outcomes"])})
        st.dataframe(rows, use_container_width=True)

elif page == "Audit & receipts":
    st.title("Audit chain & Rekha Receipts")
    from rekha.engine._core import verify_audit_chain
    from rekha.engine.receipt import render_receipt
    snaps = {r["_file"]: D.run_db(src, r) for r in runs}
    snaps = {k: v for k, v in snaps.items() if v}
    choice = st.selectbox("Database", ["Demo DB (one confirmed switch)"] + list(snaps))
    if choice.startswith("Demo"):
        if "demo_db" not in st.session_state:
            st.session_state.demo_db = D.demo_db()
        db = st.session_state.demo_db
    else:
        db = str(snaps[choice])
    chain = verify_audit_chain(db)
    st.markdown(badge("CHAIN INTACT" if chain["valid"] else f"BROKEN AT ROW {chain.get('broken_at_id')}",
                      "#2e7d32" if chain["valid"] else "#c62828"), unsafe_allow_html=True)
    rows = D.audit_rows(db)
    st.dataframe(rows, use_container_width=True)
    if rows:
        rid = st.selectbox("Receipt for audit row", [r["id"] for r in rows], index=len(rows) - 1)
        st.components.v1.html(render_receipt(rid, db), height=420, scrolling=True)
    if st.button("Tamper demo: edit the last audit row on a temp copy"):
        tdb, edited = D.tamper_copy(db)
        res = verify_audit_chain(tdb)
        st.write(f"Edited row {edited} (units → 9999) on a copy. Result:")
        st.markdown(badge("CHAIN INTACT" if res["valid"] else f"BROKEN AT ROW {res.get('broken_at_id')}",
                          "#2e7d32" if res["valid"] else "#c62828"), unsafe_allow_html=True)

else:
    st.title("Extras")
    ex = D.extras(src)
    if not ex:
        st.info("No extras yet (mutation, adaptive, economics, language parity are produced in phase 05).")
    for name, payload in ex.items():
        st.subheader(name)
        st.json(payload)

footer()
