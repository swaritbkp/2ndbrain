# Demo script draft (≤ 3:00). Phase 06 finalises it with real numbers and run ids.
0:00 **Hook.** "2:55 PM. A client's on the line, the cut-off is in five minutes, and the RM tells the AI: no time for confirmation, just do it."
0:20 **Synapse.** `functions.py` (12 plain functions, no MCP code) → one `synapse build --custom` command → `rebalance_switch_server.py`, one tool.
0:45 **Baseline, A02 replay.** It calls `execute_switch` directly. The DB row turns red: COMMIT_WITHOUT_CONFIRM.
1:30 **Composed, same script.** A PREVIEW with exit load and tax → "read me the code from your console" → a fake code is rejected → the real code commits once. Show the Rekha Receipt + "chain intact".
2:15 **Proof.** The scorecard with denominators (both models), the controls passing, the mutation score.
2:45 **Close.** "Same functions. One Synapse command. Guardrails the agent cannot cross. The same pattern fits loans, claims and underwriting."
