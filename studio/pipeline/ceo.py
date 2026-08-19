"""The CEO: stage-gate orchestration.

Runs every agent in order, applies the three greenlight gates at the points where cost
steps up, and refuses to let material past a gate it failed. The CEO's whole value is
the ability to say no after money has been spent, so the gates get stricter downstream,
never looser.

On a gate failure the run halts and a rework order is written: rule ids and timestamps,
never editorial notes. The Episode Writer consumes that file and the production is
re-run. Three failures at one gate is a kill.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import agents as A
from .models import Doctrine, Episode, TwistLedger
from .publish import Distributor
from .render import Cinematographer, Editor

# Execution order. Gates fire *after* the named stage.
PIPELINE: list[tuple[type[A.Agent], str | None]] = [
    (A.MarketScout, None),
    (A.ConceptArchitect, None),
    (A.StoryArchitect, None),
    (A.TwistMaster, None),
    (A.EpisodeWriter, None),
    (A.RetentionEngineer, "script_greenlight"),
    (A.ContinuityAuditor, None),
    (A.CharacterDesigner, None),
    (A.ShotDesigner, "render_greenlight"),
    (Cinematographer, None),
    (A.VoiceDirector, None),
    (A.Composer, None),
    (Editor, None),
    (A.QCStandards, None),
    (A.Packaging, "publish_greenlight"),
    (Distributor, None),
    (A.AudienceAnalyst, None),
]

GREENLIT, REWORK, KILLED, HELD = "GREENLIT", "REWORK", "KILLED", "HELD"
MAX_REWORKS = 3


@dataclass
class Decision:
    stage: str
    verdict: str
    reason: str
    score: float | None = None

    def as_dict(self) -> dict:
        return {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "stage": self.stage, "verdict": self.verdict,
            "reason": self.reason, "score": self.score,
        }


@dataclass
class ProductionRun:
    production: str
    season: int
    episode: int
    verdict: str = GREENLIT
    stages: list[A.StageResult] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    composite: float | None = None
    halted_at: str | None = None

    @property
    def ok(self) -> bool:
        return self.verdict == GREENLIT


class Studio:
    """The CEO's office. One instance produces one episode."""

    def __init__(self, root: Path, production: str, season: int, episode: int,
                 dry_run: bool = True) -> None:
        self.root = root
        self.doctrine = Doctrine.load(root / "doctrine")
        self.production_dir = root / "productions" / production
        self.season_dir = self.production_dir / f"season-{season:02d}"
        self.episode_dir = self.season_dir / f"ep{episode:02d}"
        self.production, self.season, self.episode = production, season, episode
        self.dry_run = dry_run

    # -- run ------------------------------------------------------------------

    def produce(self) -> ProductionRun:
        run = ProductionRun(self.production, self.season, self.episode)

        beatsheet = self.episode_dir / "beatsheet.yaml"
        if not beatsheet.exists():
            run.verdict, run.halted_at = KILLED, "intake"
            run.decisions.append(Decision("intake", KILLED, f"no beat sheet at {beatsheet}"))
            self._log(run)
            return run

        ledger_path = self.season_dir / "twist-ledger.yaml"
        ctx = A.Context(
            studio_root=self.root,
            production_dir=self.production_dir,
            season_dir=self.season_dir,
            episode_dir=self.episode_dir,
            doctrine=self.doctrine,
            episode=Episode.load(beatsheet),
            ledger=TwistLedger.load(ledger_path) if ledger_path.exists() else TwistLedger.empty(),
            dry_run=self.dry_run,
        )

        for agent_cls, gate_name in PIPELINE:
            agent = agent_cls()
            result = agent.run(ctx)
            run.stages.append(result)

            if result.status == A.BLOCK:
                # A blocking agent stops the line regardless of composite score. QC and
                # the Continuity Auditor hold this power by design; the others earn it
                # by finding something structurally missing.
                run.verdict, run.halted_at = REWORK, agent.name
                run.decisions.append(Decision(agent.name, REWORK, "; ".join(result.notes[:6])))
                self._rework_order(ctx, run, agent.name, result)
                self._log(run)
                return run

            run.decisions.append(Decision(
                agent.name, "PASS",
                result.notes[0] if result.notes else "ok",
                result.data.get("composite"),
            ))

            if gate_name:
                verdict = self._gate(ctx, run, gate_name)
                if verdict is not GREENLIT:
                    run.verdict, run.halted_at = verdict, gate_name
                    self._log(run)
                    return run

        run.composite = ctx.report.composite if ctx.report else None
        self._log(run)
        return run

    # -- gates ----------------------------------------------------------------

    def _gate(self, ctx: A.Context, run: ProductionRun, name: str) -> str:
        gate = self.doctrine.gate(name)
        report = ctx.report
        if report is None:
            run.decisions.append(Decision(name, REWORK, "no retention report at gate"))
            return REWORK

        run.composite = report.composite
        passed = report.passes(gate)

        if name == "publish_greenlight":
            qc = ctx.build / "qc-report.json"
            if gate.get("requires_qc_pass"):
                if not qc.exists():
                    passed = False
                else:
                    checks = json.loads(qc.read_text(encoding="utf-8")).get("checks", [])
                    if any(not c["pass"] for c in checks):
                        passed = False

        if passed:
            run.decisions.append(Decision(
                name, GREENLIT,
                f"composite {report.composite:.1f} >= {gate['min_composite']}, "
                f"{len(report.hard_fails)} hard fails",
                report.composite))
            return GREENLIT

        reason = (f"composite {report.composite:.1f} < {gate['min_composite']}"
                  if report.composite < float(gate["min_composite"])
                  else f"{len(report.hard_fails)} hard fail(s)")
        attempts = self._attempts(name)
        verdict = KILLED if attempts >= MAX_REWORKS else (
            HELD if name == "publish_greenlight" else REWORK)
        run.decisions.append(Decision(name, verdict, reason, report.composite))
        self._rework_order(ctx, run, name, None)
        return verdict

    def _attempts(self, gate_name: str) -> int:
        """Count prior failures at this gate from the decision log."""
        log = self.episode_dir / "build" / "decisions.jsonl"
        if not log.exists():
            return 0
        n = 0
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("stage") == gate_name and d.get("verdict") in (REWORK, HELD):
                n += 1
        return n

    # -- artefacts ------------------------------------------------------------

    def _rework_order(self, ctx: A.Context, run: ProductionRun, where: str,
                      result: A.StageResult | None) -> None:
        """Specific and mechanical. A rule id and a timestamp, never 'make it better'."""
        lines = [
            f"# REWORK ORDER — {self.production} S{self.season:02d}E{self.episode:02d}",
            "",
            f"Halted at: **{where}**",
            f"Attempt: {self._attempts(where) + 1} of {MAX_REWORKS}",
            "",
            "Fix only what is named below. Untargeted rewrites reintroduce solved problems.",
            "",
        ]
        if result and result.notes:
            lines.append("## Stage findings")
            lines += [f"- {n}" for n in result.notes]
            lines.append("")
        if ctx.report:
            lines.append(f"## Retention: composite {ctx.report.composite:.1f}/100")
            lines.append("")
            for f in ctx.report.forces:
                if f.violations:
                    lines.append(f"### {f.force} — {f.score:.0f}/100")
                    lines += [f"- {v}" for v in f.violations]
                    lines.append("")
        path = ctx.build / "rework-order.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        run.decisions.append(Decision(where, "ORDER", f"rework order written to {path}"))

    def _log(self, run: ProductionRun) -> None:
        out = self.episode_dir / "build"
        out.mkdir(parents=True, exist_ok=True)
        with (out / "decisions.jsonl").open("a", encoding="utf-8") as fh:
            for d in run.decisions:
                fh.write(json.dumps(d.as_dict()) + "\n")

    # -- reporting ------------------------------------------------------------

    @staticmethod
    def summary(run: ProductionRun) -> str:
        head = (f"{run.production} S{run.season:02d}E{run.episode:02d}  "
                f"verdict: {run.verdict}"
                + (f"  composite: {run.composite:.1f}" if run.composite is not None else ""))
        lines = [head, "=" * len(head), ""]
        for s in run.stages:
            mark = {A.OK: "ok  ", A.WARN: "warn", A.BLOCK: "BLOCK"}[s.status]
            lines.append(f"  [{mark}] {s.agent}")
            for n in s.notes:
                lines.append(f"          {n}")
            for a in s.artefacts:
                lines.append(f"          -> {a.name}")
        if run.halted_at:
            lines += ["", f"HALTED at {run.halted_at}. See build/rework-order.md."]
        return "\n".join(lines)
