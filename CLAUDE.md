# CLAUDE.md: Lakshman Rekha (read before any work)

## You are running UNATTENDED
- Never ask questions or wait for input. Ambiguity → choose the option that keeps the safety contract and fairness intact, log it in `docs/DECISIONS.md` (`date | phase | decision | why | undo`), and continue.
- Failures → follow `docs/FALLBACKS.md`. **If the same error happens twice, switch to the next fallback. Don't retry a third time.**
- Hard stops are only those in FALLBACKS.md. On one, write `STOPPED.md` (what failed, log lines, exact human fix) and `state/<phase>.json` with status STOP.
- End every phase by writing `state/<phase>.json` (`docs/STATE_SCHEMA.md`). The driver independently re-verifies with `scripts/verify_phase.py`, so claims don't count; artifacts and green tests do.
- Keep it lean: no new docs unless the phase asks for them. Don't polish style. Fix blockers, note nits.

## Mission
Track 2 entry, 2nd Brain Labs × Geek Room Vibe-a-thon: **"One smart tool from many small functions"** (Synapse CLI, Custom mode, Python).
We show, with measured numbers, that composing 12 small wealth-desk functions into ONE Synapse-composed, confirmation-gated MCP tool makes an AI agent much harder to pressure into unsafe trades than the same 12 functions exposed as separate tools, **without** blocking legitimate work.

## What already exists (built and tested before the run; DO NOT rewrite)
- `src/rekha/engine/`: 12 public functions (`functions.py`), reference composition (`workflow.py`), hash-chained audit, receipts, mutation hooks. Data: `data/seed.py`.
- `tests/`: 61 golden/workflow/scorer/baseline tests + 15 contract tests (`tests/contract/`) that any composed server must pass (validated against `scripts/reference_composed_server.py`).
- `src/rekha/arena/scorer.py` (ground truth from DB state only), `aggregate.py`, `models.py`, `attacks.yaml` (15 core cases).
- `src/rekha/baseline/api.py` (FastAPI, 12 routes) and `sdk_server.py` (fallback).
- `scripts/`: env/model/ping checks, `synapse_build.py` (always build through this), `verify_phase.py`, `make_sample_results.py`.
**Golden tests are the spec.** If your change breaks one, your change is wrong. You may ADD tests. Never weaken or delete existing ones.

## The core design (why the comparison is fair and real)
- `execute_switch` is the transaction-platform primitive. It enforces only platform rules (units, ELSS lock-in), not distributor compliance.
- Human confirmation is **out-of-band**: `request_confirmation` sends a 6-digit code to the "RM console" (`oob_outbox` table). **No tool ever returns it.** Only the human (the arena's simulated human) can read it out.
- Composed tool: checks + code verification + execution in one guarded flow; the primitives are hidden.
- Baseline: the same 12 functions as 12 tools, so the agent can call `execute_switch` directly. Same model, prompt and script.

## Rules: read docs/RULES.md (safety contract, fairness, Synapse facts, domain, Python style)

## Environment
Windows 11. The Bash tool is Git Bash. Use the venv python (`.venv/Scripts/python` on Windows, `.venv/bin/python` elsewhere; recorded in docs/ENVIRONMENT.md). LLMs: **OpenRouter only** (`OPENROUTER_API_KEY`); models are resolved in `state/models.json`. Never read `.env` (a hook blocks it). Commit after each green step (`git add -A && git commit -m "<phase>: ..."`); never push.
