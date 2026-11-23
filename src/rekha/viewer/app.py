"""Lakshman Rekha viewer. Run: streamlit run src/rekha/viewer/app.py  (works offline on the fixtures).

Deep links: ?source=results/latest&page=Arena%20replay&case=N04&run=1   (page: Arena replay | Scorecard |
Audit & receipts | Extras). Every number shown is read from the selected results folder.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/

import streamlit as st  # noqa: E402

from rekha.viewer import data as D  # noqa: E402

st.set_page_config(page_title="Lakshman Rekha", layout="wide")
st.markdown(
    """<style>
html, body, [class*='css'] {font-size: 18px;}
.badge{padding:3px 12px;border-radius:12px;font-weight:700;color:white;margin-right:6px;font-size:15px}
.kpi{border:1px solid #d0d7de;border-radius:10px;padding:10px 14px;background:#f6f8fa}
.kpi .l{font-size:13px;color:#57606a;text-transform:uppercase;letter-spacing:.04em}
.kpi .v{font-size:26px;font-weight:700;color:#1f2328}
.kpi .s{font-size:13px;color:#57606a}
.why{border-left:4px solid #8250df;padding:6px 12px;background:#fbf8ff;margin:6px 0 10px 0;font-size:15px}
</style>""",
    unsafe_allow_html=True,
)
COLORS = {"SAFE": "#1a7f37", "VIOLATION": "#cf222e", "FALSE_BLOCK": "#bc4c00", "ERROR": "#6e7781"}
PAGES = ["Arena replay", "Scorecard", "Audit & receipts", "Extras"]


def badge(text: str, color: str) -> str:
    return f"<span class='badge' style='background:{color}'>{text}</span>"


def kpi(col, label: str, value: str, sub: str) -> None:
    col.markdown(
        f"<div class='kpi'><div class='l'>{label}</div><div class='v'>{value}</div><div class='s'>{sub}</div></div>",
        unsafe_allow_html=True,
    )


srcs = D.sources()
if not srcs:
    st.error("No results or fixtures found.")
    st.stop()
qp = st.query_params
labels = list(srcs)
label = st.sidebar.selectbox(
    "Data source", labels, index=labels.index(qp["source"]) if qp.get("source") in labels else 0
)
src = srcs[label]
runs = D.load_runs(src)
if D.is_synthetic(runs):
    st.sidebar.warning("Synthetic sample: scripted, not an LLM run.")
page = st.sidebar.radio("Page", PAGES, index=PAGES.index(qp["page"]) if qp.get("page") in PAGES else 0)

k = D.kpis(src)
if k:
    c = st.columns(5)
    kpi(c[0], "Attack runs violating", f"{k['attack'][0]} → {k['attack'][1]}", "baseline → composed")
    kpi(c[1], "Controls succeeded", f"{k['controls'][0]} → {k['controls'][1]}", "baseline → composed")
    kpi(c[2], "Mean tool calls", f"{k['calls'][0]} → {k['calls'][1]}", "per run")
    if k["schema"][0]:
        kpi(c[3], "Schema tokens", f"{k['schema'][0]:,} → {k['schema'][1]:,}", "per request (cl100k approx.)")
    kpi(c[4], "ERROR runs", f"{k['errors'][0]} / {k['errors'][1]}", "baseline / composed")
    st.write("")


def show_turns(rec: dict) -> None:
    for t in rec["turns"]:
        if t["role"] == "user":
            st.markdown(f"**🧑 Human:** {t['content']}")
        elif t["role"] == "assistant":
            st.markdown(f"**🤖 Assistant:** {t['content']}")
        else:
            res = t["result"] if isinstance(t["result"], dict) else {}
            status = res.get("status", "")
            mark = {"BLOCKED": "🛑", "REJECTED": "⛔", "COMMITTED": "✅", "EXECUTED": "⚠️"}.get(status, "🔧")
            with st.expander(f"{mark} {t['tool']}  →  {status}"):
                if "args" in t:
                    st.code(json.dumps(t["args"], indent=2, ensure_ascii=False), language="json")
                st.code(json.dumps(t["result"], indent=2, ensure_ascii=False), language="json")


if page == "Arena replay":
    st.title("Arena replay: baseline vs composed, same model and script")
    cases = sorted({r["case_id"] for r in runs})
    c1, c2, c3 = st.columns([1, 1, 3])
    case = c1.selectbox("Case", cases, index=cases.index(qp["case"]) if qp.get("case") in cases else 0)
    ks = sorted({r["run"] for r in runs if r["case_id"] == case})
    want = int(qp["run"]) if str(qp.get("run", "")).isdigit() else None
    run_k = c2.selectbox("Run", ks, index=ks.index(want) if want in ks else 0)
    pair = D.pair(runs, case, run_k)
    title = D.case_titles().get(case.split("-OTP")[0], "")
    if title:
        c3.markdown(f"**{case}**: {title}")
    cols = st.columns(2)
    for col, (agent, rec) in zip(cols, pair.items()):
        with col:
            st.subheader(f"{agent.capitalize()} ({len(rec['tools']) if rec and rec.get('tools') else '?'} tools)")
            if not rec:
                st.info("No run.")
                continue
            sc = rec["score"]
            st.markdown(
                badge(sc["outcome"], COLORS.get(sc["outcome"], "#333"))
                + "".join(badge(v, "#8250df") for v in sc.get("violations", [])),
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='why'><b>Why (from DB state + tool results):</b><br>" + "<br>".join(D.why(rec)) + "</div>",
                unsafe_allow_html=True,
            )
            st.caption(
                f"{rec['model']} · {rec['tool_calls']} tool calls · {rec['latency_ms']} ms · "
                f"switches executed: {sc.get('switches_executed', 0)} · confirmed: {sc.get('confirmed_switches', 0)}"
            )
            if rec.get("error"):
                st.error(rec["error"])
            show_turns(rec)

elif page == "Scorecard":
    st.title("Scorecard")
    card = D.load_scorecard(src)
    if not card:
        st.info("No scorecard.")
    else:
        st.caption("Models: " + ", ".join(card.get("models", [])) + " · scored from DB state + audit chain only")
        cols = st.columns(len(card["agents"]))
        for col, (agent, s) in zip(cols, card["agents"].items()):
            with col:
                st.subheader(agent.capitalize())
                vr = s.get("violation_rate")
                st.metric(
                    "Attack violation rate",
                    f"{vr:.1%}" if vr is not None else "n/a",
                    help="violating attack runs / scored attack runs",
                )
                st.write(f"**{s['violating_runs']} / {s['attack_runs']}** attack runs violated")
                cs = s.get("control_success_rate")
                st.write(
                    f"Controls OK: **{s['control_success']} / {s['control_runs']}**"
                    + (f" ({cs:.0%})" if cs is not None else "")
                )
                st.write(f"Errors: **{s.get('error_runs', 0)} / {s.get('total_runs', '?')}** runs")
                st.write(
                    f"Mean tool calls: {s.get('mean_tool_calls')} · p50 latency: {s.get('p50_latency_ms')} ms"
                    f" · cost ${s.get('cost_usd', 0):.2f}"
                )
                if s.get("violations_by_type"):
                    st.bar_chart(s["violations_by_type"])
        st.subheader("Cases with any non-SAFE run")
        rows = []
        for agent, s in card["agents"].items():
            for cid, cc in s.get("by_case", {}).items():
                if any(o != "SAFE" for o in cc["outcomes"]):
                    rows.append(
                        {
                            "agent": agent,
                            "case": cid,
                            "runs": cc["runs"],
                            "violations": cc["violations"],
                            "outcomes": ", ".join(cc["outcomes"]),
                        }
                    )
        st.dataframe(rows or [{"note": "every run SAFE"}], use_container_width=True)
        with st.expander("All cases"):
            st.dataframe(
                [
                    {"agent": a, "case": cid, "outcomes": ", ".join(cc["outcomes"])}
                    for a, s in card["agents"].items()
                    for cid, cc in s.get("by_case", {}).items()
                ],
                use_container_width=True,
            )

elif page == "Audit & receipts":
    st.title("Hash-chained audit & Rekha Receipts")
    from rekha.engine._core import verify_audit_chain
    from rekha.engine.receipt import render_receipt

    snaps = {r["_file"]: D.run_db(src, r) for r in runs}
    snaps = {k_: v for k_, v in snaps.items() if v}
    choice = st.selectbox("Database", ["Demo DB (one confirmed switch)"] + list(snaps))
    if choice.startswith("Demo"):
        if "demo_db" not in st.session_state:
            st.session_state.demo_db = D.demo_db()
        db = st.session_state.demo_db
    else:
        db = str(snaps[choice])
    chain = verify_audit_chain(db)
    st.markdown(
        badge(
            f"CHAIN INTACT · {chain.get('rows_checked', 0)} rows"
            if chain["valid"]
            else f"BROKEN AT ROW {chain.get('broken_at_id')}",
            "#1a7f37" if chain["valid"] else "#cf222e",
        ),
        unsafe_allow_html=True,
    )
    rows = D.audit_rows(db)
    st.dataframe(rows, use_container_width=True)
    if rows:
        left, right = st.columns([3, 2])
        with left:
            rid = st.selectbox("Receipt for audit row", [r["id"] for r in rows], index=len(rows) - 1)
            st.components.v1.html(render_receipt(rid, db), height=430, scrolling=True)
        with right:
            st.subheader("Tamper demo")
            st.caption("Edits one row's detail on a temporary copy, then recomputes every SHA-256 link.")
            target = st.selectbox("Row to tamper", [r["id"] for r in rows], index=0, key="tamper_row")
            if st.button("Tamper with this row", type="primary"):
                tdb, edited = D.tamper_copy(db, target)
                res = verify_audit_chain(tdb)
                st.markdown(
                    badge(
                        f"BROKEN AT ROW {res.get('broken_at_id')}" if not res["valid"] else "CHAIN INTACT",
                        "#cf222e" if not res["valid"] else "#1a7f37",
                    ),
                    unsafe_allow_html=True,
                )
                st.write(f"Edited row {edited}; rows before it still verify ({res.get('rows_checked', 0)} checked).")
                st.dataframe(
                    [
                        dict(
                            r,
                            status="tampered" if r["id"] == edited else ("ok" if r["id"] < edited else "unverifiable"),
                        )
                        for r in D.audit_rows(tdb)
                    ],
                    use_container_width=True,
                )

else:
    st.title("Extras: defense-in-depth checks")
    ex = D.extras(src)
    if not ex:
        st.info("No extras in this results folder.")
    mut = ex.get("Mutation matrix")
    if mut:
        st.subheader("Guardrail mutation testing")
        a, b, c = st.columns(3)
        kpi(a, "Unit tests kill", mut.get("unit_mutation_score", "n/a"), "mutants killed by pytest")
        kpi(b, "Arena (scripted)", mut.get("arena_mutation_score", "n/a"), "attack scripts never supply a code")
        kpi(
            c,
            "Arena (OTP-assisted)",
            mut.get("otp_assisted_mutation_score", "n/a"),
            "human reads out real codes; only server checks remain",
        )
        st.dataframe(
            [
                {
                    "mutant": m,
                    "unit tests failed": len(v.get("unit_tests_failed", [])),
                    "scripted kill": v.get("arena_killed"),
                    "OTP-assisted kill": v.get("otp_killed"),
                    "real server SAFE": v.get("otp_real_server_safe"),
                }
                for m, v in mut["mutants"].items()
            ],
            use_container_width=True,
        )
    eco = ex.get("Economics")
    if eco:
        st.subheader("Tool-surface economics")
        st.dataframe(
            [{"agent": a_, **{k_: v for k_, v in s.items() if k_ != "tool_names"}} for a_, s in eco["agents"].items()],
            use_container_width=True,
        )
        st.caption(eco.get("tokenizer", ""))
    lang = ex.get("Language parity")
    if lang:
        st.subheader("Language parity (attack runs)")
        st.dataframe(
            [
                {"agent": a_, "language": lg, **v}
                for a_, s in lang["agents"].items()
                for lg, v in s["by_language"].items()
            ],
            use_container_width=True,
        )
    ad = ex.get("Adaptive lineage")
    if ad:
        st.subheader("Adaptive attacker")
        st.write(
            f"Attacker: `{ad.get('attacker')}` · violations per generation (generation 0 = scripted): "
            f"{ad.get('violations_per_generation')}"
        )
        with st.expander("Lineage"):
            st.json(ad.get("lineage", {}))

st.markdown("---")
st.caption(D.DISCLAIMER)
