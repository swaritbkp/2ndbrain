"""CLI: python -m rekha.arena run --suite core|extra|all --agents baseline,composed --runs N --model <id> --out results/<name>
python -m rekha.arena aggregate results/<name>"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rekha.arena import models
from rekha.arena.aggregate import build_scorecard


def _write_card(out: str) -> dict:
    card = build_scorecard(out)
    Path(out, "scorecard.json").write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
    return card


def main() -> int:
    ap = argparse.ArgumentParser(prog="rekha.arena")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--suite", default="core", choices=["core", "extra", "v2", "all"])
    r.add_argument("--cases", default="", help="comma list of case ids (default: all in suite)")
    r.add_argument("--agents", default="baseline,composed")
    r.add_argument("--runs", type=int, default=1)
    r.add_argument("--model", default="")
    r.add_argument("--out", required=True)
    a = sub.add_parser("aggregate")
    a.add_argument("out")
    args = ap.parse_args()
    if args.cmd == "run":
        from rekha.arena.runner import run_suite  # noqa: PLC0415

        meta = run_suite(
            args.suite,
            [x.strip() for x in args.agents.split(",") if x.strip()],
            args.runs,
            args.model or models.get("arena"),
            args.out,
            [c.strip() for c in args.cases.split(",") if c.strip()] or None,
        )
        print(json.dumps({k: v for k, v in meta.items() if k != "skipped"} | {"skipped": len(meta["skipped"])}))
    card = _write_card(args.out)
    print(
        json.dumps({ag: {k: v for k, v in s.items() if k != "by_case"} for ag, s in card["agents"].items()}, indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
