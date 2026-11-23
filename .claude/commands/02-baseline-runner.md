---
description: Phase 02: baseline server, arena runner, simulated human, attack variants, smoke run
---
# 02 Baseline + runner
1. **Baseline:** `python scripts/synapse_build.py --label baseline --cwd src/rekha/baseline -- --auto --all-endpoints`. Check that the generated server lists exactly the 12 tools and can reach the API (uvicorn `rekha.baseline.api:app` on port 8765, started and stopped by the runner). Otherwise use the fallback `rekha.baseline.sdk_server` (FALLBACKS). Write the server spec to `state/baseline_server.txt`.
2. **Runner** per docs/SPEC.md "Arena runner": `src/rekha/arena/runner.py`, `human.py`, `__main__.py` (CLI), plus `tests/test_runner_offline.py` (a fake LLM client that scripts tool calls, so the loop, the human, resume and scoring are tested without network).
3. **Attacks:** invoke the **red-team-author** subagent → `src/rekha/arena/attacks_extra.yaml` (the `-HI` variants of A01–A12 + up to 6 new attacks).
4. **Smoke run:** `python -m rekha.arena run --suite core --cases A02,K01 --agents baseline,composed --runs 1 --out results/smoke`, then aggregate → `results/smoke/scorecard.json`. Inspect one transcript per agent and confirm the flow is sane (the composed agent asks for the code; the human supplies it on K01).
Acceptance: the offline runner tests pass; the smoke scorecard has both agents; verify_phase 02 passes.

## Finish
1. Invoke the **reviewer** subagent: "Review phase 02-baseline-runner against .claude/commands/02-baseline-runner.md". Fix only BLOCKERS. Max 2 review rounds; then decide the status yourself.
2. Run `python scripts/verify_phase.py 02-baseline-runner` yourself. It must exit 0 for PASS or DEGRADED.
3. `git add -A && git commit -m "02-baseline-runner: <summary>"`. Append one line to PROGRESS.md and a short section to docs/BUILD_LOG.md.
4. Write `state/02-baseline-runner.json` (docs/STATE_SCHEMA.md). End your turn.
