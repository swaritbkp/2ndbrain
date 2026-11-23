---
description: Phase 05: mutation testing, adaptive attacker, economics, language parity (each one non-blocking)
---
# 05 Distinctive layer (docs/FEATURES.md F6, F8–F10). Each failure → a DEGRADED item, never a stop.
1. **Economics** `src/rekha/arena/economics.py` → `results/latest/economics.json`.
2. **Language parity** (EN vs -HI) → `results/latest/language.json`.
3. **Mutation testing** `scripts/mutation_test.py`: for each of the 7 mutants, (a) run pytest with `REKHA_MUTANT` and record which tests fail (the unit tests must kill every mutant), (b) run the targeted cases once against the composed agent, with the mutant set ONLY in the composed server env → `results/latest/mutation.json` + the mutation score.
4. **Adaptive attacker** `src/rekha/arena/adaptive.py` (attacker = `models.get("attacker")`): 3 generations against both agents on the 6 hardest cases; the attacker sees the goal + the last transcript + what stopped it, and writes the next human turns (it never gets the real code) → `results/latest/adaptive.json` with lineage.
5. Re-run the reviewer in FAIRNESS mode on the new files.
Acceptance: economics + language exist; the others exist or are listed as DEGRADED with a reason.

## Finish
1. Invoke the **reviewer** subagent: "Review phase 05-distinctive against .claude/commands/05-distinctive.md". Fix only BLOCKERS. Max 2 review rounds; then decide the status yourself.
2. Run `python scripts/verify_phase.py 05-distinctive` yourself. It must exit 0 for PASS or DEGRADED.
3. `git add -A && git commit -m "05-distinctive: <summary>"`. Append one line to PROGRESS.md and a short section to docs/BUILD_LOG.md.
4. Write `state/05-distinctive.json` (docs/STATE_SCHEMA.md). End your turn.
