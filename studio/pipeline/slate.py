"""The Slate — what the studio should do next.

A Claude Routine fires a **fresh session with no memory of any prior run**. That session
has to answer one question before it can do anything useful: where is this production,
and what is the single next thing that moves it forward?

That answer cannot live in a conversation, so it lives here. The Slate reads the
production directory, derives every episode's position on the production ladder from
files on disk, and emits one directive. Everything about the studio's autonomy rests on
this being derivable rather than remembered.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

import yaml


class Stage(IntEnum):
    """The production ladder. An episode is always at exactly one rung."""

    PLANNED = 0      # named in the season arc, nothing written
    WRITTEN = 1      # beat sheet exists
    REWORK = 2       # written, ran, and failed a gate
    GREENLIT = 3     # passed every gate in a dry run; manifests staged
    RENDERED = 4     # a live render manifest exists
    RELEASED = 5     # recorded in the season release log

    @property
    def label(self) -> str:
        return self.name.lower()


# The agent that owns the next move at each rung.
OWNER = {
    Stage.PLANNED: "episode-writer",
    Stage.WRITTEN: "retention-engineer",
    Stage.REWORK: "episode-writer",
    Stage.GREENLIT: "cinematographer",
    Stage.RENDERED: "distributor",
    Stage.RELEASED: None,
}

ACTION = {
    Stage.PLANNED: "write the beat sheet, script, shot list and packaging",
    Stage.WRITTEN: "score it and take it through the gates",
    Stage.REWORK: "fix the named violations and re-run",
    Stage.GREENLIT: "render the shot list and assemble",
    Stage.RENDERED: "publish to the release platforms",
    Stage.RELEASED: "nothing — this episode has shipped",
}


@dataclass
class EpisodeStatus:
    production: str
    season: int
    episode: int
    stage: str
    stage_rank: int
    title: str = ""
    composite: float | None = None
    hard_fails: int = 0
    rework_attempts: int = 0
    blocking: list[str] = field(default_factory=list)
    path: str = ""

    @property
    def ref(self) -> str:
        return f"{self.production} S{self.season:02d}E{self.episode:02d}"


@dataclass
class Directive:
    """One instruction. A Routine does this and nothing else."""

    action: str
    owner: str | None
    ref: str | None
    production: str | None
    season: int | None
    episode: int | None
    stage: str | None
    detail: str
    command: str | None = None

    def render(self) -> str:
        lines = [f"NEXT: {self.action}"]
        if self.ref:
            lines.append(f"  target: {self.ref}  (stage: {self.stage}, owner: {self.owner})")
        lines.append(f"  {self.detail}")
        if self.command:
            lines.append(f"  run: {self.command}")
        return "\n".join(lines)


RENDER_KEYS = ("VEO_API_KEY", "RUNWAY_API_KEY", "KLING_API_KEY")
PUBLISH_KEYS = ("YOUTUBE_REFRESH_TOKEN", "TIKTOK_ACCESS_TOKEN", "IG_ACCESS_TOKEN")


class Slate:
    """Reads the production tree and reports state. Never writes anything."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.productions_dir = root / "productions"

    # -- capabilities ---------------------------------------------------------

    @staticmethod
    def can_render() -> bool:
        import os
        return any(os.environ.get(k) for k in RENDER_KEYS)

    @staticmethod
    def can_publish() -> bool:
        import os
        return any(os.environ.get(k) for k in PUBLISH_KEYS)

    def blocked_stages(self) -> dict[str, str]:
        """Stages the studio cannot currently advance, and why.

        An unattended Routine must not spin on a rung it has no means to climb. It
        skips these and does the next thing it *can* do — which is why writing the
        following episode is always available as fallback work.
        """
        out = {}
        if not self.can_render():
            out[Stage.GREENLIT.label] = (
                "no render credentials in the environment; set one of "
                + ", ".join(RENDER_KEYS))
        if not self.can_publish():
            out[Stage.RENDERED.label] = (
                "no publish credentials in the environment; set one of "
                + ", ".join(PUBLISH_KEYS))
        return out

    # -- discovery ------------------------------------------------------------

    def productions(self) -> list[str]:
        if not self.productions_dir.is_dir():
            return []
        return sorted(p.name for p in self.productions_dir.iterdir()
                      if p.is_dir() and (p / "bible.md").exists())

    def seasons(self, production: str) -> list[int]:
        base = self.productions_dir / production
        out = []
        for d in sorted(base.glob("season-*")):
            m = re.fullmatch(r"season-(\d+)", d.name)
            if m and d.is_dir():
                out.append(int(m.group(1)))
        return out

    def planned_episode_count(self, production: str, season: int) -> int:
        """How many episodes the arc commits to, so unwritten ones are still visible."""
        arc = self.productions_dir / production / f"season-{season:02d}" / "arc.md"
        if not arc.exists():
            return 0
        found = {int(m) for m in re.findall(r"\bE(\d{2})\b", arc.read_text(encoding="utf-8"))}
        return max(found) if found else 0

    # -- per-episode state ----------------------------------------------------

    def episode_status(self, production: str, season: int, episode: int) -> EpisodeStatus:
        ep_dir = (self.productions_dir / production / f"season-{season:02d}"
                  / f"ep{episode:02d}")
        st = EpisodeStatus(production=production, season=season, episode=episode,
                           stage=Stage.PLANNED.label, stage_rank=int(Stage.PLANNED),
                           path=str(ep_dir))

        beatsheet = ep_dir / "beatsheet.yaml"
        if not beatsheet.exists():
            st.blocking.append("no beatsheet.yaml")
            return st

        try:
            with beatsheet.open(encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            st.title = raw.get("title", "")
        except yaml.YAMLError as exc:
            st.blocking.append(f"beatsheet.yaml will not parse: {exc}")
            return st

        st.stage, st.stage_rank = Stage.WRITTEN.label, int(Stage.WRITTEN)

        if self._released(production, season, episode):
            st.stage, st.stage_rank = Stage.RELEASED.label, int(Stage.RELEASED)
            return st

        build = ep_dir / "build"
        report = self._json(build / "retention-report.json")
        if report:
            st.composite = report.get("composite")
            st.hard_fails = len(report.get("hard_fails", []))

        decisions = self._decisions(build / "decisions.jsonl")
        st.rework_attempts = sum(1 for d in decisions
                                 if d.get("verdict") in ("REWORK", "HELD"))

        # Never ran, or ran and stopped short: the writer still owns it.
        last_verdicts = [d["verdict"] for d in decisions if d.get("verdict") in
                         ("GREENLIT", "REWORK", "HELD", "KILLED")]
        greenlit_run = bool(last_verdicts) and last_verdicts[-1] == "GREENLIT"

        if not (ep_dir / "shotlist.yaml").exists():
            st.blocking.append("no shotlist.yaml")
            return st
        if not (ep_dir / "packaging.yaml").exists():
            st.blocking.append("no packaging.yaml")
            return st

        if decisions and not greenlit_run:
            st.stage, st.stage_rank = Stage.REWORK.label, int(Stage.REWORK)
            order = build / "rework-order.md"
            st.blocking.append(f"see {order}" if order.exists() else "last run did not greenlight")
            return st
        if not decisions:
            st.blocking.append("never run through the pipeline")
            return st

        st.stage, st.stage_rank = Stage.GREENLIT.label, int(Stage.GREENLIT)

        manifest = self._json(build / "render-manifest.json")
        if manifest and manifest.get("mode") == "live":
            st.stage, st.stage_rank = Stage.RENDERED.label, int(Stage.RENDERED)
        return st

    def season_status(self, production: str, season: int) -> list[EpisodeStatus]:
        planned = self.planned_episode_count(production, season)
        existing = set()
        base = self.productions_dir / production / f"season-{season:02d}"
        for d in base.glob("ep*"):
            m = re.fullmatch(r"ep(\d+)", d.name)
            if m:
                existing.add(int(m.group(1)))
        numbers = sorted(existing | set(range(1, planned + 1)))
        return [self.episode_status(production, season, n) for n in numbers]

    def all_status(self) -> list[EpisodeStatus]:
        out = []
        for p in self.productions():
            for s in self.seasons(p):
                out.extend(self.season_status(p, s))
        return out

    # -- the directive --------------------------------------------------------

    def next_action(self) -> Directive:
        """One instruction, chosen by the CEO's ordering rules.

        Priority is deliberately NOT 'lowest rung first'. Material already paid for
        outranks material not yet written: an episode sitting rendered-but-unreleased
        is spent money earning nothing, and a rework order is a known defect with a
        known fix. Writing the next episode is the lowest priority that still counts
        as progress, because it is the only one that creates new liabilities.
        """
        statuses = self.all_status()
        if not statuses:
            return Directive(
                action="greenlight a production", owner="concept-architect", ref=None,
                production=None, season=None, episode=None, stage=None,
                detail="no productions found — the Concept Architect owns the next move",
            )

        def pick(stage: Stage) -> EpisodeStatus | None:
            candidates = [s for s in statuses if s.stage_rank == int(stage)]
            return min(candidates, key=lambda s: (s.production, s.season, s.episode)) \
                if candidates else None

        blocked = self.blocked_stages()
        for stage in (Stage.RENDERED, Stage.REWORK, Stage.GREENLIT,
                      Stage.WRITTEN, Stage.PLANNED):
            hit = pick(stage)
            if not hit:
                continue
            if stage.label in blocked:
                # No means to climb this rung. Fall through to work we can actually do
                # rather than burning a scheduled run on a no-op.
                continue

            # An episode that has burned its rework budget is a CEO decision, not a
            # writer's. Surface it as a kill rather than a sixth rewrite.
            if stage is Stage.REWORK and hit.rework_attempts >= 3:
                return Directive(
                    action="kill or re-brief", owner="ceo", ref=hit.ref,
                    production=hit.production, season=hit.season, episode=hit.episode,
                    stage=hit.stage,
                    detail=(f"{hit.rework_attempts} failed reworks — the brief is wrong, "
                            f"not the writing. Escalate to a human before spending again."),
                )

            base = (f"python3 studio.py run --production {hit.production} "
                    f"--season {hit.season} --episode {hit.episode}")
            # Writing and gating are free; rendering and publishing spend money, so
            # only those two rungs pass --live.
            cmd = base + (" --live" if stage in (Stage.GREENLIT, Stage.RENDERED) else "")
            if stage is Stage.PLANNED:
                cmd = None

            detail = ACTION[Stage(stage)]
            if hit.blocking:
                detail += f" — blocking: {'; '.join(hit.blocking)}"
            if hit.composite is not None:
                detail += f" (last composite {hit.composite})"

            return Directive(
                action=ACTION[Stage(stage)].split(" —")[0], owner=OWNER[Stage(stage)],
                ref=hit.ref, production=hit.production, season=hit.season,
                episode=hit.episode, stage=hit.stage, detail=detail, command=cmd,
            )

        return Directive(
            action="open the next season", owner="story-architect", ref=None,
            production=statuses[0].production, season=None, episode=None, stage=None,
            detail="every planned episode has shipped — the arc for the next season is the move",
        )

    # -- rendering ------------------------------------------------------------

    def render(self) -> str:
        rows = self.all_status()
        if not rows:
            return "SLATE: empty. No productions."
        width = max(len(r.ref) for r in rows)
        lines = ["SLATE", "=" * 5, ""]
        current = None
        for r in rows:
            key = (r.production, r.season)
            if key != current:
                current = key
                lines.append(f"  {r.production} — season {r.season}")
            bar = "#" * r.stage_rank + "." * (5 - r.stage_rank)
            extra = f"  {r.composite}" if r.composite is not None else ""
            note = f"  ({'; '.join(r.blocking)})" if r.blocking else ""
            lines.append(f"    {r.ref:<{width}}  [{bar}] {r.stage:<9}{extra}{note}")
        blocked = self.blocked_stages()
        if blocked:
            lines += ["", "  BLOCKED STAGES"]
            lines += [f"    {stage:<9} {why}" for stage, why in blocked.items()]
        lines += ["", self.next_action().render()]
        return "\n".join(lines)

    def as_dict(self) -> dict[str, Any]:
        return {
            "episodes": [asdict(s) for s in self.all_status()],
            "next": asdict(self.next_action()),
        }

    # -- io -------------------------------------------------------------------

    @staticmethod
    def _json(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _decisions(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def _released(self, production: str, season: int, episode: int) -> bool:
        log = self.productions_dir / production / f"season-{season:02d}" / "release-log.yaml"
        if not log.exists():
            return False
        try:
            with log.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except yaml.YAMLError:
            return False
        return any(int(r.get("episode", -1)) == episode and r.get("published_at")
                   for r in data.get("releases", []))
