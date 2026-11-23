"""Driver-side INDEPENDENT verification. The driver trusts this, not the agent's claims.

Works with any coding agent (it doesn't depend on .claude/). Usage: python scripts/verify_phase.py <phase-id>
Exit 0 = verified. Writes state/<phase>.verify.json with the failures (fed to the retry prompt).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SECRET_RX = re.compile(r"(sk-or-v1-[0-9a-f]{20,}|sk-[A-Za-z0-9]{32,}|AIza[0-9A-Za-z_\-]{30,})")


def sh(args, env=None, timeout=1800):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, env=e, timeout=timeout)
    return p.returncode, (p.stdout or "")[-3000:] + (p.stderr or "")[-2000:]


def read(p):
    f = ROOT / p
    return f.read_text(encoding="utf-8").strip() if f.exists() else ""


def check_tests(fails, extra_env=None, paths=("tests",)):
    code, out = sh([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", *paths], extra_env)
    if code != 0:
        fails.append(f"pytest failed {paths}: {out[-1500:]}")


def check_integrity(fails):
    man = ROOT / "state" / "build_manifest.json"
    if man.exists():
        for rel, info in json.loads(man.read_text(encoding="utf-8")).items():
            f = ROOT / rel
            if f.exists() and hashlib.sha256(f.read_bytes()).hexdigest() != info["sha256"]:
                fails.append(f"generated server hand-edited after build: {rel}")
    code, out = sh(["git", "ls-files"])
    if code == 0:
        files = out.split()
        if ".env" in files:
            fails.append(".env is tracked by git")
        for rel in files:
            f = ROOT / rel
            if f.is_file() and f.stat().st_size < 2_000_000 and f.suffix in {".py", ".md", ".json", ".yaml", ".yml", ".txt", ".ps1", ".sh", ".log"}:
                if SECRET_RX.search(f.read_text(encoding="utf-8", errors="ignore")):
                    fails.append(f"possible secret in tracked file: {rel}")


def need(fails, *paths):
    for p in paths:
        if not (ROOT / p).exists():
            fails.append(f"missing artifact: {p}")


def json_has(fails, path, pred, msg):
    f = ROOT / path
    try:
        if not pred(json.loads(f.read_text(encoding="utf-8"))):
            fails.append(msg)
    except Exception as e:
        fails.append(f"{path}: {type(e).__name__}: {e}")


def main(phase: str) -> int:
    fails: list[str] = []
    check_integrity(fails)
    if phase.startswith("00"):
        need(fails, "state/models.json", "docs/ENVIRONMENT.md")
        check_tests(fails)
    elif phase.startswith("01"):
        need(fails, "state/composed_server.txt", "state/build_manifest.json")
        srv = read("state/composed_server.txt")
        check_tests(fails, {"COMPOSED_SERVER": srv})
        if "reference_composed_server" in srv:
            fails.append("composed server must be Synapse-generated, not the reference server")
        man_f = ROOT / "state" / "build_manifest.json"
        man = json.loads(man_f.read_text(encoding="utf-8")) if man_f.exists() else {}
        for s in [x.strip() for x in srv.split(",") if x.strip()]:
            if s.replace("\\", "/") not in man:
                fails.append(f"{s} is not in state/build_manifest.json, so it wasn't produced via scripts/synapse_build.py")
    elif phase.startswith("02"):
        need(fails, "state/baseline_server.txt", "src/rekha/arena/runner.py", "src/rekha/arena/attacks.yaml", "results/smoke/scorecard.json")
        check_tests(fails, {"COMPOSED_SERVER": read("state/composed_server.txt")})
        json_has(fails, "results/smoke/scorecard.json", lambda c: {"baseline", "composed"} <= set(c["agents"]), "smoke scorecard lacks both agents")
    elif phase.startswith("03"):
        need(fails, "src/rekha/viewer/app.py", "tests/test_viewer_smoke.py")
        check_tests(fails, paths=("tests/test_viewer_smoke.py",))
    elif phase.startswith("04"):
        need(fails, "results/latest/scorecard.json")
        json_has(fails, "results/latest/scorecard.json",
                 lambda c: all(c["agents"].get(a, {}).get("attack_runs", 0) >= 12 for a in ("baseline", "composed")),
                 "scorecard needs >= 12 attack runs per agent")
        need(fails, "results/latest/fairness_audit.json")
    elif phase.startswith("05"):
        pass  # non-critical; artifacts optional (listed as DEGRADED by the agent)
    elif phase.startswith("06"):
        need(fails, "README.md", "FINAL_REPORT.md", "docs/DEMO_FINAL.md")
        check_tests(fails, {"COMPOSED_SERVER": read("state/composed_server.txt")})
    out = {"phase": phase, "verified": not fails, "failures": fails}
    (ROOT / "state").mkdir(exist_ok=True)
    (ROOT / "state" / f"{phase}.verify.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
