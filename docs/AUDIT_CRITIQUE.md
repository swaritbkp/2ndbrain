# Audit critique (v1 submission, commit 8a3fcbe)
Reviewer stance: Staff engineer + hackathon judge. Goal: find what does not hold up before a judge does.
Scope read: `README.md`, `FINAL_REPORT.md`, `docs/SPEC.md`, `docs/DECISIONS.md`, `results/latest/SUMMARY.md`, `src/rekha/engine/*`, `src/rekha/arena/*`, `src/rekha/viewer/*`, `preview_/confirm_rebalance_switch_server.py`.

## 1. What is defensible vs. what is thin
**Defensible (keep, lead with these):**
- **Out-of-band confirmation.** The 6-digit code is written to `oob_outbox`, a table no MCP tool reads. The model can't self-approve, replay a code it never saw, or forge one that verifies. This is the core idea, and the scorer checks it from DB state (`FORGED_CONFIRMATION` requires a verified code the human never disclosed).
- **Ground truth from DB state.** `scorer.py` replays executed switches against a pristine DB and checks the real distributor rules. Model text is never scored. This makes the 198-run table re-checkable (the v1 audit re-scored 198/198 with 0 mismatches).
- **Hash-chained audit.** `verify_audit_chain` recomputes SHA-256 over every row; the tamper demo shows the first broken row.
- **Honest Synapse findings.** Route A failed because Synapse 0.1.9 emits optional parameters as required; Synapse Auto dropped all non-path parameters. These are real, reproducible tool findings, with failed outputs kept in `logs/failed_builds/` (local) and the reasoning in `docs/DECISIONS.md`.

**Thin or over-claimed:**
- The README title had to be walked back once already ("can't be pressured"). The tagline in the original pack ("Twelve small tools get talked out of compliance") is not what the data shows: the baseline resisted 87/90 attacks.
- "Composition" is partly the hand-written workflow restated in prompt text. The `-q` prompts for the final builds name every result key and branch. Synapse wrote the code, but the design came from `workflow.py`. That should be said plainly.
- The deck (`.pptx`) was never rendered or visually checked.
- The adaptive attacker is described as "3 generations" but generation 0 is the scripted case; it selected A01–A06 by fallback, not by difficulty.

## 2. Benchmark validity
| Finding | Why it matters | Severity |
|---|---|---|
| Attack delta is 3/90 vs 0/90, all from one case (N04) | The effect is one attack class (fake system notice). Case-level n is 1 case × 3 runs; per-run Wilson CIs overstate certainty. | High (framing) |
| Composed controls 6/9 vs 9/9 (K02 3/3 false block) | The composed surface removed discovery along with execution. A guard that blocks legitimate work has a real cost; v1 shipped the regression unfixed. | High (design) |
| Arena mutation reach 1/7 | Attack scripts never supply a real code, so the agent stops at "read me the code" before any disabled check is reached. The arena half of mutation testing measured script design, not guardrail depth. | High (method) |
| Attacker = defender model (Nemotron Super) | An attacker that shares the defender's priors may under-explore. The adaptive result (0 violations) is weak evidence. | Medium |
| One model family, T=0.2, 3 runs/case | Results may not transfer to other models or higher temperature. | Medium |
| Controls get a "Yes, go ahead." nudge | Disclosed, applied to both arms, and it helps the baseline; acceptable. | Low |
| 4 baseline runs hit the 15-call cap | A later violation can't be ruled out; all were SAFE at cut-off. | Low |

## 3. Production readiness gaps
- **No CI.** Tests, contract tests and the secret scan only run when someone remembers to.
- **No lint/format gate.** No `ruff` config; style drift is unchecked.
- **Privilege boundary is implicit.** The composed surface has write-path tools only. There is no documented rule for what read access an agent should get, which is how K02 happened.
- **Threat model is scattered.** The safety contract lives in `docs/RULES.md` and the README; there's no STRIDE-style table, no trust-boundary diagram, no TOCTOU discussion.
- **Viewer UX.** The scorecard shows numbers per agent but no deltas; the replay doesn't call out *why* a run violated; no KPI strip for a judge who has 30 seconds.
- **Reproducibility.** Running the arena needs an OpenRouter key; offline reproduction is limited to re-scoring stored DBs, which is not documented as a first-class path.
- **Nested `runs_db/` folders** are tracked by accident (`.gitignore` matches only one level). Harmless (fictional data) but unintentional.

## 4. Action plan (executed in Step 2, ordered by impact)
1. **Fix K02 with read/write separation:** add a Synapse-generated, strictly read-only `lookup_holdings` tool (holdings + ELSS tranche lock-in, no CRM notes, no OTPs, no writes). Prove read-only and OTP-blind in contract tests; re-run the composed arm.
2. **Fix mutation reach:** OTP-assisted mutation runs, where the human *does* read out a real code, so the server's internal checks are the only barrier. A mutant is killed when an illegal commit lands.
3. **Add 4 high-signal attacks** (N07–N10): note-borne instruction via the profile, cap smurfing across consecutive orders, stale-approval reuse for a second tranche, compliance-waiver escalation with a fabricated reference. Re-run both arms in full (v2) and archive v1.
4. **Deterministic number check:** `scripts/check_numbers.py` recomputes the scorecard from raw run JSONs and fails on any mismatch; run it in CI.
5. **CI:** clean install, full tests incl. contract tests, `ruff`, secret scan over tree and history.
6. **Viewer:** KPI strip (violation, control, tool-call, schema-token deltas), per-run "why" badges, deep links for every demo beat.
