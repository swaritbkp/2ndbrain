---
description: Phase 04: full arena run (resumable, budgeted), model sweep, fairness audit
---
# 04 Arena
1. Full run: `python -m rekha.arena run --suite all --agents baseline,composed --runs ${ARENA_RUNS:-3} --out results/<ts>_<model-slug>`, then point `results/latest` at it (copy if symlinks fail on Windows). Resumable: if interrupted, rerun the same command.
2. Model sweep (F7): for each model in `models.get("sweep")`, run `--suite core --runs 2` into its own folder.
3. Aggregate every folder (`python -m rekha.arena.aggregate <dir>`).
4. Invoke the **reviewer** subagent in FAIRNESS mode on results/latest. It writes `results/latest/fairness_audit.json`. Fix high-severity issues and rerun the affected cases.
5. Write `results/latest/SUMMARY.md`: headline numbers with denominators, honest caveats (model, temperature, runs, ERROR count, budget truncation).
Acceptance: ≥ 12 scored attack runs per agent in latest; fairness audit present with no open high issues; verify_phase 04 passes.

## Finish
1. Invoke the **reviewer** subagent: "Review phase 04-arena against .claude/commands/04-arena.md". Fix only BLOCKERS. Max 2 review rounds; then decide the status yourself.
2. Run `python scripts/verify_phase.py 04-arena` yourself. It must exit 0 for PASS or DEGRADED.
3. `git add -A && git commit -m "04-arena: <summary>"`. Append one line to PROGRESS.md and a short section to docs/BUILD_LOG.md.
4. Write `state/04-arena.json` (docs/STATE_SCHEMA.md). End your turn.
