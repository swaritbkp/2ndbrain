# Fallbacks (follow them, don't ask). The same error twice → next fallback.

## Hard stops (the ONLY reasons to stop)
1. `OPENROUTER_API_KEY` missing, or no tool-capable model can be resolved/pinged (scripts/openrouter_models.py + ping_model.py, 3 tries).
2. Python < 3.11 or Node < 20, and they can't be installed without admin rights.
3. Phase 01: none of Routes A–C yields a Synapse-generated server that passes `tests/contract/`.
On a hard stop, write STOPPED.md with the exact human fix (e.g. "add $5 OpenRouter credit", "set SYNAPSE_MODEL_FALLBACKS=<a stronger model>").

## Synapse composition (phase 01). Acceptance = `COMPOSED_SERVER=<file> pytest tests/contract` green
- **Route A:** one `--custom` build composing the 12 functions into `rebalance_switch` (the -q text is in .claude/commands/01-compose.md). Up to 3 attempts, varying the -q wording; on `emit_tool_plan` errors the wrapper switches model.
- **Route B:** two `--custom` builds: `preview_rebalance_switch` (no code param; checks + request_confirmation) and `confirm_rebalance_switch` (id + code; re-checks + verify + execute). The contract tests support 2 tools.
- **Route C:** `--custom` over `engine/workflow.py` alone ("expose rebalance_switch from workflow.py as one tool"). Synapse still generates the server, but the composition logic is ours. Log it in DECISIONS and say it honestly in the README ("Synapse 0.1.9 couldn't reliably compose the branching logic; it generated the server around our composed workflow").
- If the generated server COPIES engine logic instead of importing it: accept it only if the contract tests pass; record it.

## Baseline (phase 02)
Synapse Auto over `src/rekha/baseline/api.py` must list exactly the 12 tools (`python tests/mcp_client.py <server>`), with the base URL reachable. Otherwise use `rekha.baseline.sdk_server` (a docstring-verbatim MCP server) and record it. Either is fair. The README states which.

## Models / OpenRouter
- 429 / rate limits: back off (Retry-After), lower `ARENA_RPM`, continue. Daily limit reached → stop launching runs, score what exists, mark DEGRADED, and say how many runs are missing.
- > 30% ERROR runs on the controls → the model can't do tool calls reliably here: try the next tool-capable Nemotron in state/models.json, log it, and rerun the controls.
- The sweep model fails → drop it from the sweep (DEGRADED).

## Anything else
Keep the safety contract and fairness intact, prefer the smaller change, log it in DECISIONS.md.
