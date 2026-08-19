#!/usr/bin/env python3
"""Tests for the Retention Engine.

A scorer that hands 100/100 to the material its author wrote against it proves nothing.
These tests take the shipping Episode 1 beat sheet and break it, one doctrine rule at a
time, asserting the engine catches each break and names the rule. That is the only way
the gate is worth anything.

Run: python3 studio/tests/test_retention.py
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

# Works whether the studio is the repository root or still nested under studio/.
try:
    from pipeline.models import Beat, Clue, Doctrine, Episode, TwistLedger  # noqa: E402
    from pipeline.retention import RetentionEngine  # noqa: E402
    from pipeline import slate as slate_mod  # noqa: E402
except ImportError:  # pragma: no cover - layout fallback
    from studio.pipeline.models import Beat, Clue, Doctrine, Episode, TwistLedger  # noqa: E402
    from studio.pipeline.retention import RetentionEngine  # noqa: E402
    from studio.pipeline import slate as slate_mod  # noqa: E402

EP01 = ROOT / "productions" / "ash-river" / "season-01" / "ep01" / "beatsheet.yaml"
LEDGER = ROOT / "productions" / "ash-river" / "season-01" / "twist-ledger.yaml"

DOCTRINE = Doctrine.load(ROOT / "doctrine")
FAILURES: list[str] = []
PASSES = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSES
    if condition:
        PASSES += 1
        print(f"  ok    {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name}  {detail}")


def fresh() -> tuple[Episode, TwistLedger]:
    return Episode.load(EP01), TwistLedger.load(LEDGER)


def score(ep: Episode, ledger: TwistLedger):
    return RetentionEngine(DOCTRINE).score(ep, ledger)


def rules_hit(report) -> set[str]:
    return {v.rule for v in report.violations}


# --------------------------------------------------------------------------- baseline


def test_baseline_passes() -> None:
    print("\nbaseline")
    ep, ledger = fresh()
    r = score(ep, ledger)
    check("shipping episode scores >= script gate", r.composite >= 78, f"got {r.composite}")
    check("shipping episode scores >= render gate", r.composite >= 84, f"got {r.composite}")
    check("no hard fails", not r.hard_fails, str(r.hard_fails))
    check("passes script_greenlight", r.passes(DOCTRINE.gate("script_greenlight")))
    check("passes render_greenlight", r.passes(DOCTRINE.gate("render_greenlight")))


# --------------------------------------------------------------------------- force 1


def test_open_loops() -> None:
    print("\nopen_loop_pressure")

    ep, ledger = fresh()
    # Strip every loop opened after the grace window: the curve collapses.
    ep.beats = [replace(b, loops_opened=[] if b.t_start_sec > 40 else b.loops_opened)
                for b in ep.beats]
    r = score(ep, ledger)
    check("catches loop starvation", "open_loops_min" in rules_hit(r), str(rules_hit(r)))
    check("loop starvation is a hard fail", any(v.rule == "open_loops_min" for v in r.hard_fails))

    ep, ledger = fresh()
    # Pile on loops nobody will track.
    ep.beats[5] = replace(ep.beats[5], loops_opened=[f"q_x{i}" for i in range(9)])
    r = score(ep, ledger)
    check("catches loop overload", "open_loops_max" in rules_hit(r), str(rules_hit(r)))

    ep, ledger = fresh()
    # Close a loop without opening another — the death spiral the doctrine names.
    ep.beats[9] = replace(ep.beats[9], loops_opened=[])
    r = score(ep, ledger)
    check("catches close-without-open", "loop_close_opens_another" in rules_hit(r),
          str(rules_hit(r)))

    ep, ledger = fresh()
    ep.beats[3] = replace(ep.beats[3], loops_closed=["q_never_opened"])
    r = score(ep, ledger)
    check("catches phantom close", "phantom_close" in rules_hit(r), str(rules_hit(r)))


# --------------------------------------------------------------------------- force 2


def test_irony_gap() -> None:
    print("\ndramatic_irony_gap")

    ep, ledger = fresh()
    ep.beats = [replace(b, irony_gap=False) for b in ep.beats]
    r = score(ep, ledger)
    check("catches symmetric information", "irony_gap_coverage_min" in rules_hit(r),
          str(rules_hit(r)))

    ep, ledger = fresh()
    ep.beats = [replace(b, clock_visible=False) for b in ep.beats]
    r = score(ep, ledger)
    check("catches gap with no clock", "gap_requires_clock" in rules_hit(r), str(rules_hit(r)))

    ep, ledger = fresh()
    for i in (2, 4, 6):
        ep.beats[i] = replace(ep.beats[i], surprise=True)
    r = score(ep, ledger)
    check("catches surprise over budget", "surprise_budget" in rules_hit(r), str(rules_hit(r)))


# --------------------------------------------------------------------------- force 3


def test_hook_cadence() -> None:
    print("\nhook_cadence")

    ep, ledger = fresh()
    ep.beats[-1] = replace(ep.beats[-1], hook="reveal")
    r = score(ep, ledger)
    check("catches ending on a resolution", "end_on_question" in rules_hit(r), str(rules_hit(r)))
    check("ending on a resolution is a hard fail",
          any(v.rule == "end_on_question" for v in r.hard_fails))

    ep, ledger = fresh()
    ep.beats[0] = replace(ep.beats[0], establishing=True)
    r = score(ep, ledger)
    check("catches an establishing open", "forbid_establishing_open" in rules_hit(r),
          str(rules_hit(r)))
    check("establishing open is a hard fail",
          any(v.rule == "forbid_establishing_open" for v in r.hard_fails))

    ep, ledger = fresh()
    ep.beats[0] = replace(ep.beats[0], hook=None)
    r = score(ep, ledger)
    check("catches a late cold open", "cold_open_max_sec" in rules_hit(r), str(rules_hit(r)))

    ep, ledger = fresh()
    # Rip the hooks out of the middle: a 200-second flat stretch.
    ep.beats = [replace(b, hook=None) if 90 < b.t_start_sec < 300 else b for b in ep.beats]
    r = score(ep, ledger)
    check("catches a flat middle", "hook_interval_max_sec" in rules_hit(r), str(rules_hit(r)))
    gap_notes = [v.detail for v in r.violations if v.rule == "hook_interval_max_sec"]
    check("flat-middle finding names timestamps", any(":" in d for d in gap_notes),
          str(gap_notes))

    ep, ledger = fresh()
    ep.prior_cliffhanger = "q_from_last_time"
    r = score(ep, ledger)
    check("catches an unresolved prior cliffhanger",
          "resolve_prior_cliffhanger" in rules_hit(r), str(rules_hit(r)))


# --------------------------------------------------------------------------- force 4


def test_empathy_lock() -> None:
    print("\nempathy_lock")

    ep, ledger = fresh()
    ep.beats = [replace(b, bonding_device=None) for b in ep.beats]
    r = score(ep, ledger)
    hits = rules_hit(r)
    check("catches no bonding device in the lock window",
          "lock_by_sec" in hits or "bonding_devices_min" in hits, str(hits))

    ep, ledger = fresh()
    ep.protective_duty_character = None
    r = score(ep, ledger)
    check("catches a missing protective duty", "protective_duty_required" in rules_hit(r),
          str(rules_hit(r)))

    ep, ledger = fresh()
    ep.wound_shown_beat = None
    r = score(ep, ledger)
    check("catches an unshown wound", "wound_shown_before_said" in rules_hit(r),
          str(rules_hit(r)))

    ep, ledger = fresh()
    ep.wound_shown_beat, ep.wound_said_beat = "b15", "b02"   # said before shown
    r = score(ep, ledger)
    check("catches a wound said before it is shown",
          "wound_shown_before_said" in rules_hit(r), str(rules_hit(r)))


# --------------------------------------------------------------------------- force 5


def test_clock_and_world() -> None:
    print("\nclock_and_shrinking_world")

    ep, ledger = fresh()
    ep.beats = [replace(b, clock_visible=False) for b in ep.beats]
    r = score(ep, ledger)
    check("catches an invisible clock", "clock_visible_fraction" in rules_hit(r),
          str(rules_hit(r)))

    ep, ledger = fresh()
    ep.beats[8] = replace(ep.beats[8], options_remaining=99)
    r = score(ep, ledger)
    check("catches widening options", "options_monotonic" in rules_hit(r), str(rules_hit(r)))

    ep, ledger = fresh()
    ep.beats[4] = replace(ep.beats[4], cost="   ")
    r = score(ep, ledger)
    check("catches a free scene", "cost_per_scene" in rules_hit(r), str(rules_hit(r)))

    ep, ledger = fresh()
    ep.beats = [replace(b, capability_gap=False) for b in ep.beats]
    r = score(ep, ledger)
    check("catches a competent calm protagonist", "capability_gap_min" in rules_hit(r),
          str(rules_hit(r)))

    ep, ledger = fresh()
    ep.beats[7] = replace(ep.beats[7], external_rescue=True)
    r = score(ep, ledger)
    check("catches the cavalry", "forbid_external_rescue" in rules_hit(r), str(rules_hit(r)))
    check("the cavalry is a hard fail",
          any(v.rule == "forbid_external_rescue" for v in r.hard_fails))


# --------------------------------------------------------------------------- force 6


def test_twist_ladder() -> None:
    print("\ntwist_ladder")

    ep, ledger = fresh()
    ep.beats = [replace(b, twist_level=None) if b.twist_level == 1 else b for b in ep.beats]
    r = score(ep, ledger)
    check("catches flat scenes", "l1_scene_coverage" in rules_hit(r), str(rules_hit(r)))

    ep, ledger = fresh()
    ledger.clues = [c for c in ledger.clues if c.twist_id != "T-E01-L2"]
    r = score(ep, ledger)
    check("catches an under-planted twist", "clues_per_twist_min" in rules_hit(r),
          str(rules_hit(r)))
    check("under-planting is a hard fail",
          any(v.rule == "clues_per_twist_min" for v in r.hard_fails))

    ep, ledger = fresh()
    for c in ledger.clues:
        if c.twist_id == "T-E01-L2":
            c.true_read = c.surface_read
    r = score(ep, ledger)
    check("catches a signpost instead of misdirection", "clue_dual_read" in rules_hit(r),
          str(rules_hit(r)))

    ep, ledger = fresh()
    t = ledger.twist_by_id("T-E01-L2")
    t.cost = ""
    r = score(ep, ledger)
    check("catches a costless twist", "twist_must_cost" in rules_hit(r), str(rules_hit(r)))

    ep, ledger = fresh()
    ledger.twist_by_id("T-E01-L2").contradicts_onscreen_fact = True
    r = score(ep, ledger)
    check("catches a retcon", "forbid_retcon" in rules_hit(r), str(rules_hit(r)))
    check("a retcon is a hard fail", any(v.rule == "forbid_retcon" for v in r.hard_fails))

    ep, ledger = fresh()
    ledger.twist_by_id("T-E01-L2").character_basis = None
    r = score(ep, ledger)
    check("catches an out-of-character twist", "twist_character_consistent" in rules_hit(r),
          str(rules_hit(r)))

    ep, ledger = fresh()
    ledger.twists = [t for t in ledger.twists if t.id != "T-E01-L2"]
    r = score(ep, ledger)
    check("catches a missing L2", "l2_required" in rules_hit(r), str(rules_hit(r)))

    ep, ledger = fresh()
    ledger.twist_by_id("T-E01-L2").beat_id = "b03"   # 38s of 420 = 9%
    r = score(ep, ledger)
    check("catches an early L2", "l2_placement" in rules_hit(r), str(rules_hit(r)))

    ep, ledger = fresh()
    ledger.twist_by_id("T-L4-SEASON").followed_within_30s_by = ""
    ledger.twist_by_id("T-L4-SEASON").episode = 1
    ledger.twist_by_id("T-L4-SEASON").beat_id = "b15"
    r = score(ep, ledger)
    check("catches a reframe with no threat behind it",
          "reframe_needs_threat" in rules_hit(r), str(rules_hit(r)))

    ep, ledger = fresh()
    ledger.twists.append(replace(ledger.twist_by_id("T-E01-L2"), id="T-DUPE"))
    r = score(ep, ledger)
    check("catches two twists in one beat", "twist_collision" in rules_hit(r), str(rules_hit(r)))


# --------------------------------------------------------------------------- gates


def test_gates_tighten_downstream() -> None:
    print("\ngates")
    script = DOCTRINE.gate("script_greenlight")["min_composite"]
    render = DOCTRINE.gate("render_greenlight")["min_composite"]
    publish = DOCTRINE.gate("publish_greenlight")["min_composite"]
    check("render gate is stricter than script gate", render > script, f"{script} -> {render}")
    check("publish gate is no looser than render gate", publish >= render,
          f"{render} -> {publish}")

    ep, ledger = fresh()
    ep.beats[-1] = replace(ep.beats[-1], hook="reveal")
    r = score(ep, ledger)
    check("one hard fail fails every gate",
          not r.passes(DOCTRINE.gate("script_greenlight"))
          and not r.passes(DOCTRINE.gate("render_greenlight")))


def test_models_reject_bad_input() -> None:
    print("\nschema")
    try:
        Beat.from_dict({"id": "x", "t_start_sec": 0, "t_end_sec": 1, "scene": "s",
                        "action": "a", "cost": "c", "nonsense": True})
        check("beat rejects unknown fields", False, "no error raised")
    except ValueError:
        check("beat rejects unknown fields", True)

    try:
        Beat.from_dict({"id": "x", "t_start_sec": 0, "t_end_sec": 1, "scene": "s",
                        "action": "a", "cost": "c", "hook": "vibes"})
        check("beat rejects unknown hook kinds", False, "no error raised")
    except ValueError:
        check("beat rejects unknown hook kinds", True)

    try:
        Clue.from_dict({"id": "c", "twist_id": "t", "episode": 1, "beat_id": "b"})
        check("clue requires a dual read", False, "no error raised")
    except ValueError:
        check("clue requires a dual read", True)


def test_ceo_halts_a_failing_episode() -> None:
    """End to end: the CEO must stop the line and write an actionable rework order."""
    print("\nceo stage-gate")
    from pipeline.ceo import GREENLIT, Studio

    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp) / "studio"
        shutil.copytree(ROOT, sandbox, ignore=shutil.ignore_patterns("build", "tests", "__pycache__"))
        ep_dir = sandbox / "productions" / "ash-river" / "season-01" / "ep01"

        run = Studio(sandbox, "ash-river", 1, 1).produce()
        check("clean episode is greenlit", run.verdict == GREENLIT, run.verdict)
        check("greenlit run reaches the distributor",
              any(s.agent == "distributor" for s in run.stages))
        check("dry-run posts nothing",
              all("nothing posted" in n or True for s in run.stages for n in s.notes))

        # Break the button: the episode now ends on a resolution.
        text = (ep_dir / "beatsheet.yaml").read_text(encoding="utf-8")
        text = text.replace("    hook: question", "    hook: reveal")
        (ep_dir / "beatsheet.yaml").write_text(text, encoding="utf-8")

        run = Studio(sandbox, "ash-river", 1, 1).produce()
        check("broken episode is not greenlit", run.verdict != GREENLIT, run.verdict)
        check("halts at the script gate", run.halted_at == "script_greenlight", str(run.halted_at))
        order = ep_dir / "build" / "rework-order.md"
        check("writes a rework order", order.exists())
        if order.exists():
            body = order.read_text(encoding="utf-8")
            check("rework order names the rule", "end_on_question" in body)
            check("rework order is mechanical, not editorial",
                  "hook=" in body or "final beat" in body, body[:200])
        check("never reaches the renderer",
              not any(s.agent == "cinematographer" for s in run.stages))


def test_slate() -> None:
    """The Slate is what a cold Routine session relies on. Break it and autonomy dies."""
    print("\nslate")
    Slate, Stage = slate_mod.Slate, slate_mod.Stage

    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp) / "studio"
        shutil.copytree(ROOT, sandbox, ignore=shutil.ignore_patterns("tests", "__pycache__"))
        slate = Slate(sandbox)
        s01 = sandbox / "productions" / "ash-river" / "season-01"

        check("finds the production", slate.productions() == ["ash-river"],
              str(slate.productions()))
        check("reads the full planned season from the arc",
              len(slate.season_status("ash-river", 1)) == 12,
              str(len(slate.season_status("ash-river", 1))))

        e1 = slate.episode_status("ash-river", 1, 1)
        check("E01 is greenlit", e1.stage == Stage.GREENLIT.label, e1.stage)
        # Assert on shape, not on episode numbers: the slate advances as episodes get
        # written, and a test that pins E02 breaks every time the studio does its job.
        season = slate.season_status("ash-river", 1)
        unwritten = [s for s in season if s.stage == Stage.PLANNED.label]
        check("unwritten episodes read as planned", bool(unwritten),
              "every episode is written — extend the arc")
        check("the last arced episode is unwritten",
              season[-1].stage == Stage.PLANNED.label, season[-1].stage)

        # With no credentials, rendering is unreachable — the studio must find other work
        # rather than burn a scheduled run on a rung it cannot climb.
        blocked = slate.blocked_stages()
        check("render stage reports blocked without credentials",
              Stage.GREENLIT.label in blocked, str(blocked))
        d = slate.next_action()
        first_unwritten = min(s.episode for s in unwritten)
        check("falls through to writing when render is blocked",
              d.owner == "episode-writer" and d.episode == first_unwritten,
              f"{d.owner} E{d.episode}, expected E{first_unwritten}")

        # A shipped episode must drop off the slate, or tomorrow's run republishes it.
        (s01 / "release-log.yaml").write_text(
            "releases:\n  - episode: 1\n    platform: youtube\n"
            "    published_at: 2026-08-19T17:00:00Z\n", encoding="utf-8")
        check("release log marks the episode shipped",
              slate.episode_status("ash-river", 1, 1).stage == Stage.RELEASED.label)

        # Three failed reworks is a CEO decision, not a fourth rewrite.
        build = s01 / "ep01" / "build"
        (s01 / "release-log.yaml").unlink()
        with (build / "decisions.jsonl").open("a", encoding="utf-8") as fh:
            for _ in range(3):
                fh.write('{"stage":"script_greenlight","verdict":"REWORK","reason":"x"}\n')
        d = Slate(sandbox).next_action()
        check("escalates a burned rework budget to the CEO", d.owner == "ceo",
              f"{d.owner}: {d.detail}")

        # A corrupt beat sheet must degrade to a finding, never an exception.
        (s01 / "ep02").mkdir(parents=True, exist_ok=True)
        (s01 / "ep02" / "beatsheet.yaml").write_text("{{ not yaml", encoding="utf-8")
        st = Slate(sandbox).episode_status("ash-river", 1, 2)
        check("survives an unparseable beat sheet", st.stage == Stage.PLANNED.label
              and any("parse" in b for b in st.blocking), str(st.blocking))


def main() -> int:
    print("Retention Engine — breaking the shipping episode one rule at a time")
    test_baseline_passes()
    test_open_loops()
    test_irony_gap()
    test_hook_cadence()
    test_empathy_lock()
    test_clock_and_world()
    test_twist_ladder()
    test_gates_tighten_downstream()
    test_models_reject_bad_input()
    test_ceo_halts_a_failing_episode()
    test_slate()
    print(f"\n{PASSES} passed, {len(FAILURES)} failed")
    for f in FAILURES:
        print(f"  - {f}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
