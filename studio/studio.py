#!/usr/bin/env python3
"""Studio CLI — the single entry point, and the one a Claude Routine drives.

    python3 studio.py status                    where every episode stands
    python3 studio.py next                      the one thing to do now (add --json)
    python3 studio.py run --production ash-river --season 1 --episode 1
    python3 studio.py run ... --live            call real providers
    python3 studio.py score --production ...    grade a beat sheet and stop
    python3 studio.py test                      the retention engine test suite
    python3 studio.py doctor                    is this checkout able to produce?

Exit codes are the contract a Routine reads:
    0  done / greenlit / nothing to do
    1  rework or held — actionable, a rework order was written
    2  killed — needs a human
    3  bad invocation
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

try:                                     # installed at repo root
    from pipeline.ceo import KILLED, Studio
    from pipeline.models import Doctrine, Episode, TwistLedger
    from pipeline.retention import RetentionEngine
    from pipeline.slate import Slate
except ImportError:                      # still nested under studio/
    from studio.pipeline.ceo import KILLED, Studio
    from studio.pipeline.models import Doctrine, Episode, TwistLedger
    from studio.pipeline.retention import RetentionEngine
    from studio.pipeline.slate import Slate


def _episode_dir(production: str, season: int, episode: int) -> Path:
    return ROOT / "productions" / production / f"season-{season:02d}" / f"ep{episode:02d}"


def _paused() -> bool:
    """The kill switch. `touch PAUSE`, commit, and every Routine no-ops on its next run.

    Enforced here rather than only in the Routine prompts, so it holds even if a prompt
    is edited or a run is started by hand.
    """
    pause = ROOT / "PAUSE"
    if not pause.exists():
        return False
    reason = pause.read_text(encoding="utf-8").strip()
    print(f"PAUSED — the studio is halted.{(' ' + reason) if reason else ''}")
    print("Remove the PAUSE file to resume.")
    return True


def cmd_status(args: argparse.Namespace) -> int:
    slate = Slate(ROOT)
    print(json.dumps(slate.as_dict(), indent=2) if args.json else slate.render())
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    if _paused():
        return 0
    directive = Slate(ROOT).next_action()
    if args.json:
        print(json.dumps(directive.__dict__, indent=2))
    else:
        print(directive.render())
    # A directive owned by the CEO means the machine has run out of authority.
    return 2 if directive.owner == "ceo" else 0


def cmd_score(args: argparse.Namespace) -> int:
    beatsheet = _episode_dir(args.production, args.season, args.episode) / "beatsheet.yaml"
    if not beatsheet.exists():
        print(f"no beat sheet at {beatsheet}", file=sys.stderr)
        return 3
    doctrine = Doctrine.load(ROOT / "doctrine")
    ledger_path = beatsheet.parent.parent / "twist-ledger.yaml"
    ledger = TwistLedger.load(ledger_path) if ledger_path.exists() else TwistLedger.empty()
    report = RetentionEngine(doctrine).score(Episode.load(beatsheet), ledger)
    print(report.render())
    gate = doctrine.gate("script_greenlight")
    passed = report.passes(gate)
    print(f"\nscript_greenlight: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


def cmd_run(args: argparse.Namespace) -> int:
    if _paused():
        return 0
    beatsheet = _episode_dir(args.production, args.season, args.episode) / "beatsheet.yaml"
    if not beatsheet.exists():
        print(f"no beat sheet at {beatsheet}", file=sys.stderr)
        return 3
    studio = Studio(ROOT, args.production, args.season, args.episode, dry_run=not args.live)
    run = studio.produce()
    print(Studio.summary(run))
    if run.ok:
        return 0
    return 2 if run.verdict == KILLED else 1


def cmd_test(_: argparse.Namespace) -> int:
    return subprocess.call([sys.executable, str(ROOT / "tests" / "test_retention.py")])


def cmd_doctor(_: argparse.Namespace) -> int:
    """Can this checkout actually produce? A Routine runs this before anything else."""
    import os
    import shutil

    problems, notes = [], []

    if sys.version_info < (3, 11):
        problems.append(f"python {sys.version_info.major}.{sys.version_info.minor}, need 3.11+")
    try:
        import yaml  # noqa: F401
    except ImportError:
        problems.append("pyyaml not installed (pip install pyyaml)")

    for d in ("doctrine", "agents", "pipeline", "productions"):
        if not (ROOT / d).is_dir():
            problems.append(f"missing {d}/")

    try:
        Doctrine.load(ROOT / "doctrine")
        notes.append("doctrine loads")
    except Exception as exc:                                  # noqa: BLE001
        problems.append(f"doctrine will not load: {exc}")

    render_keys = ["VEO_API_KEY", "RUNWAY_API_KEY", "KLING_API_KEY"]
    publish_keys = ["YOUTUBE_REFRESH_TOKEN", "TIKTOK_ACCESS_TOKEN", "IG_ACCESS_TOKEN"]
    have_render = [k for k in render_keys if os.environ.get(k)]
    have_publish = [k for k in publish_keys if os.environ.get(k)]
    notes.append(f"render lanes credentialled: {have_render or 'none — dry-run only'}")
    notes.append(f"publish targets credentialled: {have_publish or 'none — dry-run only'}")
    notes.append(f"ffmpeg: {'present' if shutil.which('ffmpeg') else 'absent — plan only'}")

    slate = Slate(ROOT)
    notes.append(f"productions: {slate.productions() or 'none'}")

    for n in notes:
        print(f"  ok    {n}")
    for p in problems:
        print(f"  FAIL  {p}")
    print(f"\n{'ready to produce' if not problems else f'{len(problems)} problem(s)'}")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="studio.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def target(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--production", required=True)
        sp.add_argument("--season", type=int, default=1)
        sp.add_argument("--episode", type=int, required=True)

    s = sub.add_parser("status", help="where every episode stands")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("next", help="the single next action")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_next)

    s = sub.add_parser("score", help="grade a beat sheet and stop")
    target(s)
    s.set_defaults(func=cmd_score)

    s = sub.add_parser("run", help="run an episode through every agent and gate")
    target(s)
    s.add_argument("--live", action="store_true",
                   help="call real generation and publishing providers")
    s.set_defaults(func=cmd_run)

    sub.add_parser("test", help="run the retention engine test suite").set_defaults(func=cmd_test)
    sub.add_parser("doctor", help="can this checkout produce?").set_defaults(func=cmd_doctor)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
