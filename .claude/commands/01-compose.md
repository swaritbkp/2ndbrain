---
description: Phase 01: Synapse-compose rebalance_switch; must pass the contract tests
---
# 01 Compose with Synapse (the Track 2 core)
1. Read docs/RULES.md §3 and docs/ENVIRONMENT.md (Synapse help output). Decide how the model is chosen (flag, `model set --global`, or default) and log it in DECISIONS.
2. **Route A** from the repo root:
   `python scripts/synapse_build.py --label composed --cwd . -- --custom -q "<Q>"`
   with Q = "Compose the functions in src/rekha/engine/functions.py into ONE MCP tool named rebalance_switch(client_id: str, from_scheme: str, to_scheme: str, units: str, confirmation_id: str = , confirmation_code: str = ). Behaviour must match src/rekha/engine/workflow.py exactly: always call get_client_profile, verify_kyc, check_lockin, check_suitability, compute_exit_load, check_daily_limit; any failed check returns status BLOCKED with reasons and a helpful_alternative and issues no confirmation. If no confirmation_code: call estimate_capital_gains_tax and check_cutoff, then request_confirmation, and return status PREVIEW with impact, warnings and confirmation_id. If confirmation_code is given: re-run all checks, call verify_confirmation with the exact params, and only if verified call execute_switch and return COMMITTED; otherwise REJECTED with the reason. Never expose execute_switch, verify_confirmation or request_confirmation as tools. Never return a confirmation code."
3. Find the generated server(s) (the wrapper prints `generated_or_changed`). Write their path(s), comma-separated, to `state/composed_server.txt`. Then run:
   `COMPOSED_SERVER=<path> python -m pytest -q tests/contract`
4. Failing → vary the -q (up to 3 total attempts for Route A) → Route B → Route C (docs/FALLBACKS.md). Never edit generated files.
5. Record in docs/BUILD_LOG.md: the route, the commands, the tool list + inputSchema (`python tests/mcp_client.py <server>`), imports vs copies, and contract results.
6. `docs/MCP_CONFIG.md`: a Claude Desktop config snippet for the composed server (F11).
Acceptance: the contract tests pass against a Synapse-generated server; verify_phase 01 passes.

## Finish
1. Invoke the **reviewer** subagent: "Review phase 01-compose against .claude/commands/01-compose.md". Fix only BLOCKERS. Max 2 review rounds; then decide the status yourself.
2. Run `python scripts/verify_phase.py 01-compose` yourself. It must exit 0 for PASS or DEGRADED.
3. `git add -A && git commit -m "01-compose: <summary>"`. Append one line to PROGRESS.md and a short section to docs/BUILD_LOG.md.
4. Write `state/01-compose.json` (docs/STATE_SCHEMA.md). End your turn.
