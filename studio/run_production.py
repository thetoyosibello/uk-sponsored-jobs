#!/usr/bin/env python3
"""Studio CLI.

    python3 run_production.py --production ash-river --season 1 --episode 1
    python3 run_production.py --production ash-river --season 1 --episode 1 --live
    python3 run_production.py --score-only --production ash-river --season 1 --episode 1

Exit codes: 0 greenlit, 1 rework/held, 2 killed, 3 bad invocation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.pipeline.ceo import KILLED, Studio  # noqa: E402
from studio.pipeline.models import Doctrine, Episode, TwistLedger  # noqa: E402
from studio.pipeline.retention import RetentionEngine  # noqa: E402

ROOT = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run an episode through the studio pipeline.")
    p.add_argument("--production", required=True)
    p.add_argument("--season", type=int, default=1)
    p.add_argument("--episode", type=int, default=1)
    p.add_argument("--live", action="store_true",
                   help="call real generation and publishing providers (needs credentials)")
    p.add_argument("--score-only", action="store_true",
                   help="run the Retention Engine and stop; no artefacts written")
    args = p.parse_args(argv)

    ep_dir = ROOT / "productions" / args.production / f"season-{args.season:02d}" / f"ep{args.episode:02d}"
    beatsheet = ep_dir / "beatsheet.yaml"
    if not beatsheet.exists():
        print(f"no beat sheet at {beatsheet}", file=sys.stderr)
        return 3

    if args.score_only:
        doctrine = Doctrine.load(ROOT / "doctrine")
        ledger_path = beatsheet.parent.parent / "twist-ledger.yaml"
        ledger = TwistLedger.load(ledger_path) if ledger_path.exists() else TwistLedger.empty()
        report = RetentionEngine(doctrine).score(Episode.load(beatsheet), ledger)
        print(report.render())
        gate = doctrine.gate("script_greenlight")
        print(f"\nscript_greenlight: {'PASS' if report.passes(gate) else 'FAIL'}")
        return 0 if report.passes(gate) else 1

    studio = Studio(ROOT, args.production, args.season, args.episode, dry_run=not args.live)
    run = studio.produce()
    print(Studio.summary(run))
    if run.ok:
        return 0
    return 2 if run.verdict == KILLED else 1


if __name__ == "__main__":
    raise SystemExit(main())
