"""Run a Synapse --local build with a timeout, model fallbacks and an integrity manifest.

  python scripts/synapse_build.py --label composed --cwd . -- --custom -q "..."
  python scripts/synapse_build.py --label baseline --cwd src/rekha/baseline -- --auto --all-endpoints

- Provider: SYNAPSE_PROVIDER (default openrouter). Model: state/models.json 'synapse', then SYNAPSE_MODEL_FALLBACKS.
  The model flag is passed only if `synapse build --help` lists one (--model/-m); otherwise this is recorded.
- On 'emit_tool_plan' failures, the next fallback model is tried.
- New/changed *_server.py files are hashed into state/build_manifest.json, so verify_phase.py can detect hand edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rekha.arena import models  # noqa: E402

MANIFEST = ROOT / "state" / "build_manifest.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def servers(cwd: Path) -> dict[str, str]:
    return {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in cwd.glob("*_server.py")}


def model_flag() -> str | None:
    exe = shutil.which("synapse")
    if not exe:
        return None
    try:
        h = subprocess.run([exe, "build", "--help"], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return None
    m = re.search(r"(--model)\b", h)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("rest", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    rest = [x for x in a.rest if x != "--"]
    exe = shutil.which("synapse")
    if not exe:
        print("synapse not found on PATH")
        return 2
    cwd = (ROOT / a.cwd).resolve()
    provider = os.environ.get("SYNAPSE_PROVIDER", "openrouter")
    flag = model_flag()
    candidates = [models.get("synapse")] + [m.strip() for m in os.environ.get("SYNAPSE_MODEL_FALLBACKS", "").split(",") if m.strip()]
    candidates = [c for c in candidates if c] or [""]
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    before = servers(cwd)
    result = {"label": a.label, "cwd": str(cwd.relative_to(ROOT)), "provider": provider, "model_flag": flag, "attempts": []}
    for model in candidates if flag else candidates[:1]:
        cmd = [exe, "build", "--local", "--provider", provider] + ([flag, model] if flag and model else []) + rest
        t0 = time.time()
        try:
            p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=a.timeout, stdin=subprocess.DEVNULL)
            out, code = (p.stdout or "") + (p.stderr or ""), p.returncode
        except subprocess.TimeoutExpired as e:
            out, code = f"TIMEOUT after {a.timeout}s\n{(e.stdout or b'')[-4000:]!r}", -1
        logf = log_dir / f"synapse_{a.label}_{int(t0)}.log"
        logf.write_text(" ".join(cmd) + "\n\n" + out, encoding="utf-8")
        result["attempts"].append({"model": model or "(provider default)", "exit": code, "log": str(logf.relative_to(ROOT)),
                                   "secs": round(time.time() - t0, 1), "emit_tool_plan_error": "emit_tool_plan" in out})
        if code == 0 and "emit_tool_plan" not in out:
            break
    after = servers(cwd)
    changed = {k: v for k, v in after.items() if before.get(k) != v}
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    man.update({k: {"sha256": v, "label": a.label, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")} for k, v in after.items()})
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")
    result["generated_or_changed"] = list(changed)
    print(json.dumps(result, indent=2))
    return 0 if result["attempts"][-1]["exit"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
