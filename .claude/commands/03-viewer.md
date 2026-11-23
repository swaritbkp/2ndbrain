---
description: Phase 03: Streamlit viewer (replay-first, works offline). Built early so the demo floor exists
---
# 03 Viewer (`src/rekha/viewer/app.py`)
Data source: a dropdown over `results/*/` + `fixtures/sample_results/` (labelled "synthetic sample" when `synthetic: true`).
Pages (keep it simple and clear; large type for screen recording):
1. **Arena replay**: pick a case and run; Baseline | Composed side by side; step through turns (human, assistant, tool call/result collapsible); the final DB effect + violation badges.
2. **Scorecard**: violation rate with denominators, violations by type, control success, errors; the model selector if a sweep exists.
3. **Audit & receipts**: run `verify_audit_chain` on a chosen run DB snapshot (if saved) or the demo DB; a tamper demo on a temp copy; render a Rekha Receipt (`engine/receipt.py`).
4. **Extras** (render only if the files exist): mutation matrix, adaptive lineage, economics, language parity.
Footer disclaimer on every page. `tests/test_viewer_smoke.py`: import the app helpers, load the fixtures and the smoke results without error. Start `streamlit run` headless for ~10 s and confirm it serves.
Acceptance: works offline on the fixtures; verify_phase 03 passes.

## Finish
1. Invoke the **reviewer** subagent: "Review phase 03-viewer against .claude/commands/03-viewer.md". Fix only BLOCKERS. Max 2 review rounds; then decide the status yourself.
2. Run `python scripts/verify_phase.py 03-viewer` yourself. It must exit 0 for PASS or DEGRADED.
3. `git add -A && git commit -m "03-viewer: <summary>"`. Append one line to PROGRESS.md and a short section to docs/BUILD_LOG.md.
4. Write `state/03-viewer.json` (docs/STATE_SCHEMA.md). End your turn.
