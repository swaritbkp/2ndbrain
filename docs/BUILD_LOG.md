# Build log

## 00-preflight (PASS)
Git initialised (core.autocrlf=false). models.json: arena/attacker/synapse=nvidia/nemotron-3.5-super-vl, sweep=nvidia/nemotron-3.5-lightning, no substitutions, all pinged tool_calls=1. Synapse fallbacks validated. 76/76 tests (reference server). Reviewer PROCEED. verify_phase 00 exit 0.

## 01-compose (Route B: two Synapse Custom builds)
**Route A (2 attempts, abandoned):** `synapse_build.py --label composed --cwd . -- --custom -q "<Q>"`. Attempt 1 (Nemotron, 27 s) and attempt 2
(Nemotron emit_tool_plan failure, then DeepSeek fallback) both produced a server whose optional `confirmation_id`/`confirmation_code` were emitted as
*required* params, so the preview call failed validation (2/15 contract tests). Attempt 1 also read wrong result keys. Outputs kept unmodified in `logs/failed_builds/`.
**Route B:** `--label composed_preview` (preview, no code param) + `--label composed_confirm` (id + code). Iterations, all via the wrapper, none hand-edited:
| build | model | contract |
|---|---|---|
| preview #1 | nemotron-3.5-super-vl | did not load (`string` annotations) |
| preview #2 + confirm #1 | nemotron / nemotron | 12/15 (preview used `ok` instead of `kyc_valid`, so KYC blocks failed; no lock-in alternative) |
| preview #3 | nemotron | 14/15 (str vs int compare on `unlocked_units`) |
| **preview #4 + confirm #1** | **deepseek-v4.1-flash-1017 (fallback after emit_tool_plan) / nemotron** | **15/15** |

Final tools:
- `preview_rebalance_switch(client_id, from_scheme, to_scheme, units)`: all required strings.
- `confirm_rebalance_switch(client_id, from_scheme, to_scheme, units, confirmation_id, confirmation_code)`: all required strings.

Execution primitives (`execute_switch`, `verify_confirmation`, `request_confirmation`) are not exposed.
**Imports vs copies:** both servers *import* the 12 engine functions from `src.rekha.engine.functions` (no engine logic copied); the composition/branching is Synapse-generated.
Contract: `COMPOSED_SERVER=preview_rebalance_switch_server.py,confirm_rebalance_switch_server.py pytest tests/contract` → 15 passed. verify_phase 01 exit 0.
Notes: manifest `label` is overwritten per build (both read composed_preview); hashes are correct. confirm reads a non-existent `reason` key for lock-in blocks (falls back to `lockin_blocked`); preview is authoritative for block codes. Cosmetic only.

### Tool list (`python tests/mcp_client.py <server>`, descriptions omitted)
```json
[{"name": "preview_rebalance_switch", "inputSchema": {"properties": {"client_id": {"title": "Client Id", "type": "string"}, "from_scheme": {"title": "From Scheme", "type": "string"}, "to_scheme": {"title": "To Scheme", "type": "string"}, "units": {"title": "Units", "type": "string"}}, "required": ["client_id", "from_scheme", "to_scheme", "units"], "title": "preview_rebalance_switchArguments", "type": "object"}}]
[{"name": "confirm_rebalance_switch", "inputSchema": {"properties": {"client_id": {"title": "Client Id", "type": "string"}, "from_scheme": {"title": "From Scheme", "type": "string"}, "to_scheme": {"title": "To Scheme", "type": "string"}, "units": {"title": "Units", "type": "string"}, "confirmation_id": {"title": "Confirmation Id", "type": "string"}, "confirmation_code": {"title": "Confirmation Code", "type": "string"}}, "required": ["client_id", "from_scheme", "to_scheme", "units", "confirmation_id", "confirmation_code"], "title": "confirm_rebalance_switchArguments", "type": "object"}}]
```
