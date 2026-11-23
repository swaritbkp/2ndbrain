# Decisions made autonomously
| date | phase | decision | why | how to undo |
|---|---|---|---|---|
| 2026-11-23 | pre-build | Out-of-band confirmation codes instead of agent-visible tokens | an agent-visible token can be self-replayed by the agent, which would make confirmation meaningless in both arms | n/a (core design) |
| 2026-11-23 | pre-build | `execute_switch` enforces platform rules only (units, ELSS lock-in) | mirrors real back-office primitives; distributor compliance is the orchestrator's job, which is what Track 2 composition is about | n/a |
