"""OpenRouter cost ledger from per-run records (cost_usd, prompt/completion tokens). Writes results/latest/cost_ledger.json.

Each source folder is counted once. results/latest/*__run*.json is a copy of the v2 full run and is NOT counted again.
Not metered here (no per-call record): Synapse build attempts, model pings, the v1 adaptive attacker's own 24 calls.
python scripts/cost_ledger.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
SOURCES = [
    ("v1", "smoke run", "smoke", "*__run*.json"),
    ("v1", "full arena (33 cases x 3 x 2)", "20261123_nemotron-3.5-super-vl", "*__run*.json"),
    ("v1", "Lightning sweep (core x 2)", "20261123_sweep_nemotron-3.5-lightning", "*__run*.json"),
    ("v1", "mutation, scripted arena", "archive/v1_latest/mutation_runs", "*.json"),
    ("v1", "adaptive attacker, agent runs", "archive/v1_latest/adaptive_runs", "*.json"),
    ("v2", "full arena (37 cases x 3 x 2)", "20261123_v2_nemotron-3.5-super-vl", "*__run*.json"),
    ("v2", "Lightning sweep (core x 2)", "20261123_v2_sweep_nemotron-3.5-lightning", "*__run*.json"),
    ("v2", "mutation, scripted + OTP-assisted arena", "latest/mutation_runs", "*.json"),
]


def main() -> int:
    rows, tot = [], {"v1": [0, 0, 0.0], "v2": [0, 0, 0.0]}
    for ver, label, folder, pat in SOURCES:
        recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((RES / folder).glob(pat))]
        recs = [r for r in recs if "score" in r]
        n, tok = len(recs), sum(r.get("prompt_tokens", 0) + r.get("completion_tokens", 0) for r in recs)
        usd = round(sum(r.get("cost_usd", 0) for r in recs), 4)
        rows.append(
            {"version": ver, "item": label, "folder": f"results/{folder}", "runs": n, "tokens": tok, "usd": usd}
        )
        tot[ver][0] += n
        tot[ver][1] += tok
        tot[ver][2] += usd
    out = {
        "rows": rows,
        "v1": {"runs": tot["v1"][0], "tokens": tot["v1"][1], "usd": round(tot["v1"][2], 4)},
        "v2_incremental": {"runs": tot["v2"][0], "tokens": tot["v2"][1], "usd": round(tot["v2"][2], 4)},
        "total_runs": tot["v1"][0] + tot["v2"][0],
        "total_tokens": tot["v1"][1] + tot["v2"][1],
        "total_usd": round(tot["v1"][2] + tot["v2"][2], 4),
        "not_metered": "Synapse build attempts, model pings, adaptive attacker calls (no per-call records)",
        "pricing_source": "state/models.json (OpenRouter /models pricing at preflight)",
    }
    (RES / "latest" / "cost_ledger.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
