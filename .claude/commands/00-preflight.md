---
description: Phase 00: environment, OpenRouter models, dependencies
---
# 00 Preflight
1. Python ≥ 3.11, Node ≥ 20, git. Create `.venv`, `pip install -r requirements.txt`, then `python scripts/check_deps.py`. Record the venv python path in docs/ENVIRONMENT.md and use it from now on.
2. `git init` if needed; commit the untouched pack as the first commit.
3. Synapse: `npm install -g @2ndbrainlabs-ai/synapse-cli` if `synapse --version` fails. Save `synapse --version`, `synapse build --help` and `synapse model --help` output to docs/ENVIRONMENT.md (needed by phase 01 to choose a model).
4. `python scripts/env_check.py` (required keys) → `python scripts/openrouter_models.py` (writes state/models.json) → `python scripts/ping_model.py`. Any of these failing after 3 tries = hard stop.
5. `python data/seed.py --reset` and `python -m pytest -q` (all golden tests must pass on this machine).
6. `python scripts/make_sample_results.py` (viewer fixtures).
Acceptance: deps import, models resolved + ping OK, tests green, docs/ENVIRONMENT.md written (no secrets).

## Finish
1. Invoke the **reviewer** subagent: "Review phase 00-preflight against .claude/commands/00-preflight.md". Fix only BLOCKERS. Max 2 review rounds; then decide the status yourself.
2. Run `python scripts/verify_phase.py 00-preflight` yourself. It must exit 0 for PASS or DEGRADED.
3. `git add -A && git commit -m "00-preflight: <summary>"`. Append one line to PROGRESS.md and a short section to docs/BUILD_LOG.md.
4. Write `state/00-preflight.json` (docs/STATE_SCHEMA.md). End your turn.
