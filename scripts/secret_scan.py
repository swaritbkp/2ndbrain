"""Secret-pattern scan over tracked files AND the full git history. Exit 1 on any hit.
Also fails if a .env file or .venv/ path was ever committed, or a tracked blob is larger than 25 MB.
python scripts/secret_scan.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = re.compile(
    rb"sk-or-v1-[0-9a-f]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{32,}|AIza[0-9A-Za-z_\-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}"
    rb"|github_pat_[A-Za-z0-9_]{30,}|xox[abpr]-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
ALLOW = {Path("scripts/secret_scan.py"), Path("scripts/verify_phase.py")}  # files that contain the patterns themselves
MAX_BLOB = 25 * 1024 * 1024


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def main() -> int:
    bad = []
    for name in git("ls-files", "-z").split(b"\0"):
        if not name:
            continue
        p = Path(name.decode())
        f = ROOT / p
        if not f.is_file():
            continue
        if f.stat().st_size > MAX_BLOB:
            bad.append(f"tracked file over 25 MB: {p}")
        if p not in ALLOW and PATTERNS.search(f.read_bytes()):
            bad.append(f"secret pattern in tracked file: {p}")
    paths = set(git("log", "--all", "--name-only", "--pretty=format:").decode(errors="replace").split())
    bad += [
        f"committed in history: {x}" for x in sorted(paths) if re.search(r"(^|/)\.env$", x) or x.startswith(".venv/")
    ]
    for commit in git("rev-list", "--all").split():
        for m in PATTERNS.finditer(git("show", "--format=", "-p", "--text", commit.decode())):
            ctx = m.group(0)[:12]
            if b"compile(" not in ctx:
                bad.append(f"secret pattern in history: commit {commit.decode()[:10]} ({ctx!r}...)")
                break
    for b in bad:
        print("FAIL:", b)
    print("secret scan clean" if not bad else f"{len(bad)} finding(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
