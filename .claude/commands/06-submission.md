---
description: Phase 06: submission write-up, deck, demo, clean-room check, final report
---
# 06 Submission + final audit
1. `README.md`: rewrite as the submission write-up. Cover:
   - the problem, and why Synapse Custom fits
   - architecture (mermaid) and the safety contract
   - results with denominators, from the results JSON only
   - fairness method and distinctive features
   - how to run (5 commands), limitations, config verification status, disclaimer
   - the composition route used (A/B/C), stated honestly
2. `scripts/build_deck.py` → `deliverables/Lakshman_Rekha_deck.pptx` (python-pptx). Follow docs/DECK_OUTLINE.md. Charts from the results, ≤ 30 words per slide, speaker notes on each slide. If LibreOffice is present, render the slides to PNG and check for overflow.
3. `docs/DEMO_FINAL.md` (≤ 3:00, real case ids and numbers) + `scripts/demo.ps1` / `demo.sh` (replay mode, Enter-to-advance, opens the viewer on the right case).
4. **Clean room:** copy the repo without `.venv`, `results` or `data/*.db` to a temp dir, then make a fresh venv, install, `pytest -q`, contract tests, and replay the demo. Record the result.
5. Invoke the **reviewer** in FAIRNESS mode: every number in README and deck must match the results files.
6. `FINAL_REPORT.md`: phase statuses, what shipped (F1–F11), DEGRADED items, autonomous decisions (link), unverified config values, exact human next steps (record video, final read, submit), and the tokens/cost used.
Acceptance: README, deck, demo, FINAL_REPORT exist; numbers audited; verify_phase 06 passes.

## Finish
1. Invoke the **reviewer** subagent: "Review phase 06-submission against .claude/commands/06-submission.md". Fix only BLOCKERS. Max 2 review rounds; then decide the status yourself.
2. Run `python scripts/verify_phase.py 06-submission` yourself. It must exit 0 for PASS or DEGRADED.
3. `git add -A && git commit -m "06-submission: <summary>"`. Append one line to PROGRESS.md and a short section to docs/BUILD_LOG.md.
4. Write `state/06-submission.json` (docs/STATE_SCHEMA.md). End your turn.
