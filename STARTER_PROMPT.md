# Starter prompt (only if you prefer ONE interactive session over run_autonomous.ps1)

The driver script is the robust way: a fresh context per phase, timeouts, independent verification, and it sleeps through usage limits.
If you still want one session: start Claude Code in this folder with prompts disabled (otherwise the first unlisted command stalls the run):

    claude --model claude-opus-5-5 --dangerously-skip-permissions

Paste everything below the line.

---
You are the ORCHESTRATOR of an unattended build. No human will answer until you finish. Never ask questions.
Read CLAUDE.md, docs/FALLBACKS.md and docs/STATE_SCHEMA.md. For each file in .claude/commands/ in order (00 → 06):
1. Skip it if state/<phase>.json says PASS or DEGRADED AND `python scripts/verify_phase.py <phase>` exits 0.
2. Otherwise spawn ONE general-purpose subagent: "You are running UNATTENDED. Read CLAUDE.md, then execute .claude/commands/<phase>.md exactly. Never ask questions; follow docs/FALLBACKS.md. End by writing state/<phase>.json." Keep your own context small. The phase work happens in the subagent.
3. Then run `python scripts/verify_phase.py <phase>` YOURSELF. Treat a verifier failure as FAIL, whatever the state file says.
4. FAIL → a fresh subagent retry that reads state/<phase>.verify.json first (max 3 for phases 00/01/02/04, 2 for the others). STOP, or a critical phase failing → make sure STOPPED.md has the exact human fix, then stop. A non-critical phase failing → note it in PROGRESS.md and continue.
5. Usage or rate limit → wait and retry the same phase. Don't skip it.
At the end, reply with: phase statuses, headline numbers with denominators, DEGRADED items, and the human next steps from FINAL_REPORT.md.
