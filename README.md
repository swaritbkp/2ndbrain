# Lakshman Rekha: Wealth Red-Team Arena (autonomous build pack v3)
**2nd Brain Labs × Geek Room Vibe-a-thon, Track 2: "One smart tool from many small functions".**
Builder: Claude Code + Claude Opus 5.5, unattended. LLMs under test: Nemotron 3.5 via OpenRouter. (Phase 06 rewrites this README into the submission write-up.)

> Twelve small tools get talked out of compliance. One Synapse-composed tool can't be. We measure it.

## Start (about 10 minutes of your time, then walk away)
1. Install Claude Code, Python 3.11+, Node 20+ and Git. LibreOffice is optional (slide previews).
2. Unzip into an **empty, dedicated folder**. Copy `.env.example` to `.env`, then set `OPENROUTER_API_KEY` and a long random `REKHA_TOKEN_SECRET`. Use **paid** Nemotron variants with a few dollars of OpenRouter credit; free variants rate-limit the arena.
3. Check the plan: `.\run_autonomous.ps1 -DryRun`. It parses the script and prints the phases.
4. Go: `.\run_autonomous.ps1`. Watch `PROGRESS.md`; the result is `FINAL_REPORT.md`. If it stops, `STOPPED.md` gives the exact fix, then resume with `-StartPhase N`.

## What changed in v3 (and why)
| Risk raised | Fix |
|---|---|
| Orchestration overhead and review loops | 7 phases (was 11), 2 subagents (was 4), 1 rules file (was 5). The reviewer blocks **only** on real blockers; style is a NOTE. Max 2 review rounds, a wall-clock timeout per phase, and "same error twice → next fallback". |
| Thin config files | Real structure: FIFO lots, graded liquid exit load, cess, the per-FY LTCG exemption, debt-at-slab, stamp duty/STT, SEBI riskometer labels, cut-offs. Every value carries a `verified` flag. Equity rates were confirmed for FY 2026-27. |
| No seed data or starter tests | The engine is **pre-built and tested**: 12 functions, 8 seeded clients (each triggers one guardrail), **76 tests** (39 engine golden + 11 workflow + 9 scorer + 2 baseline-fairness + 15 contract). Golden tests are the spec: the agent may add tests, never weaken them. |
| Late UI | The viewer moved to phase 03, built on bundled **sample results** (`fixtures/`), so a demoable artifact exists before the expensive arena run. |
| Tooling lock-in to .claude/ | The driver runs `scripts/verify_phase.py` **itself** after every phase (tests, artifacts, a hash check of Synapse-generated servers, `.env` not tracked, a secret scan). The agent's claim of PASS is overridden if verification fails, whichever agent ran the phase. |
| Lean dependency manifest | Complete, with an MCP v1 pin. `scripts/check_deps.py` imports everything in preflight and in the clean-room check. |
| (Found while building) an agent-visible token can be self-replayed | **Out-of-band confirmation**: a 6-digit code goes to an "RM console" table no tool can read. Only the human, or the arena's scripted human, can supply it. This makes the baseline-vs-composed comparison real and fair. |

## Phases
| # | Phase | Critical | What it does |
|---|---|---|---|
| 00 | preflight | yes | venv, deps, Synapse CLI, OpenRouter model discovery + tool-call ping, golden tests |
| 01 | compose | yes | Synapse `--custom` → `rebalance_switch`; must pass 15 contract tests (Routes A/B/C) |
| 02 | baseline-runner | yes | 12-tool baseline, arena runner + scripted human, Hinglish/novel attacks, smoke run |
| 03 | viewer | no | Streamlit replay, scorecard, audit chain + receipts (offline) |
| 04 | arena | yes | full run (resumable, budgeted), Nemotron Super vs Lightning sweep, fairness audit |
| 05 | distinctive | no | mutation testing, adaptive attacker, economics, language parity |
| 06 | submission | no | README write-up, .pptx deck, demo runner, clean-room check, FINAL_REPORT |

## Already built and tested (before the run)
`src/rekha/engine/` (functions, workflow oracle, audit chain, receipts, mutants) · `data/seed.py` · `src/rekha/arena/{scorer,aggregate,models}.py` + `attacks.yaml` · `src/rekha/baseline/{api,sdk_server}.py` · `scripts/` (model discovery, ping, Synapse wrapper, verifier, sample results) · `tests/`.
Run the tests yourself: `python -m pytest -q`. The contract tests run with `COMPOSED_SERVER=scripts/reference_composed_server.py`.

*Fictional data. Indicative estimates only. Not tax or investment advice.*
