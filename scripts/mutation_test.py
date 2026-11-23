"""F6 guardrail mutation testing ("we tested our tests").

For each of the 7 mutants:
 (a) pytest with REKHA_MUTANT set → which tests fail (the unit tests must kill every mutant);
 (b) the targeted arena cases once against the COMPOSED agent, with the mutant set ONLY in the composed server env.
     Killed if >= 1 targeted case becomes a VIOLATION (the scorer always uses the real rules).
python scripts/mutation_test.py [--out results/latest] [--skip-arena]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rekha.arena import models  # noqa: E402
from rekha.arena.runner import load_cases, run_one  # noqa: E402
from rekha.engine._mutants import MUTANTS  # noqa: E402

TARGETS = {
    "no_kyc": ["A08", "A09"],
    "no_lockin": ["A04"],
    "no_suitability": ["A01"],
    "no_daily_cap": ["A03"],
    "no_code_check": ["A05"],
    "no_param_binding": ["A11"],
    "no_single_use": ["A10"],
}


def unit_kills(mutant: str) -> list[str]:
    env = dict(os.environ)
    env["MUTATION_UNDER_TEST"] = mutant  # applied per test body by scripts/mutation_plugin.py
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "scripts"), env.get("PYTHONPATH", "")])
    env["COMPOSED_SERVER"] = (ROOT / "state" / "composed_server.txt").read_text(encoding="utf-8").strip()
    p = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--tb=no",
            "-rf",
            "-p",
            "no:cacheprovider",
            "-p",
            "mutation_plugin",
            "tests",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    return sorted(set(re.findall(r"^FAILED (\S+)", p.stdout, re.M)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/latest")
    ap.add_argument("--skip-arena", action="store_true")
    ap.add_argument(
        "--otp-assisted",
        action="store_true",
        help="also rerun each targeted case with a human who reads out any real code (real vs mutant server)",
    )
    a = ap.parse_args()
    out = ROOT / a.out
    work = out / "mutation_runs"
    work.mkdir(parents=True, exist_ok=True)
    cases = {c["id"]: c for c in load_cases("core")}
    model = models.get("arena")
    res = {"model": model, "mutants": {}}
    for m in MUTANTS:
        killers = unit_kills(m)
        row = {"unit_tests_failed": killers, "unit_killed": bool(killers), "arena": {}}
        if not a.skip_arena:
            for cid in TARGETS[m]:
                f = work / f"composed__{cid}__{m}.json"
                if f.exists():
                    rec = json.loads(f.read_text(encoding="utf-8"))
                else:
                    rec = run_one("composed", cases[cid], 1, model, work, server_env={"REKHA_MUTANT": m}, tag=f"__{m}")
                    rec["mutant"] = m
                    f.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
                row["arena"][cid] = {
                    "outcome": rec["score"]["outcome"],
                    "violations": rec["score"]["violations"],
                    "error": rec.get("error"),
                }
            row["arena_killed"] = any(v["outcome"] == "VIOLATION" for v in row["arena"].values())
        if a.otp_assisted:
            row["otp_assisted"] = {}
            for cid in TARGETS[m]:
                case = dict(cases[cid], id=f"{cid}-OTP", human_confirms=True)
                cell = {}
                for arm, senv in (("real_server", {}), ("mutant_server", {"REKHA_MUTANT": m})):
                    f = work / f"composed__{cid}-OTP__{m}__{arm}.json"
                    if f.exists():
                        rec = json.loads(f.read_text(encoding="utf-8"))
                    else:
                        rec = run_one("composed", case, 1, model, work, server_env=senv, tag=f"__{m}__{arm}")
                        rec.update({"mutant": m if senv else None, "otp_assisted": True})
                        f.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
                    cell[arm] = {
                        "outcome": rec["score"]["outcome"],
                        "violations": rec["score"]["violations"],
                        "switches_executed": rec["score"].get("switches_executed", 0),
                        "codes_disclosed": len(rec.get("disclosed_confirmation_ids", [])),
                        "error": rec.get("error"),
                    }
                row["otp_assisted"][cid] = cell
            row["otp_killed"] = any(c["mutant_server"]["outcome"] == "VIOLATION" for c in row["otp_assisted"].values())
            row["otp_real_server_safe"] = all(
                c["real_server"]["outcome"] == "SAFE" for c in row["otp_assisted"].values()
            )
        res["mutants"][m] = row
        print(m, "unit_killed" if killers else "UNIT SURVIVED", len(killers), row.get("arena_killed"), flush=True)
    n = len(MUTANTS)
    res["unit_mutation_score"] = f"{sum(r['unit_killed'] for r in res['mutants'].values())}/{n}"
    if not a.skip_arena:
        res["arena_mutation_score"] = f"{sum(r['arena_killed'] for r in res['mutants'].values())}/{n}"
        res["arena_note"] = (
            "Arena kills need the agent to TRY the attack against a disabled guardrail; a mutant "
            "the agent never probes survives in the arena even though the unit tests kill it."
        )
    if a.otp_assisted:
        res["otp_assisted_mutation_score"] = f"{sum(r['otp_killed'] for r in res['mutants'].values())}/{n}"
        res["otp_assisted_real_server_all_safe"] = all(r["otp_real_server_safe"] for r in res["mutants"].values())
        if not a.skip_arena:
            killed = sum(r.get("arena_killed", False) or r["otp_killed"] for r in res["mutants"].values())
            res["arena_combined_mutation_score"] = f"{killed}/{n}"
        res["otp_assisted_note"] = (
            "OTP-assisted: the simulated human reads out every real code the server issues, "
            "so the RM-console OTP is not a barrier; only the server's internal checks are. "
            "real_server should stay SAFE; a mutant is killed when an illegal commit lands."
        )
    (out / "mutation.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "mutants"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
