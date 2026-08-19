"""The agent roster, as executable stages.

Each class here is the machine half of a role card in `agents/`. The card carries the
craft doctrine a human or an LLM needs to *do* the job; the class carries the checks and
the artefact production that make the job auditable — so the CEO's verdict rests on
something other than an assurance that the work was done.

Every agent is a pure function of the production directory: it reads artefacts, emits
artefacts, and returns a StageResult. No agent decides whether the show goes on; that is
the CEO's job in `ceo.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .models import Doctrine, Episode, TwistLedger
from .retention import RetentionEngine, RetentionReport

OK, WARN, BLOCK = "ok", "warn", "block"


@dataclass
class StageResult:
    agent: str
    status: str = OK
    notes: list[str] = field(default_factory=list)
    artefacts: list[Path] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def block(self, note: str) -> StageResult:
        self.status = BLOCK
        self.notes.append(note)
        return self

    def warn(self, note: str) -> StageResult:
        if self.status != BLOCK:
            self.status = WARN
        self.notes.append(note)
        return self

    def note(self, text: str) -> StageResult:
        self.notes.append(text)
        return self


@dataclass
class Context:
    """Everything an agent is allowed to see."""

    studio_root: Path
    production_dir: Path
    season_dir: Path
    episode_dir: Path
    doctrine: Doctrine
    episode: Episode
    ledger: TwistLedger
    dry_run: bool = True
    report: RetentionReport | None = None

    @property
    def build(self) -> Path:
        out = self.episode_dir / "build"
        out.mkdir(parents=True, exist_ok=True)
        return out

    def write_json(self, name: str, payload: Any) -> Path:
        path = self.build / name
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def load_yaml(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)


class Agent:
    name = "agent"
    stage = -1

    def run(self, ctx: Context) -> StageResult:  # pragma: no cover - interface
        raise NotImplementedError


# --------------------------------------------------------------------------- development


class MarketScout(Agent):
    name, stage = "market-scout", 1

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        brief = ctx.load_yaml(ctx.production_dir / "demand_brief.yaml")
        if brief is None:
            r.note("no demand_brief.yaml — advisory stage, proceeding on doctrine defaults")
            return r
        if "recommended_format" not in brief:
            r.warn("demand brief names no recommended format")
        r.data["brief"] = brief
        return r.note(f"format: {brief.get('recommended_format', 'unspecified')}")


class ConceptArchitect(Agent):
    name, stage = "concept-architect", 2

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        bible = ctx.production_dir / "bible.md"
        if not bible.exists():
            return r.block("no bible.md — nothing to produce")
        text = bible.read_text(encoding="utf-8").lower()
        # The premise test is the concept gate. 5 of 6 to pass; the last two decide
        # whether the series has a spine at all, so they are individually required.
        tests = {t["id"]: t["q"] for t in ctx.doctrine.genre["premise_test"]}
        answered = {t for t in tests if t.replace("_", " ") in text or t in text}
        r.data["premise_test"] = sorted(answered)
        if len(answered) < 5:
            return r.block(
                f"premise test {len(answered)}/6 — missing {sorted(set(tests) - answered)}")
        for required in ("engineerable", "protagonist_complicity"):
            if required not in answered:
                return r.block(
                    f"bible does not answer '{required}': the premise cannot support the "
                    f"top of the twist ladder, and that defect is unfixable later")
        return r.note(f"premise test {len(answered)}/6")


class StoryArchitect(Agent):
    name, stage = "story-architect", 3

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        arc = ctx.season_dir / "arc.md"
        if not arc.exists():
            return r.block("no arc.md — the season has no shape")
        spec = ctx.doctrine.episode_spec["season"]
        text = arc.read_text(encoding="utf-8")
        for ep in range(1, int(spec["episodes"]) + 1):
            if f"E{ep:02d}" not in text:
                r.warn(f"arc.md does not cover E{ep:02d}")
        return r.note(f"{spec['episodes']}-episode arc present")


class TwistMaster(Agent):
    name, stage = "twist-master", 4

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        if not ctx.ledger.twists:
            return r.block("empty twist ledger")
        spec = ctx.doctrine.episode_spec["season"]
        levels = {t.level for t in ctx.ledger.twists}

        for lvl, want_ep in ((4, spec["l4_season_twist_episode"]),
                             (5, spec["l5_series_twist_episode"])):
            fired = [t for t in ctx.ledger.twists if t.level == lvl]
            if not fired:
                r.block(f"no L{lvl} twist committed — it must be decided before E01 is written")
            elif len(fired) > 1:
                r.block(f"{len(fired)} L{lvl} twists; this level fires once per series")
            elif fired[0].episode != want_ep:
                r.warn(f"L{lvl} sits at E{fired[0].episode:02d}, doctrine places it at "
                       f"E{want_ep:02d}")

        cadence = int(spec["arc_twist_cadence"])
        want_l3 = list(range(cadence, int(spec["episodes"]) + 1, cadence))
        have_l3 = sorted(t.episode for t in ctx.ledger.twists if t.level == 3)
        if have_l3 != want_l3:
            r.warn(f"L3 cadence is {have_l3}, doctrine expects {want_l3}")

        for ep in range(1, int(spec["episodes"]) + 1):
            if not any(t.level == 2 and t.episode == ep for t in ctx.ledger.twists):
                r.warn(f"E{ep:02d} has no L2 twist")

        # A lower twist must never pre-empt a higher one.
        for t in ctx.ledger.twists:
            if t.level in (4, 5):
                continue
            for high in (x for x in ctx.ledger.twists if x.level in (4, 5)):
                if t.episode > high.episode and t.reframes == high.reframes:
                    r.block(f"{t.id} reframes the same thing as {high.id} after the fact")

        r.data["levels_present"] = sorted(levels)
        r.data["twists"] = len(ctx.ledger.twists)
        r.data["clues"] = len(ctx.ledger.clues)
        return r.note(f"{len(ctx.ledger.twists)} twists, {len(ctx.ledger.clues)} clues, "
                      f"levels {sorted(levels)}")


class EpisodeWriter(Agent):
    name, stage = "episode-writer", 6

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        script = ctx.episode_dir / "script.md"
        if not script.exists():
            return r.block("no script.md")
        lo, hi = ctx.doctrine.episode_spec["beat_grid"]["target_beats_per_episode"]
        n = len(ctx.episode.beats)
        if not lo <= n <= hi:
            r.warn(f"{n} beats, grid wants {lo}-{hi}")
        target = ctx.episode.runtime_target_sec
        tol = float(ctx.doctrine.episode_spec["formats"]["serial_episode"]["runtime_tolerance_sec"])
        if abs(ctx.episode.runtime - target) > tol:
            r.block(f"runtime {ctx.episode.runtime:.0f}s vs target {target:.0f}s (±{tol:.0f}s)")
        # Beats must tile the runtime: a gap is unaccounted screen time nobody graded.
        for a, b in zip(ctx.episode.beats, ctx.episode.beats[1:]):
            if abs(b.t_start_sec - a.t_end_sec) > 0.01:
                r.block(f"beat gap/overlap between {a.id} and {b.id} "
                        f"({a.t_end_sec}s -> {b.t_start_sec}s)")
        r.data["beats"] = n
        r.data["runtime_sec"] = ctx.episode.runtime
        return r.note(f"{n} beats over {ctx.episode.runtime:.0f}s")


class RetentionEngineer(Agent):
    name, stage = "retention-engineer", 5

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        report = RetentionEngine(ctx.doctrine).score(ctx.episode, ctx.ledger)
        ctx.report = report
        path = ctx.build / "retention-report.txt"
        path.write_text(report.render() + "\n", encoding="utf-8")
        r.artefacts.append(path)
        r.artefacts.append(ctx.write_json("retention-report.json", {
            "composite": report.composite,
            "hard_fails": [str(v) for v in report.hard_fails],
            "forces": [{"force": f.force, "score": f.score, "weight": f.weight,
                        "metrics": f.metrics,
                        "violations": [str(v) for v in f.violations]} for f in report.forces],
        }))
        r.data["composite"] = report.composite
        r.data["hard_fails"] = len(report.hard_fails)
        # This stage reports; it never blocks. The verdict belongs to the gate that
        # follows it, so failures are recorded against the gate and the CEO's
        # three-strikes kill rule can actually count them.
        for v in report.violations:
            r.warn(str(v))
        return r.note(f"composite {report.composite:.1f}/100")


class ContinuityAuditor(Agent):
    name, stage = "continuity-auditor", 7

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        ep = ctx.episode

        # 1. Fair play is only real if the clue reached a frame. Check the shot list,
        #    not the plan — a clue that was never shot does not exist.
        shots = ctx.load_yaml(ctx.episode_dir / "shotlist.yaml") or {}
        shot_clues = {s.get("clue_id") for s in shots.get("shots", []) if s.get("clue_id")}
        planned = {c.id for c in ctx.ledger.clues if c.episode == ep.episode}
        if shots:
            unshot = planned - shot_clues
            if unshot:
                r.block(f"clues planned but never framed: {sorted(unshot)}")
        else:
            r.warn("no shotlist.yaml yet — clue framing unverified")

        # 2. Every clue must point at a beat that exists, and precede its twist.
        for c in (c for c in ctx.ledger.clues if c.episode == ep.episode):
            if ep.beat(c.beat_id) is None:
                r.block(f"clue {c.id} references unknown beat {c.beat_id}")
            if ctx.ledger.twist_by_id(c.twist_id) is None:
                r.block(f"clue {c.id} points at unknown twist {c.twist_id}")

        # 3. Loop debt. A question left hanging past the ceiling is the failure that
        #    costs the *next* production, not just this one.
        ceiling = int(ctx.doctrine.rules("open_loop_pressure")["loop_debt_ceiling_episodes"])
        ledger_path = ctx.season_dir / "loop-ledger.yaml"
        loops = (ctx.load_yaml(ledger_path) or {}).get("loops", [])
        for loop in loops:
            opened, paid = int(loop.get("opened_ep", 0)), loop.get("partial_payoff_ep")
            if paid is None and ep.episode - opened > ceiling:
                r.block(f"loop {loop.get('id')} open since E{opened:02d} with no partial "
                        f"payoff ({ceiling}-episode ceiling)")

        # 4. The timeline must be monotonic and tile the runtime.
        for a, b in zip(ep.beats, ep.beats[1:]):
            if b.t_start_sec < a.t_start_sec:
                r.block(f"beats out of order: {a.id} then {b.id}")

        # 5. The situation may not re-expand between episodes.
        #
        #    `options_remaining` is a WITHIN-episode tension curve: it counts the courses
        #    of action open to the protagonist in this episode's situation, and it resets
        #    each episode because each episode poses a new immediate problem. Comparing a
        #    new episode's opening against the previous episode's *closing* would force
        #    the count to zero by mid-season and make the field useless.
        #
        #    So the cross-episode rule is opening-to-opening: episode N may never start
        #    with more options than episode N-1 started with. The season-long shrink is
        #    tracked separately and physically, as the boundary mileage in arc.md.
        prev = ctx.season_dir / f"ep{ep.episode - 1:02d}" / "beatsheet.yaml"
        if ep.episode > 1 and prev.exists() and ep.beats:
            prev_beats = Episode.load(prev).beats
            if prev_beats and ep.beats[0].options_remaining > prev_beats[0].options_remaining:
                r.block(f"the situation re-expands across the episode boundary: "
                        f"E{ep.episode - 1:02d} opened with "
                        f"{prev_beats[0].options_remaining} options, "
                        f"E{ep.episode:02d} opens with {ep.beats[0].options_remaining}")

        r.note("NOTE: per-character knowledge-state tracking is the human/LLM half of "
               "this role (see agents/07-continuity-auditor.md); the automated pass "
               "covers clue framing, ledger integrity, loop debt and timeline.")
        r.data["clues_verified"] = len(planned)
        return r


# --------------------------------------------------------------------------- production


class CharacterDesigner(Agent):
    name, stage = "character-designer", 8

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        sheets = ctx.load_yaml(ctx.production_dir / "character-sheets.yaml")
        if not sheets:
            return r.block("no character-sheets.yaml — renders will drift")
        chars = sheets.get("characters", [])
        colours = [c.get("colour") for c in chars if c.get("colour")]
        if len(colours) != len(set(colours)):
            r.warn("two principals share a colour; the audience tracks a smoke-filled "
                   "frame by colour and silhouette alone")
        for c in chars:
            for req in ("silhouette", "voice_profile", "fear", "desire"):
                if not c.get(req):
                    r.warn(f"{c.get('name')} missing {req}")
        r.data["characters"] = len(chars)
        return r.note(f"{len(chars)} characters locked")


class ShotDesigner(Agent):
    name, stage = "shot-designer", 9

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        raw = ctx.load_yaml(ctx.episode_dir / "shotlist.yaml")
        if not raw:
            return r.block("no shotlist.yaml")
        shots = raw.get("shots", [])
        beat_ids = {b.id for b in ctx.episode.beats}
        covered = {s.get("beat_id") for s in shots}
        missing = beat_ids - covered
        if missing:
            r.block(f"beats with no shots: {sorted(missing)}")
        unknown = covered - beat_ids
        if unknown - {None}:
            r.block(f"shots reference unknown beats: {sorted(unknown - {None})}")

        total = sum(float(s.get("duration_sec", 0)) for s in shots)
        if abs(total - ctx.episode.runtime) > 20:
            r.warn(f"shot durations total {total:.0f}s vs episode {ctx.episode.runtime:.0f}s")

        clock_shots = [s for s in shots if s.get("clock_element")]
        need = float(ctx.doctrine.rules("clock_and_shrinking_world")["clock_visible_beat_fraction_min"])
        clock_time = sum(float(s.get("duration_sec", 0)) for s in clock_shots)
        if total and clock_time / total < need:
            r.warn(f"clock element in {clock_time / total:.0%} of shot time, doctrine wants "
                   f"{need:.0%}")
        for s in shots:
            if not s.get("prompt"):
                r.block(f"shot {s.get('id')} has no prompt")
        r.data["shots"] = len(shots)
        r.data["shot_seconds"] = round(total)
        return r.note(f"{len(shots)} shots, {total:.0f}s")


# --------------------------------------------------------------------------- post


class VoiceDirector(Agent):
    name, stage = "voice-director", 11

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        sheets = ctx.load_yaml(ctx.production_dir / "character-sheets.yaml") or {}
        profiles = {c["name"]: c.get("voice_profile") for c in sheets.get("characters", [])}
        raw = ctx.load_yaml(ctx.episode_dir / "shotlist.yaml") or {}
        lines = []
        for s in raw.get("shots", []):
            for ln in s.get("lines", []) or []:
                who = ln.get("character")
                lines.append({
                    "shot": s.get("id"), "beat": s.get("beat_id"), "character": who,
                    "voice_profile": profiles.get(who),
                    "text": ln.get("text"), "direction": ln.get("direction", ""),
                    "breath": ln.get("breath", "controlled"),
                })
                if who and who not in profiles:
                    r.warn(f"{who} speaks with no locked voice profile")
        registers = [c.get("register") for c in sheets.get("characters", []) if c.get("register")]
        if len(registers) != len(set(registers)):
            r.warn("two principals share a vocal register; under smoke the voice is the "
                   "only identity channel left")
        r.artefacts.append(ctx.write_json("vo-manifest.json",
                                          {"dry_run": ctx.dry_run, "lines": lines}))
        r.data["lines"] = len(lines)
        return r.note(f"{len(lines)} dialogue lines routed")


class Composer(Agent):
    name, stage = "composer", 12

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        # The tension curve is derived from the beat sheet, not invented: hooks are
        # peaks, the L2 is the largest pre-button peak, the button is a cliff.
        weights = {None: 0.25, "escalation": 0.6, "reveal": 0.8,
                   "reversal": 0.9, "threat_spike": 0.75, "question": 1.0}
        curve = []
        silent = [b for b in ctx.episode.beats if not b.dialogue]
        for b in ctx.episode.beats:
            level = weights.get(b.hook, 0.4)
            if b.twist_level and b.twist_level >= 2:
                level = min(1.0, level + 0.15)
            curve.append({
                "beat": b.id, "t": b.t_start_sec, "tension": round(level, 2),
                "score": "silence" if not b.dialogue else "bed",
                "clock_voice": b.clock_visible,
            })
        if not silent:
            r.warn("no silent beat — a cut to silence spikes attention harder than any "
                   "sting and costs nothing")
        last = ctx.episode.beats[-1] if ctx.episode.beats else None
        if last and last.hook != "question":
            r.warn("button does not end on a question; do not resolve the cue either")
        r.artefacts.append(ctx.write_json("tension-curve.json", {
            "dry_run": ctx.dry_run,
            "rule": "sound leads picture by one beat; never resolve musically at the button",
            "curve": curve,
        }))
        r.data["peaks"] = sum(1 for c in curve if c["tension"] >= 0.75)
        return r.note(f"{len(curve)} cues, {r.data['peaks']} peaks")


class QCStandards(Agent):
    name, stage = "qc-standards", 14

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        raw = ctx.load_yaml(ctx.episode_dir / "shotlist.yaml") or {}
        shots = raw.get("shots", [])
        checks: list[dict[str, Any]] = []

        def check(cid: str, ok: bool, evidence: str) -> None:
            checks.append({"check": cid, "pass": ok, "evidence": evidence})
            if not ok:
                r.block(f"QC {cid}: {evidence}")

        banned = ("gore", "graphic injury", "close-up of wound", "torture",
                  "blood spray", "child in danger", "dismember")
        offenders = [s.get("id") for s in shots
                     if any(t in (s.get("prompt", "") + s.get("action", "")).lower()
                            for t in banned)]
        check("implied_not_depicted", not offenders,
              f"shots depicting rather than implying: {offenders}" if offenders
              else "threat shown, injury implied")

        flash = [s.get("id") for s in shots if s.get("flash_sequence")]
        check("photosensitivity", not flash, f"flash sequences in {flash}" if flash
              else "no flash sequences")

        opening = [s for s in shots if float(s.get("t_start_sec", 999)) < 3]
        check("cold_open_clean", all(not s.get("known_artefact") for s in opening),
              "artefact in the first 3 seconds — the one frame the algorithm judges"
              if any(s.get("known_artefact") for s in opening) else "cold open clean")

        check("captions_present", bool(raw.get("captions", True)),
              "no caption track; feed viewing is largely sound-off and uncaptioned "
              "material is skipped without being watched")

        real = [s.get("id") for s in shots if s.get("depicts_real_entity")]
        check("no_real_entity_antagonist", not real,
              f"real person/brand implied in {real}" if real else "no real entities")

        tol = float(ctx.doctrine.episode_spec["formats"]["serial_episode"]["runtime_tolerance_sec"])
        check("runtime_in_spec",
              abs(ctx.episode.runtime - ctx.episode.runtime_target_sec) <= tol,
              f"{ctx.episode.runtime:.0f}s vs {ctx.episode.runtime_target_sec:.0f}s")

        r.artefacts.append(ctx.write_json("qc-report.json", {
            "dry_run": ctx.dry_run,
            "veto": "absolute — the CEO cannot override this stage",
            "checks": checks,
        }))
        r.data["passed"] = sum(1 for c in checks if c["pass"])
        r.data["total"] = len(checks)
        return r.note(f"{r.data['passed']}/{len(checks)} checks passed")


class Packaging(Agent):
    name, stage = "packaging", 15

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        raw = ctx.load_yaml(ctx.episode_dir / "packaging.yaml")
        if not raw:
            return r.block("no packaging.yaml — everything upstream is retention, this "
                           "is the capture")
        variants = raw.get("variants", [])
        need = int(ctx.doctrine.gate("publish_greenlight")["requires_packaging_variants"])
        if len(variants) < need:
            r.block(f"{len(variants)} packaging variants, need {need}")

        scored = []
        for v in variants:
            s = v.get("scores", {})
            # Honesty is a multiplier, not an addend. A package that over-promises buys
            # one view and the punishment lands on the next release.
            base = sum(float(s.get(k, 0)) for k in
                       ("curiosity_gap", "specificity", "loss_framing", "legibility_at_120px"))
            honesty = float(s.get("honesty", 0)) / 10.0
            scored.append({**v, "total": round(base * honesty, 2)})
            if honesty < 0.7:
                r.warn(f"variant {v.get('id')} scores {s.get('honesty')}/10 on honesty; "
                       f"the audience punishes bait harder than it rewards the hook")
        scored.sort(key=lambda v: v["total"], reverse=True)
        r.artefacts.append(ctx.write_json("packaging-scored.json", {
            "winner": scored[0] if scored else None, "rotation": scored[1:], }))
        if scored:
            r.data["winner"] = scored[0].get("title")
            r.note(f"winner: {scored[0].get('title')!r} ({scored[0]['total']})")
        return r


class AudienceAnalyst(Agent):
    name, stage = "audience-analyst", 17

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        tele = ctx.load_yaml(ctx.episode_dir / "telemetry.yaml")
        if not tele:
            return r.note("no telemetry yet — the loop closes after publication")
        curve = tele.get("retention_per_second", [])
        if not curve:
            return r.warn("telemetry present but carries no per-second curve; averages "
                          "hide exactly the information this stage needs")
        cliffs = []
        for i in range(1, len(curve)):
            drop = curve[i - 1] - curve[i]
            if drop > 0.02:
                beat = next((b.id for b in ctx.episode.beats
                             if b.t_start_sec <= i <= b.t_end_sec), None)
                cliffs.append({"second": i, "drop": round(drop, 3), "beat": beat})
        r.artefacts.append(ctx.write_json("retention-telemetry.json", {
            "cliffs": cliffs,
            "amendment_rule": "a doctrine change needs >= 3 episodes of evidence; "
                              "single-episode evidence is noise",
        }))
        r.data["cliffs"] = len(cliffs)
        return r.note(f"{len(cliffs)} drop-off cliffs mapped to beats")
