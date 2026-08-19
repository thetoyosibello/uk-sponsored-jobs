"""The Retention Engine.

This is the gate every piece of material passes through before the studio spends a
cent rendering it. It reads a beat sheet and grades it against the six attention forces
in doctrine/attention_physics.yaml, returning a composite score plus the exact list of
violations — so a rework instruction is specific ("no hook between 03:12 and 04:40")
rather than a note ("the middle sags").

The design bet: rejecting a script is cheap, rejecting a render is expensive, and
publishing something skippable is the most expensive of all, because it teaches the
distribution algorithm that our work can be skipped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Doctrine, Episode, TwistLedger

# How much a single violation of each rule costs its force's 0-100 score.
PENALTY = {
    # open_loop_pressure
    "open_loops_min": 30,
    "open_loops_max": 20,
    "loop_close_opens_another": 12,
    "phantom_close": 18,
    "loop_never_closed": 8,
    # dramatic_irony_gap
    "irony_gap_coverage_min": 45,
    "gap_requires_clock": 15,
    "surprise_budget": 20,
    # hook_cadence
    "cold_open_max_sec": 35,
    "hook_interval_max_sec": 18,
    "resolve_prior_cliffhanger": 30,
    "button_within_last_sec": 25,
    "end_on_question": 40,
    "forbid_establishing_open": 40,
    # empathy_lock
    "lock_by_sec": 30,
    "bonding_devices_min": 25,
    "protective_duty_required": 20,
    "wound_shown_before_said": 25,
    # clock_and_shrinking_world
    "clock_visible_fraction": 35,
    "options_monotonic": 15,
    "cost_per_scene": 12,
    "capability_gap_min": 20,
    "forbid_external_rescue": 50,
    # twist_ladder
    "l1_scene_coverage": 25,
    "clues_per_twist_min": 30,
    "clue_dual_read": 15,
    "clue_spread": 12,
    "twist_must_cost": 20,
    "twist_character_consistent": 15,
    "forbid_retcon": 50,
    "twist_collision": 15,
    "l2_required": 30,
    "l2_placement": 12,
    "reframe_needs_threat": 20,
}

FORCE_ORDER = [
    "open_loop_pressure",
    "dramatic_irony_gap",
    "hook_cadence",
    "empathy_lock",
    "clock_and_shrinking_world",
    "twist_ladder",
]


def _ts(seconds: float) -> str:
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


@dataclass
class Violation:
    rule: str
    force: str
    detail: str
    hard: bool = False

    def __str__(self) -> str:
        mark = "HARD" if self.hard else "soft"
        return f"[{mark}] {self.force}.{self.rule}: {self.detail}"


@dataclass
class ForceScore:
    force: str
    score: float
    weight: float
    violations: list[Violation] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def weighted(self) -> float:
        return self.score * self.weight / 100.0


@dataclass
class RetentionReport:
    production: str
    season: int
    episode: int
    forces: list[ForceScore]
    composite: float
    hard_fails: list[Violation]

    @property
    def violations(self) -> list[Violation]:
        return [v for f in self.forces for v in f.violations]

    def passes(self, gate: dict[str, Any]) -> bool:
        if self.composite < float(gate.get("min_composite", 0)):
            return False
        return len(self.hard_fails) <= int(gate.get("hard_fails_allowed", 0))

    def render(self) -> str:
        lines = [
            f"RETENTION REPORT  {self.production} S{self.season:02d}E{self.episode:02d}",
            f"composite {self.composite:.1f}/100   hard fails: {len(self.hard_fails)}",
            "",
        ]
        for f in self.forces:
            bar = "#" * int(round(f.score / 5)) + "." * (20 - int(round(f.score / 5)))
            lines.append(f"  {f.force:<28} {f.score:5.1f}  w{f.weight:>3.0f}  [{bar}]")
            for k, v in f.metrics.items():
                lines.append(f"      {k}: {v}")
            for v in f.violations:
                lines.append(f"      {v}")
        return "\n".join(lines)


class RetentionEngine:
    """Grades an episode against the doctrine. Stateless; safe to reuse."""

    def __init__(self, doctrine: Doctrine) -> None:
        self.d = doctrine
        self._hard_rules = doctrine.hard_fail_rules

    # -- public ---------------------------------------------------------------

    def score(self, ep: Episode, ledger: TwistLedger | None = None) -> RetentionReport:
        ledger = ledger or TwistLedger.empty()
        forces = [
            self._open_loop_pressure(ep),
            self._dramatic_irony_gap(ep),
            self._hook_cadence(ep),
            self._empathy_lock(ep),
            self._clock_and_shrinking_world(ep),
            self._twist_ladder(ep, ledger),
        ]
        composite = sum(f.weighted for f in forces)
        hard = [v for f in forces for v in f.violations if v.hard]
        return RetentionReport(
            production=ep.production,
            season=ep.season,
            episode=ep.episode,
            forces=forces,
            composite=round(composite, 1),
            hard_fails=hard,
        )

    # -- helpers --------------------------------------------------------------

    def _mk(self, force: str, viols: list[Violation], metrics: dict[str, Any]) -> ForceScore:
        penalty = sum(PENALTY.get(v.rule, 10) for v in viols)
        return ForceScore(
            force=force,
            score=max(0.0, 100.0 - penalty),
            weight=self.d.weight(force),
            violations=viols,
            metrics=metrics,
        )

    def _v(self, force: str, rule: str, detail: str) -> Violation:
        # A rule is hard if the doctrine's hard_fail_rules list names it. The list uses
        # the doctrine's own rule keys, so accept either the doctrine key or ours.
        hard = rule in self._hard_rules or f"forbid_{rule}" in self._hard_rules
        return Violation(rule=rule, force=force, detail=detail, hard=hard)

    # -- force 1: open loop pressure ------------------------------------------

    def _open_loop_pressure(self, ep: Episode) -> ForceScore:
        force = "open_loop_pressure"
        r = self.d.rules(force)
        viols: list[Violation] = []
        live: set[str] = set()
        # Loops carried in from earlier episodes are not visible here; the season-level
        # ledger check in ceo.py owns that. Within an episode we grade the local curve.
        if ep.prior_cliffhanger:
            live.add(ep.prior_cliffhanger)
        counts: list[int] = []
        grace_sec = 45.0  # you cannot have three questions live at second five

        for b in ep.beats:
            for q in b.loops_closed:
                if q not in live:
                    viols.append(self._v(force, "phantom_close",
                                         f"{b.id} @{_ts(b.t_start_sec)} closes {q!r}, never opened"))
                live.discard(q)
            if b.loops_closed and not b.loops_opened:
                viols.append(self._v(force, "loop_close_opens_another",
                                     f"{b.id} @{_ts(b.t_start_sec)} closes "
                                     f"{b.loops_closed} without opening anything"))
            live.update(b.loops_opened)
            counts.append(len(live))
            if b.t_end_sec >= grace_sec and len(live) < int(r["open_loops_min"]):
                viols.append(self._v(force, "open_loops_min",
                                     f"{b.id} @{_ts(b.t_start_sec)} leaves only "
                                     f"{len(live)} loops live (min {r['open_loops_min']})"))
            if len(live) > int(r["open_loops_max"]):
                viols.append(self._v(force, "open_loops_max",
                                     f"{b.id} @{_ts(b.t_start_sec)} has {len(live)} loops live "
                                     f"(max {r['open_loops_max']}) — audience stops tracking"))

        return self._mk(force, viols, {
            "loop_curve": counts,
            "live_at_end": sorted(live),
            "min_live": min(counts) if counts else 0,
            "max_live": max(counts) if counts else 0,
        })

    # -- force 2: dramatic irony gap -------------------------------------------

    def _dramatic_irony_gap(self, ep: Episode) -> ForceScore:
        force = "dramatic_irony_gap"
        r = self.d.rules(force)
        viols: list[Violation] = []
        runtime = ep.runtime or 1.0

        gap_time = sum(b.duration for b in ep.beats if b.irony_gap)
        coverage = gap_time / runtime
        if coverage < float(r["irony_gap_coverage_min"]):
            viols.append(self._v(force, "irony_gap_coverage_min",
                                 f"audience-ahead for {coverage:.0%} of runtime, "
                                 f"need {float(r['irony_gap_coverage_min']):.0%} — "
                                 f"symmetric information collapses suspense into surprise"))

        if r.get("gap_requires_clock"):
            gap_beats = [b for b in ep.beats if b.irony_gap]
            clockless = [b for b in gap_beats if not b.clock_visible]
            # A gap without time pressure is exposition. Tolerate a fifth of them.
            if gap_beats and len(clockless) / len(gap_beats) > 0.20:
                viols.append(self._v(force, "gap_requires_clock",
                                     f"{len(clockless)}/{len(gap_beats)} irony-gap beats carry no "
                                     f"visible clock: {[b.id for b in clockless]}"))

        surprises = [b for b in ep.beats if b.surprise]
        budget = int(r["surprise_budget_per_episode"])
        if len(surprises) > budget:
            viols.append(self._v(force, "surprise_budget",
                                 f"{len(surprises)} pure-surprise beats, budget is {budget} "
                                 f"({[b.id for b in surprises]})"))

        return self._mk(force, viols, {
            "irony_coverage": f"{coverage:.0%}",
            "gap_seconds": round(gap_time),
            "surprise_beats": len(surprises),
        })

    # -- force 3: hook cadence -------------------------------------------------

    def _hook_cadence(self, ep: Episode) -> ForceScore:
        force = "hook_cadence"
        r = self.d.rules(force)
        viols: list[Violation] = []
        runtime = ep.runtime

        if not ep.beats:
            return self._mk(force, [self._v(force, "end_on_question", "no beats")], {})

        first = ep.beats[0]
        if r.get("forbid_establishing_open") and first.establishing:
            viols.append(self._v(force, "forbid_establishing_open",
                                 f"{first.id} opens on establishing material — "
                                 f"context is delivered mid-crisis or not at all"))

        hooks = [b for b in ep.beats if b.hook]
        cold = float(r["cold_open_max_sec"])
        if not hooks or hooks[0].t_start_sec > cold:
            at = _ts(hooks[0].t_start_sec) if hooks else "never"
            viols.append(self._v(force, "cold_open_max_sec",
                                 f"first hook at {at}, must land by {cold:.0f}s"))

        # Gaps: start -> first hook, hook -> hook, last hook -> end of episode.
        max_gap = float(r["hook_interval_max_sec"])
        marks = [0.0] + [b.t_start_sec for b in hooks] + [runtime]
        for a, b in zip(marks, marks[1:]):
            if b - a > max_gap:
                viols.append(self._v(force, "hook_interval_max_sec",
                                     f"{b - a:.0f}s with no hook between "
                                     f"{_ts(a)} and {_ts(b)} (max {max_gap:.0f}s)"))

        if ep.prior_cliffhanger:
            by = float(r["resolve_prior_cliffhanger_by_sec"])
            resolved = [b for b in ep.beats
                        if ep.prior_cliffhanger in b.loops_closed and b.t_end_sec <= by]
            if not resolved:
                viols.append(self._v(force, "resolve_prior_cliffhanger",
                                     f"prior cliffhanger {ep.prior_cliffhanger!r} not resolved "
                                     f"in first {by:.0f}s"))

        last = ep.beats[-1]
        if r.get("end_on_question") and last.hook != "question":
            viols.append(self._v(force, "end_on_question",
                                 f"final beat {last.id} is hook={last.hook!r} — "
                                 f"must end on a question, not a resolution"))

        window = float(r["button_within_last_sec"])
        if hooks:
            landing = hooks[-1].t_end_sec
            if runtime - landing > window:
                viols.append(self._v(force, "button_within_last_sec",
                                     f"final hook lands at {_ts(landing)}, "
                                     f"{runtime - landing:.0f}s before the end "
                                     f"(must be within {window:.0f}s)"))

        gaps = [b - a for a, b in zip(marks, marks[1:])]
        return self._mk(force, viols, {
            "hooks": len(hooks),
            "largest_gap_sec": round(max(gaps)) if gaps else 0,
            "mean_gap_sec": round(sum(gaps) / len(gaps)) if gaps else 0,
            "ends_on": last.hook,
        })

    # -- force 4: empathy lock -------------------------------------------------

    def _empathy_lock(self, ep: Episode) -> ForceScore:
        force = "empathy_lock"
        r = self.d.rules(force)
        viols: list[Violation] = []
        by = float(r["lock_by_sec"])

        early = [b for b in ep.beats if b.t_start_sec <= by and b.bonding_device]
        devices = {b.bonding_device for b in early}
        allowed = set(r.get("bonding_devices", []))
        unknown = devices - allowed
        if unknown:
            viols.append(self._v(force, "bonding_devices_min",
                                 f"unrecognised bonding devices {sorted(unknown)}"))
        if not early:
            viols.append(self._v(force, "lock_by_sec",
                                 f"no bonding device inside the first {by:.0f}s — "
                                 f"the clock is ticking over a stranger"))
        if len(devices & allowed) < int(r["bonding_devices_min"]):
            viols.append(self._v(force, "bonding_devices_min",
                                 f"{len(devices & allowed)} bonding device(s) in the first "
                                 f"{by:.0f}s, need {r['bonding_devices_min']}"))

        if r.get("protective_duty_required") and not ep.protective_duty_character:
            viols.append(self._v(force, "protective_duty_required",
                                 "no character who cannot save themselves"))

        # Series-level rule: the wound is behaviour before it is dialogue. Only the
        # opening episode can establish it, so only the opening episode is graded on it.
        if r.get("wound_shown_before_said") and ep.episode == 1:
            shown, said = ep.wound_shown_beat, ep.wound_said_beat
            if not shown:
                viols.append(self._v(force, "wound_shown_before_said",
                                     "protagonist's private wound is never shown as behaviour"))
            elif said:
                bs, bd = ep.beat(shown), ep.beat(said)
                if bs and bd and bs.t_start_sec >= bd.t_start_sec:
                    viols.append(self._v(force, "wound_shown_before_said",
                                         f"wound stated ({said}) before it is shown ({shown})"))

        return self._mk(force, viols, {
            "devices_in_lock_window": sorted(devices),
            "protective_duty": ep.protective_duty_character or "-",
        })

    # -- force 5: clock and shrinking world ------------------------------------

    def _clock_and_shrinking_world(self, ep: Episode) -> ForceScore:
        force = "clock_and_shrinking_world"
        r = self.d.rules(force)
        viols: list[Violation] = []
        runtime = ep.runtime or 1.0

        clock_time = sum(b.duration for b in ep.beats if b.clock_visible)
        frac = clock_time / runtime
        if frac < float(r["clock_visible_beat_fraction_min"]):
            viols.append(self._v(force, "clock_visible_fraction",
                                 f"depleting quantity legible in {frac:.0%} of runtime, "
                                 f"need {float(r['clock_visible_beat_fraction_min']):.0%}"))

        if r.get("options_monotonic_non_increasing"):
            for a, b in zip(ep.beats, ep.beats[1:]):
                if b.options_remaining > a.options_remaining:
                    viols.append(self._v(force, "options_monotonic",
                                         f"{b.id} @{_ts(b.t_start_sec)} widens options "
                                         f"{a.options_remaining} -> {b.options_remaining}; "
                                         f"a new option must cost two"))

        if r.get("cost_per_scene_required"):
            for b in ep.beats:
                if not (b.cost or "").strip():
                    viols.append(self._v(force, "cost_per_scene",
                                         f"{b.id} @{_ts(b.t_start_sec)} is a free scene"))

        gaps = [b for b in ep.beats if b.capability_gap]
        if len(gaps) < int(r["capability_gap_beats_min"]):
            viols.append(self._v(force, "capability_gap_min",
                                 "no beat where the protagonist knows the right move and "
                                 "cannot perform it — that gap is the characterisation"))

        if r.get("forbid_external_rescue"):
            for b in ep.beats:
                if b.external_rescue:
                    viols.append(self._v(force, "forbid_external_rescue",
                                         f"{b.id} @{_ts(b.t_start_sec)} resolved by outside "
                                         f"rescue; rescue may only arrive as a new problem"))

        return self._mk(force, viols, {
            "clock_coverage": f"{frac:.0%}",
            "options_curve": [b.options_remaining for b in ep.beats],
            "capability_gap_beats": [b.id for b in gaps],
        })

    # -- force 6: twist ladder -------------------------------------------------

    def _twist_ladder(self, ep: Episode, ledger: TwistLedger) -> ForceScore:
        force = "twist_ladder"
        r = self.d.rules(force)
        levels = self.d.twist_ladder["levels"]
        viols: list[Violation] = []

        # L1: every scene must resolve other than as it was set up.
        scenes = ep.scenes()
        twisted = {name for name, beats in scenes.items()
                   if any(b.twist_level for b in beats)}
        coverage = len(twisted) / len(scenes) if scenes else 0.0
        if coverage < float(r["l1_scene_coverage"]):
            missing = sorted(set(scenes) - twisted)
            viols.append(self._v(force, "l1_scene_coverage",
                                 f"{coverage:.0%} scene twist coverage; flat scenes: {missing}"))

        # Two twists in one beat: the audience can only re-read one thing at a time.
        by_beat: dict[str, list[str]] = {}
        episode_twists = [t for t in ledger.twists if t.episode == ep.episode]
        for t in episode_twists:
            by_beat.setdefault(t.beat_id, []).append(t.id)
        for beat_id, ids in by_beat.items():
            if len(ids) > 1:
                viols.append(self._v(force, "twist_collision",
                                     f"{beat_id} fires {ids} together"))

        # The episode owes an L2, placed late enough to reframe but before the button.
        l2 = [t for t in episode_twists if t.level == 2]
        if not l2:
            viols.append(self._v(force, "l2_required",
                                 "no L2 twist — the episode goal was never revealed as wrong"))
        for t in l2:
            b = ep.beat(t.beat_id)
            if b and ep.runtime:
                pos = b.t_start_sec / ep.runtime
                if not 0.60 <= pos <= 0.95:
                    viols.append(self._v(force, "l2_placement",
                                         f"{t.id} fires at {pos:.0%} of runtime; "
                                         f"L2 belongs at 60-95%"))

        # Fair play, per twist firing in this episode.
        for t in episode_twists:
            spec = levels.get(f"L{t.level}", {})
            need = int(spec.get("clues_required", 1))
            fired_at = ep.beat(t.beat_id)
            clues = ledger.clues_for(t.id)
            prior = [c for c in clues if self._clue_is_before(c, t, ep, fired_at)]
            if len(prior) < need:
                viols.append(self._v(force, "clues_per_twist_min",
                                     f"{t.id} (L{t.level}) has {len(prior)} planted clues "
                                     f"before it fires, needs {need} — under-planted twists "
                                     f"read as cheating"))
            for c in prior:
                if not c.surface_read.strip() or not c.true_read.strip():
                    viols.append(self._v(force, "clue_dual_read",
                                         f"{c.id} missing a dual read"))
                elif c.surface_read.strip() == c.true_read.strip():
                    viols.append(self._v(force, "clue_dual_read",
                                         f"{c.id} surface and true read are identical — "
                                         f"that is a signpost, not misdirection"))
            spread = int(spec.get("clue_spread_min_episodes", 1))
            if len({c.episode for c in prior}) < spread and len(prior) >= need:
                viols.append(self._v(force, "clue_spread",
                                     f"{t.id} clues sit in "
                                     f"{len({c.episode for c in prior})} episode(s), "
                                     f"need {spread}"))
            if r.get("twist_must_cost") and not (t.cost or "").strip():
                viols.append(self._v(force, "twist_must_cost",
                                     f"{t.id} costs the protagonist nothing — "
                                     f"that is a plot device wearing a twist costume"))
            if r.get("twist_character_consistent") and t.character and not t.character_basis:
                viols.append(self._v(force, "twist_character_consistent",
                                     f"{t.id} executed by {t.character} with no established "
                                     f"desire or fear behind it"))
            if t.level >= 4 and not (t.followed_within_30s_by or "").strip():
                viols.append(self._v(force, "reframe_needs_threat",
                                     f"{t.id} (L{t.level}) names no concrete threat landing "
                                     f"within 30s; a reframe left to breathe deflates "
                                     f"into exposition"))
            if r.get("forbid_retcon") and t.contradicts_onscreen_fact:
                viols.append(self._v(force, "forbid_retcon",
                                     f"{t.id} contradicts an on-screen fact; a twist may only "
                                     f"contradict the audience's interpretation"))

        return self._mk(force, viols, {
            "scene_twist_coverage": f"{coverage:.0%}",
            "twists_this_episode": [f"{t.id}(L{t.level})" for t in episode_twists],
            "clues_planted_here": len([c for c in ledger.clues if c.episode == ep.episode]),
        })

    @staticmethod
    def _clue_is_before(clue, twist, ep: Episode, fired_at) -> bool:
        """A clue counts only if the audience has already seen it when the twist fires."""
        if clue.episode < twist.episode:
            return True
        if clue.episode > twist.episode:
            return False
        cb, tb = ep.beat(clue.beat_id), fired_at
        if cb is None or tb is None:
            return False
        return cb.t_start_sec < tb.t_start_sec
