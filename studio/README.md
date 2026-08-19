# The Studio

An automated film production and publishing system, built around one question:
**what actually captures and retains attention?**

The answer, in one sentence, is that attention is captured by what you withhold and
retained by the viewer's own unfinished mental work. Everything below is machinery for
manufacturing, sustaining and strategically resolving incompleteness — and for refusing
to spend money on material that doesn't.

---

## Quick start

```bash
python3 studio.py doctor      # can this checkout produce?
python3 studio.py status      # where every episode stands
python3 studio.py next        # the single next action

# Run one episode through 17 agents and three gates. Renders nothing.
python3 studio.py run --production ash-river --season 1 --episode 1

# Same, but call real generation and publishing providers.
python3 studio.py run --production ash-river --season 1 --episode 1 --live

python3 studio.py score --production ash-river --season 1 --episode 1   # grade and stop
python3 studio.py test                                                  # 67 checks
```

Exit codes are the contract the Routines read:
`0` done/greenlit · `1` rework or held · `2` needs a human · `3` bad invocation.

Dependencies: Python 3.11+ and PyYAML. `ffmpeg` is only needed to execute the assembly
script; the plan is emitted either way.

---

## Running itself

The studio is wired to [Claude Routines](routines/README.md) and runs unattended on a
daily calendar. The thing that makes that possible is `pipeline/slate.py` — **the Slate**.

A Routine fires a fresh session with no memory of any previous run, so state cannot live
in a conversation. It lives on disk: the Slate reads the production tree, derives every
episode's rung on the production ladder, and emits one directive.

```
planned → written → rework → greenlit → rendered → released
```

| Time (UTC) | Routine | Does |
|---|---|---|
| 06:00 daily | Writers' Room | writes or reworks the next episode until it passes the gate |
| 12:00 daily | Production | renders and assembles the next greenlit episode |
| 17:00 daily | Release | publishes the next rendered episode, vertical cut first |
| 08:00 Mondays | Retention Review | maps drop-off cliffs to beats, proposes doctrine amendments |

**The Slate refuses to spin.** If a rung cannot be climbed — no render credentials, no
publish credentials — it skips that stage and returns work that *can* be done. A studio
with no API keys quietly writes all twelve episodes, spends nothing, and has a full slate
ready the moment keys appear.

Priority is deliberately not "lowest rung first". Material already paid for outranks
material not yet written: a rendered-but-unreleased episode is spent money earning
nothing. Writing the next episode is the lowest priority that still counts as progress,
because it is the only move that creates new liabilities.

### Guardrails on unattended operation

The full set is in [`routines/README.md`](routines/README.md). The ones that matter most:

- **Never publish past a QC failure.** Absolute veto; no Routine may reason past it.
- **Never amend the doctrine unattended.** The Retention Review opens a PR and waits.
  A system that rewrites its own standards while nobody is watching has no standards.
- **Never retcon a committed twist.** L4/L5 and their clue trails freeze once E01 ships.
- **Never exceed [`routines/budget.yaml`](routines/budget.yaml).** A run that cannot
  afford the whole episode does not start it — a half-rendered episode is worth nothing.
- **Never take a fourth swing.** Three failed reworks is a kill and a human decision.
- **Never publish an episode whose successor is not ready.** Loop debt applies to the
  release schedule, not just the script.

Kill switch: `touch PAUSE`, commit, push. Every Routine no-ops on its next run, and
`studio.py` itself enforces it so it holds even if a prompt is edited.

### The honest division of labour

The pipeline is deterministic Python; the *writing* is Claude working to the doctrine.
No scorer can write a good scene, and no model should be trusted to grade its own. The
machine holds the standard, the model does the work, and the standard is the thing that
never gets tired at 3am on episode nine.

---

## How it fits together

```
RESEARCH.md ──► doctrine/*.yaml ──► pipeline/retention.py ──► CEO gate ──► spend
 (findings,      (thresholds a       (grades a beat sheet,   (greenlight,
  with sources)   machine checks)     names the violations)   rework, kill)
                                                │
                          agents/*.md ──────────┘
                       (the craft half of each role)
        ▲                                                            │
        └───────── doctrine amendments ◄── AudienceAnalyst ◄── telemetry
```

Nothing renders until the beat sheet passes the gate, because the cost curve is brutal:

| stage | relative cost of a mistake |
|---|---|
| concept | 1× |
| script | 4× |
| render | 120× |
| publish | ∞ — it teaches the distribution algorithm that our work is skippable |

That last row is why the gates get **stricter** downstream, never looser, and why
"we already paid for it" is not an argument.

---

## The six attention forces

Measured on every episode, weighted into one composite score. Full derivation and
sources in [`RESEARCH.md`](RESEARCH.md); thresholds in
[`doctrine/attention_physics.yaml`](doctrine/attention_physics.yaml).

| Force | Weight | The rule underneath it |
|---|---:|---|
| **Open loop pressure** | 24 | Zeigarnik: 3–7 live questions at all times, and a loop may only close in a beat that opens another |
| **Dramatic irony gap** | 22 | Hitchcock's bomb: the audience ahead of a character for ≥55% of runtime. Surprise is 15 seconds; suspense is 15 minutes |
| **Hook cadence** | 20 | Micro-drama telemetry: threat by second 3, a hook every ≤55s, the button in the last 8s, ends on a question |
| **Empathy lock** | 14 | A named person the audience wants to survive, inside 90 seconds, via ≥2 bonding devices |
| **Clock & shrinking world** | 12 | A depleting quantity legible in ≥70% of runtime; options never widen; every scene takes something away |
| **Twist ladder** | 8 | Every scene twists; every twist is planted, dual-read, in character, and costs the protagonist |

Seven rules are **hard fails** — any one of them sinks the episode regardless of score,
because any one of them is sufficient to lose the audience on its own.

---

## The twist ladder

"Plot twists on so many levels" made structural: not more twists, but twists at
different **scopes**, each reframing a larger unit of story.

| | Scope | Cadence | Reframes | Clues required |
|---|---|---|---|---:|
| **L1** | scene | every scene | the beat | 1 |
| **L2** | episode | every episode | the episode's goal was the wrong goal | 3 |
| **L3** | arc | every 3 episodes | an alliance, identity, or loyalty | 5 |
| **L4** | season | once | the premise — the situation was engineered | 9 |
| **L5** | series | once | the protagonist — they are a cause of it | 12 |

L4 and L5 are decided **before Episode 1 is written**. They cannot be revised later
without violating `forbid_retcon`, because the clue trail is planted from the first
ninety seconds.

Fair play is enforced by bookkeeping, not by good intentions: every clue carries a
`surface_read` and a `true_read`, and the Continuity Auditor verifies each one against
the **shot list**, not the script — a clue that was never framed does not exist.

---

## The agents

The CEO holds greenlight, rework and kill authority. Each specialist has a role card in
[`agents/`](agents/) carrying the craft doctrine, and an executable half in `pipeline/`
carrying the checks.

| Stage | Agent | Gate it feeds |
|---:|---|---|
| 0 | **CEO** — showrunner-in-chief | all three |
| 1 | Market Scout | advisory only; forbidden from proposing stories |
| 2 | Concept Architect | premise test ≥ 5/6 |
| 3 | Story Architect | arc supports the ladder and the resource tiers |
| 4 | Twist Master | fair-play contract |
| 5 | **Retention Engineer** | owns all three gates; reports, never decides |
| 6 | Episode Writer | `script_greenlight` ≥ 78 |
| 7 | Continuity Auditor | can block a render alone |
| 8 | Character Designer | identity consistency |
| 9 | Shot Designer | `render_greenlight` ≥ 84 |
| 10 | Cinematographer | provider-agnostic render |
| 11 | Voice Director | performance under stress |
| 12 | Composer | tension curve matches the beat sheet |
| 13 | Editor | hooks land on the second |
| 14 | QC & Standards | **absolute veto** — the CEO cannot override |
| 15 | Packaging | ≥ 5 scored variants, honesty as a multiplier |
| 16 | Distributor | `publish_greenlight` + QC pass |
| 17 | Audience Analyst | the only agent that may amend the doctrine |

---

## Dry-run by default

With no credentials in the environment, the render and publish stages produce complete,
executable manifests and generate and post **nothing**. This is deliberate: a whole
season can be proven production-ready — every prompt, every provider, every cost, every
cut, every API payload — before a cent of GPU time is spent, and the pipeline stays
runnable in CI.

Set provider keys to go live:

```
VEO_API_KEY / RUNWAY_API_KEY / KLING_API_KEY          # video, routed per shot
YOUTUBE_CLIENT_ID / _SECRET / _REFRESH_TOKEN          # long-form master
TIKTOK_CLIENT_KEY / _SECRET / _ACCESS_TOKEN           # vertical cut (needs a passed app audit)
IG_USER_ID / IG_ACCESS_TOKEN                          # reels
```

Nothing here ever writes a secret to the repository. **Never single-source a provider** —
every shot records a fallback lane, a rule written the year one major video API announced
its own sunset.

---

## In production now

**[ASH RIVER](productions/ash-river/bible.md)** — survival thriller, 12 × 7 minutes,
assembling into an ~84-minute feature.

> One road out of a burning valley, eleven passengers, and a driver who counts them at
> every stop. On the last count of the day she gets twelve.

Episode 1, *"Headcount"*, is written, scored and greenlit end to end; the Routines take
it from here:
[beat sheet](productions/ash-river/season-01/ep01/beatsheet.yaml) ·
[script](productions/ash-river/season-01/ep01/script.md) ·
[shot list](productions/ash-river/season-01/ep01/shotlist.yaml) ·
[twist ledger](productions/ash-river/season-01/twist-ledger.yaml)

```
composite 100.0/100   hard fails: 0
  open_loop_pressure          100.0  w24   loop curve 2→7, never below 3 after 0:45
  dramatic_irony_gap          100.0  w22   audience ahead 78% of runtime
  hook_cadence                100.0  w20   10 hooks, largest gap 55s, ends on a question
  empathy_lock                100.0  w14   3 bonding devices inside 90s
  clock_and_shrinking_world   100.0  w12   clock legible 89%, options 6→1
  twist_ladder                100.0  w 8   100% scene coverage, L2 planted 3×
```

33 shots, ~$155 estimated render, 37 dialogue lines, 6/6 QC checks, publish manifests
staged for three platforms. Episodes 2–12 are arced, with every L4 and L5 clue slot
already allocated in the twist ledger — the Writers' Room fills them one per day.

---

## A note on what the score does and does not mean

The engine measures **structure**. It cannot see a flat performance, a dead line
reading, or a shot that doesn't cut. A 100 is a licence to render, not proof of quality —
which is exactly why the Editor, QC and Packaging stages sit downstream of it, and why
the Audience Analyst exists to correct the doctrine against what real viewers actually do.

And the standing warning, from the Analyst's own role card: optimising purely on measured
retention converges on the local maximum of what already exists. Retention tells you where
you lost people. It never tells you what you should have made instead.
