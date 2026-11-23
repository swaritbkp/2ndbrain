# Archived result sets (read-only)
- `v1_latest/`: the v1 submission's `results/latest` (commit 8a3fcbe), moved here unchanged with `git mv` when v2 replaced it. Its `SUMMARY.md`, `fairness_audit*.json`, `mutation.json`, `adaptive.json`, `economics.json` and `language.json` describe v1: suite of 33 cases, composed surface = preview + confirm only (no read-only lookup). Paths inside those files that say `results/latest` mean this folder.
- The raw v1 run folders stay where they were: `results/20261123_nemotron-3.5-super-vl/` (full v1 arena) and `results/20261123_sweep_nemotron-3.5-lightning/` (v1 sweep).

Why v2 exists: `docs/AUDIT_CRITIQUE.md`. What changed: `docs/BENCHMARK_METHODOLOGY.md` ("v1 → v2").
