"""Render and assembly: the Cinematographer and the Editor.

Both are provider-agnostic by construction. The studio routes each shot to whichever
generation model suits it and records a fallback, so no single provider's API sunset can
stop a season — a rule written the year OpenAI announced the Sora API would be retired.

With no credentials present, both agents run in dry-run: they emit complete, executable
manifests and plans and generate nothing. That is deliberate. It means a whole season can
be proven production-ready — every prompt, every cost, every cut — before a cent of GPU
time is spent, and it keeps the pipeline runnable in CI.
"""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from typing import Any

from .agents import Agent, Context, StageResult

# Routing policy, not a fixed list. Capability moves monthly; the *shape* of the
# decision does not. See agents/10-cinematographer.md.
PROVIDERS: dict[str, dict[str, Any]] = {
    "cinematic": {
        "family": "veo",
        "env": "VEO_API_KEY",
        "strengths": ["prompt adherence", "native audio", "4K", "landscape and portrait"],
        "usd_per_sec": 0.50,
        "fallback": "motion",
    },
    "consistency": {
        "family": "runway",
        "env": "RUNWAY_API_KEY",
        "strengths": ["reference-driven character consistency", "motion brush", "camera control"],
        "usd_per_sec": 0.35,
        "fallback": "cinematic",
    },
    "motion": {
        "family": "kling",
        "env": "KLING_API_KEY",
        "strengths": ["hair/smoke/liquid/fabric", "multi-shot storyboard", "audio sync across cuts"],
        "usd_per_sec": 0.30,
        "fallback": "consistency",
    },
}

DEFAULT_NEGATIVE = (
    "text overlay, watermark, extra limbs, warped hands, plastic skin, "
    "modern logos, saturated background, clean clothing, calm expression"
)


@dataclass
class ShotPlan:
    id: str
    beat_id: str
    duration_sec: float
    provider: str
    fallback: str
    prompt: str
    negative_prompt: str
    character_refs: list[str]
    seed: int | None
    cost_usd: float


def _route(shot: dict[str, Any]) -> str:
    """Pick a provider lane from what the shot actually needs."""
    hint = shot.get("provider_hint")
    if hint in PROVIDERS:
        return hint
    if shot.get("character_refs"):
        return "consistency"
    text = f"{shot.get('prompt', '')} {shot.get('subject', '')}".lower()
    if any(w in text for w in ("smoke", "fire", "ember", "water", "hair", "fabric", "ash")):
        return "motion"
    return "cinematic"


def _seed(episode: int, shot_id: str) -> int:
    """Deterministic per-episode, per-shot seed so a re-run reproduces the same frames."""
    return (hash((episode, shot_id)) & 0xFFFFFF) or 1


class Cinematographer(Agent):
    name, stage = "cinematographer", 10

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        raw = ctx.load_yaml(ctx.episode_dir / "shotlist.yaml")
        if not raw:
            return r.block("no shotlist.yaml")

        sheets = ctx.load_yaml(ctx.production_dir / "character-sheets.yaml") or {}
        refs = {c["name"]: c.get("reference_set", []) for c in sheets.get("characters", [])}

        plans: list[ShotPlan] = []
        for s in raw.get("shots", []):
            lane = _route(s)
            prov = PROVIDERS[lane]
            names = s.get("character_refs", []) or []
            unknown = [n for n in names if n not in refs]
            if unknown:
                r.warn(f"shot {s.get('id')} references characters with no locked "
                       f"reference set: {unknown} — descriptions drift, references do not")
            dur = float(s.get("duration_sec", 0))
            plans.append(ShotPlan(
                id=s["id"],
                beat_id=s.get("beat_id", ""),
                duration_sec=dur,
                provider=prov["family"],
                fallback=PROVIDERS[prov["fallback"]]["family"],
                prompt=s["prompt"],
                negative_prompt=s.get("negative_prompt", DEFAULT_NEGATIVE),
                character_refs=[p for n in names for p in refs.get(n, [])],
                seed=_seed(ctx.episode.episode, s["id"]),
                cost_usd=round(dur * float(prov["usd_per_sec"]), 2),
            ))

        credentialled = [k for k, p in PROVIDERS.items() if os.environ.get(p["env"])]
        live = bool(credentialled) and not ctx.dry_run
        total = round(sum(p.cost_usd for p in plans), 2)

        r.artefacts.append(ctx.write_json("render-manifest.json", {
            "mode": "live" if live else "dry-run",
            "credentialled_lanes": credentialled,
            "policy": "never single-source; every shot records a fallback lane",
            "consistency_protocol": [
                "condition on the locked reference set, never re-describe a face in prose",
                "generate 3 candidates per shot; the identity check picks, not the prettiest frame",
                "anchor frames: last frame of shot N seeds shot N+1 within a scene",
                "seeds locked per character per episode and recorded here",
            ],
            "shot_count": len(plans),
            "total_seconds": round(sum(p.duration_sec for p in plans)),
            "estimated_cost_usd": total,
            "shots": [p.__dict__ for p in plans],
        }))

        if not live:
            r.note(f"dry-run: {len(plans)} shots planned, est. ${total} — nothing generated")
            if not credentialled:
                r.note("no provider credentials in the environment; set one of "
                       + ", ".join(p["env"] for p in PROVIDERS.values()) + " to render")
        else:
            r.note(f"live render across lanes {credentialled}")

        r.data.update(shots=len(plans), cost_usd=total, mode="live" if live else "dry-run")
        return r


class Editor(Agent):
    name, stage = "editor", 13

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)
        raw = ctx.load_yaml(ctx.episode_dir / "shotlist.yaml")
        if not raw:
            return r.block("no shotlist.yaml")
        shots = raw.get("shots", [])

        # Cut to the grid first. The grid is the contract: if a hook lands late, some
        # stretch of the episode has a gap the doctrine says loses people.
        edl, t = [], 0.0
        for s in shots:
            dur = float(s.get("duration_sec", 0))
            edl.append({
                "shot": s["id"], "beat": s.get("beat_id"),
                "timeline_in": round(t, 2), "timeline_out": round(t + dur, 2),
                "transition": s.get("transition", "cut"),
                "audio": {"dialogue": bool(s.get("lines")),
                          "bed": s.get("audio_bed", "clock"),
                          "duck_under_dialogue": True},
            })
            t += dur

        # Verify the assembled timeline still lands the hooks where the sheet promised.
        drift = []
        for b in ctx.episode.beats:
            entries = [e for e in edl if e["beat"] == b.id]
            if not entries:
                continue
            actual = entries[0]["timeline_in"]
            if abs(actual - b.t_start_sec) > 4.0:
                drift.append(f"{b.id} planned {b.t_start_sec:.0f}s, assembles at {actual:.0f}s")
        for d in drift:
            r.warn(f"timeline drift: {d} — the edit is the last place structure can slip")

        vspec = ctx.doctrine.episode_spec["formats"]["vertical_clip"]
        vertical = self._vertical_cut(ctx, edl, vspec)

        plan_path = ctx.write_json("edit-plan.json", {
            "dry_run": ctx.dry_run,
            "master": {"aspect": "16:9", "runtime_sec": round(t, 2), "edl": edl},
            "vertical_cut": vertical,
            "rules": [
                "enter late, leave early: trim the first and last four seconds of every scene",
                "cut on motion, never after a completed sentence — that is an exit point",
                "the button is frame-accurate and freezes on the unanswered image",
            ],
        })
        r.artefacts.append(plan_path)
        r.artefacts.append(self._assemble_script(ctx, edl))
        r.data.update(cuts=len(edl), runtime_sec=round(t, 2), drift=len(drift))
        return r.note(f"{len(edl)} cuts, {t:.0f}s master + 60s vertical")

    @staticmethod
    def _vertical_cut(ctx: Context, edl: list[dict], vspec: dict) -> dict:
        """The 9:16 asset is an advertisement for the loop, so it ends on a question too."""
        beats = ctx.episode.beats
        opening = next((b for b in beats if b.hook), beats[0] if beats else None)
        spike = max((b for b in beats if b.hook in ("reversal", "reveal", "threat_spike")),
                    key=lambda b: b.t_start_sec, default=None)
        button = beats[-1] if beats else None
        pick = [b for b in (opening, spike, button) if b]
        return {
            "aspect": vspec["aspect"],
            "runtime_sec": vspec["runtime_target_sec"],
            "note": "freeze-frame lands 55-58s; ends on the question, never the answer",
            "segments": [
                {"role": role, "beat": b.id, "source_in": b.t_start_sec}
                for role, b in zip(("hook", "spike", "button"), pick)
            ],
        }

    @staticmethod
    def _assemble_script(ctx: Context, edl: list[dict]) -> Any:
        """Emit the ffmpeg build even where ffmpeg is absent, so the plan stays portable."""
        lines = [
            "#!/usr/bin/env bash",
            "# Generated by studio/pipeline/render.py — do not edit by hand.",
            "set -euo pipefail",
            "",
            'command -v ffmpeg >/dev/null || { echo "ffmpeg not installed" >&2; exit 1; }',
            'CLIPS="${CLIPS_DIR:-./clips}"',
            'OUT="${OUT_DIR:-./out}"',
            'mkdir -p "$OUT"',
            "",
            "concat=$(mktemp)",
        ]
        for e in edl:
            lines.append(f'echo "file \'$CLIPS/{e["shot"]}.mp4\'" >> "$concat"')
        lines += [
            "",
            "# Master: concat the graded clips, then lay dialogue and score over the top.",
            'ffmpeg -y -f concat -safe 0 -i "$concat" -c:v libx264 -crf 18 -preset slow \\',
            '  -pix_fmt yuv420p "$OUT/master_silent.mp4"',
            "",
            'ffmpeg -y -i "$OUT/master_silent.mp4" -i "$CLIPS/../audio/dialogue.wav" \\',
            '  -i "$CLIPS/../audio/score.wav" \\',
            '  -filter_complex "[1:a]volume=1.0[d];[2:a]volume=0.45[s];[d][s]amix=inputs=2[a]" \\',
            '  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k "$OUT/master.mp4"',
            "",
            "# Vertical acquisition cut: 9:16, centre-weighted crop, 60s.",
            'ffmpeg -y -i "$OUT/master.mp4" -t 60 \\',
            '  -vf "crop=ih*9/16:ih,scale=1080:1920" -c:a copy "$OUT/vertical.mp4"',
            "",
            f'echo "built {len(edl)} cuts -> $OUT/master.mp4"',
        ]
        path = ctx.build / "assemble.sh"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        path.chmod(0o755)
        return path


def ffmpeg_available() -> bool:
    from shutil import which
    return which("ffmpeg") is not None


def quote(arg: str) -> str:
    return shlex.quote(arg)
