# Decisions made autonomously
| date | phase | decision | why | how to undo |
|---|---|---|---|---|
| 2026-11-23 | pre-build | Out-of-band confirmation codes instead of agent-visible tokens | an agent-visible token can be self-replayed by the agent, which would make confirmation meaningless in both arms | n/a (core design) |
| 2026-11-23 | pre-build | `execute_switch` enforces platform rules only (units, ELSS lock-in) | mirrors real back-office primitives; distributor compliance is the orchestrator's job, which is what Track 2 composition is about | n/a |
| 2026-11-23 | 00-preflight | git core.autocrlf=false | CRLF rewriting would change file hashes and trip build-manifest fingerprint checks | `git config core.autocrlf true` |
| 2026-11-23 | 00-preflight | Synapse fallbacks = deepseek-v4.1-flash-1017, gpt-6-luna (user-set in env) | both verified tool-capable on OpenRouter; Nemotron may fail emit_tool_plan | edit SYNAPSE_MODEL_FALLBACKS |
| 2026-11-23 | 00-preflight | Unverified config values kept as-is and labelled illustrative: cut-off times (rules.yaml), liquid graded exit load (schemes.yaml), one tax block + transaction costs (tax.yaml) | engine math is spec'd by golden tests; we disclose rather than alter | set verified:true after checking primary sources |
| 2026-11-23 | 00-preflight | No Windows portability fixes needed | mcp_client.py/verify_phase.py already merge os.environ and use sys.executable; run_autonomous.ps1 resolves .venv python and parses under -DryRun | n/a |
