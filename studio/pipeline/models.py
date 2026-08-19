"""Data model for everything the studio passes between agents.

A production is a chain of documents. Each agent consumes some and emits others, and
every document that reaches the Retention Engine has to be loadable into these types.
Keeping the schema here (rather than letting each agent invent its own dict shape)
is what makes the CEO's gates enforceable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

HOOK_KINDS = {"escalation", "reveal", "reversal", "threat_spike", "question"}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the top level")
    return data


@dataclass
class Beat:
    """The atomic unit the scorer reads. Roughly one per 20-40 seconds of runtime."""

    id: str
    t_start_sec: float
    t_end_sec: float
    scene: str
    action: str
    cost: str
    loops_opened: list[str] = field(default_factory=list)
    loops_closed: list[str] = field(default_factory=list)
    irony_gap: bool = False
    clock_visible: bool = False
    hook: str | None = None
    options_remaining: int = 0
    twist_level: int | None = None
    capability_gap: bool = False
    bonding_device: str | None = None
    clue_id: str | None = None
    external_rescue: bool = False
    surprise: bool = False
    establishing: bool = False
    dialogue: bool = True

    @property
    def duration(self) -> float:
        return max(0.0, self.t_end_sec - self.t_start_sec)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Beat:
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(raw) - known
        if unknown:
            raise ValueError(f"beat {raw.get('id')!r}: unknown fields {sorted(unknown)}")
        missing = {"id", "t_start_sec", "t_end_sec", "scene", "action", "cost"} - set(raw)
        if missing:
            raise ValueError(f"beat {raw.get('id')!r}: missing required fields {sorted(missing)}")
        hook = raw.get("hook")
        if hook is not None and hook not in HOOK_KINDS:
            raise ValueError(f"beat {raw['id']!r}: hook {hook!r} not in {sorted(HOOK_KINDS)}")
        return cls(**raw)


@dataclass
class Clue:
    """A planted clue. The dual read is what separates fair play from cheating."""

    id: str
    twist_id: str
    episode: int
    beat_id: str
    plant: str
    surface_read: str
    true_read: str
    visibility: float = 1.0  # 0.5 peripheral, 1.0 framed, 1.5 stated aloud

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Clue:
        missing = {"id", "twist_id", "episode", "beat_id", "plant",
                   "surface_read", "true_read"} - set(raw)
        if missing:
            raise ValueError(f"clue {raw.get('id')!r}: missing {sorted(missing)}")
        return cls(**raw)


@dataclass
class Twist:
    """An entry on the twist ladder, with the episode and beat where it fires."""

    id: str
    level: int
    episode: int
    beat_id: str
    reframes: str
    reveal: str
    cost: str
    character: str | None = None
    character_basis: str | None = None  # the established desire or fear this maps to
    contradicts_onscreen_fact: bool = False
    # A reframe left to breathe deflates into exposition, so L4/L5 must name the
    # concrete threat that lands within 30 seconds of the reveal.
    followed_within_30s_by: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Twist:
        unknown = set(raw) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"twist {raw.get('id')!r}: unknown fields {sorted(unknown)}")
        missing = {"id", "level", "episode", "beat_id", "reframes", "reveal", "cost"} - set(raw)
        if missing:
            raise ValueError(f"twist {raw.get('id')!r}: missing {sorted(missing)}")
        if not 1 <= raw["level"] <= 5:
            raise ValueError(f"twist {raw['id']!r}: level must be 1-5")
        return cls(**raw)


@dataclass
class TwistLedger:
    """Season-wide record of every twist and every clue planted for it."""

    twists: list[Twist] = field(default_factory=list)
    clues: list[Clue] = field(default_factory=list)

    def clues_for(self, twist_id: str) -> list[Clue]:
        return [c for c in self.clues if c.twist_id == twist_id]

    def twist_by_id(self, twist_id: str) -> Twist | None:
        return next((t for t in self.twists if t.id == twist_id), None)

    @classmethod
    def load(cls, path: Path) -> TwistLedger:
        raw = _load_yaml(path)
        return cls(
            twists=[Twist.from_dict(t) for t in raw.get("twists", [])],
            clues=[Clue.from_dict(c) for c in raw.get("clues", [])],
        )

    @classmethod
    def empty(cls) -> TwistLedger:
        return cls()


@dataclass
class Episode:
    """A beat sheet plus the metadata the scorer needs to judge it in context."""

    production: str
    season: int
    episode: int
    title: str
    runtime_target_sec: float
    beats: list[Beat]
    prior_cliffhanger: str | None = None
    protective_duty_character: str | None = None
    wound_shown_beat: str | None = None
    wound_said_beat: str | None = None
    logline: str = ""

    @property
    def runtime(self) -> float:
        return max((b.t_end_sec for b in self.beats), default=0.0)

    def beat(self, beat_id: str) -> Beat | None:
        return next((b for b in self.beats if b.id == beat_id), None)

    def scenes(self) -> dict[str, list[Beat]]:
        out: dict[str, list[Beat]] = {}
        for b in self.beats:
            out.setdefault(b.scene, []).append(b)
        return out

    @classmethod
    def load(cls, path: Path) -> Episode:
        raw = _load_yaml(path)
        beats = [Beat.from_dict(b) for b in raw.get("beats", [])]
        beats.sort(key=lambda b: b.t_start_sec)
        return cls(
            production=raw["production"],
            season=int(raw["season"]),
            episode=int(raw["episode"]),
            title=raw.get("title", ""),
            runtime_target_sec=float(raw.get("runtime_target_sec", 420)),
            beats=beats,
            prior_cliffhanger=raw.get("prior_cliffhanger"),
            protective_duty_character=raw.get("protective_duty_character"),
            wound_shown_beat=raw.get("wound_shown_beat"),
            wound_said_beat=raw.get("wound_said_beat"),
            logline=raw.get("logline", ""),
        )


@dataclass
class Doctrine:
    """The rulebook, loaded from doctrine/*.yaml. Agents read; only the analyst amends."""

    physics: dict[str, Any]
    episode_spec: dict[str, Any]
    twist_ladder: dict[str, Any]
    genre: dict[str, Any]

    @classmethod
    def load(cls, root: Path) -> Doctrine:
        return cls(
            physics=_load_yaml(root / "attention_physics.yaml"),
            episode_spec=_load_yaml(root / "episode_spec.yaml"),
            twist_ladder=_load_yaml(root / "twist_ladder.yaml"),
            genre=_load_yaml(root / "genre_survival.yaml"),
        )

    def rules(self, force: str) -> dict[str, Any]:
        return self.physics["forces"][force]["rules"]

    def weight(self, force: str) -> float:
        return float(self.physics["forces"][force]["weight"])

    def gate(self, name: str) -> dict[str, Any]:
        return self.physics["gates"][name]

    @property
    def hard_fail_rules(self) -> set[str]:
        return set(self.physics.get("hard_fail_rules", []))
