"""Distribution.

Builds a per-platform publish manifest from the finished assets and the winning package.
Credentials are read from the environment only — nothing here ever writes a secret to
the repository, and with no credentials present the agent plans the release and posts
nothing.

Platform mechanics are current as of 2026 and are documented inline because they are the
kind of thing that silently changes and then silently breaks a release.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .agents import Agent, Context, StageResult

PLATFORMS: dict[str, dict[str, Any]] = {
    "youtube": {
        "asset": "master",
        "endpoint": "POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable",
        "auth": "OAuth 2.0 per channel",
        "env": ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"],
        "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        "supports_schedule": True,
        "notes": [
            "Resumable upload. Set full metadata, chapters and captions at upload time —"
            " editing them after publication costs early ranking.",
            "Publish the long-form master here; the vertical cut goes out as a Short.",
        ],
    },
    "tiktok": {
        "asset": "vertical",
        "endpoint": "POST https://open.tiktokapis.com/v2/post/publish/video/init/",
        "auth": "OAuth 2.0 per creator account",
        "env": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_ACCESS_TOKEN"],
        "scopes": ["video.publish"],
        "supports_schedule": False,
        "notes": [
            "Three steps: query creator info for available privacy levels, init the"
            " publish with PULL_FROM_URL or FILE_UPLOAD, then poll /status/fetch/ for"
            " PUBLISH_COMPLETE.",
            "Requires a PASSED APP AUDIT before posts can be public. Budget weeks, not days.",
            "No scheduled_publish_time parameter exists — the API posts immediately or"
            " creates a draft, so scheduling is our scheduler's problem.",
            "Every request must carry a privacy level, commercial-content disclosure and"
            " comment settings.",
        ],
    },
    "instagram": {
        "asset": "vertical",
        "endpoint": "POST https://graph.facebook.com/v21.0/{ig_user_id}/media",
        "auth": "OAuth 2.0, Instagram Graph API",
        "env": ["IG_USER_ID", "IG_ACCESS_TOKEN"],
        "scopes": ["instagram_content_publish"],
        "supports_schedule": False,
        "notes": ["Two-step: create a media container, then publish it by container id."],
    },
}


class Distributor(Agent):
    name, stage = "distributor", 16

    def run(self, ctx: Context) -> StageResult:
        r = StageResult(self.name)

        scored_path = ctx.build / "packaging-scored.json"
        if not scored_path.exists():
            return r.block("no scored packaging — nothing to attach to a release")
        winner = json.loads(scored_path.read_text(encoding="utf-8")).get("winner") or {}

        qc_path = ctx.build / "qc-report.json"
        if not qc_path.exists():
            return r.block("no QC report; QC holds an absolute veto and has not run")
        qc = json.loads(qc_path.read_text(encoding="utf-8"))
        failed = [c["check"] for c in qc.get("checks", []) if not c["pass"]]
        if failed:
            return r.block(f"QC failed {failed} — release held")

        ep = ctx.episode
        slug = f"{ep.production}-s{ep.season:02d}e{ep.episode:02d}"
        targets = []
        for name, p in PLATFORMS.items():
            missing = [v for v in p["env"] if not os.environ.get(v)]
            targets.append({
                "platform": name,
                "ready": not missing,
                "missing_credentials": missing,
                "asset": p["asset"],
                "endpoint": p["endpoint"],
                "auth": p["auth"],
                "scopes": p["scopes"],
                "supports_native_schedule": p["supports_schedule"],
                "notes": p["notes"],
                "payload": {
                    "title": winner.get("title", ep.title),
                    "description": self._description(ctx, winner),
                    "tags": winner.get("tags", []),
                    "thumbnail": winner.get("thumbnail"),
                    "captions": f"{slug}.vtt",
                    "synthetic_media_disclosure": True,
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disclose_commercial_content": False,
                },
            })

        ready = [t["platform"] for t in targets if t["ready"]]
        live = bool(ready) and not ctx.dry_run

        # The release-order rule: the short is the acquisition asset, the episode is the
        # destination, and the short must also end on a question or it spends the loop.
        r.artefacts.append(ctx.write_json("publish-manifest.json", {
            "mode": "live" if live else "dry-run",
            "slug": slug,
            "release_order": ["tiktok/instagram vertical cut", "youtube master"],
            "policy": [
                "never publish an episode whose successor is not already rendered",
                "cadence is fixed and announced; an unpredictable schedule makes the "
                "audience close the open loop by leaving",
                "the vertical cut ends on the question, never the answer",
            ],
            "targets": targets,
        }))

        for t in targets:
            if not t["ready"]:
                r.note(f"{t['platform']}: planned, missing {t['missing_credentials']}")
        if not live:
            r.note("dry-run: manifest written, nothing posted")

        nxt = ctx.season_dir / f"ep{ep.episode + 1:02d}" / "beatsheet.yaml"
        if not nxt.exists():
            r.warn(f"E{ep.episode + 1:02d} does not exist yet; the loop-debt rule applies "
                   f"to the release schedule, not only to the script")

        r.data.update(platforms=len(targets), ready=ready, mode="live" if live else "dry-run")
        return r

    @staticmethod
    def _description(ctx: Context, winner: dict[str, Any]) -> str:
        ep = ctx.episode
        return (
            f"{winner.get('hook_line', ep.logline)}\n\n"
            f"{ep.production.replace('-', ' ').upper()} — Season {ep.season}, "
            f"Episode {ep.episode}: {ep.title}\n\n"
            f"A work of fiction. All characters, organisations and events are invented.\n"
            f"Contains synthetic media.\n"
        )
