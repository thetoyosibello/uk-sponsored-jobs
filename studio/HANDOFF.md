# HANDOFF — automated film studio

**For the next Claude session. Read this first; it is the whole context.**

Written 2026-08-19. User: btoyosi09@gmail.com (GitHub owner `tysitv`).

---

## 1. The one thing that is blocked

Everything is built, tested and working. **The only outstanding problem is that the code
is sitting in the wrong repository and cannot be pushed to the right one.**

- **Right repo:** `tysitv/story-studio` — the user created it, it is empty, it is real.
- **Wrong repo (current home):** `tysitv/uk-sponsored-jobs`, branch
  `claude/automated-movie-production-dv279o`. This is a UK visa-sponsorship job tracker
  and has nothing to do with film. The studio lives in its `studio/` subdirectory as
  three commits explicitly labelled `HOLDING COMMIT`.

**The exact error, on `git push` to story-studio:**

```
remote: access denied by the git proxy: tysitv/story-studio is not in this session's
authorized repository set, so the proxy will not inject a credential for it.
To fix, add the repository to the session's sources.
```

**What was tried and failed:**

| Attempt | Result |
|---|---|
| `mcp__…__add_repo(tysitv/story-studio, access=push)` | `MCP tool call requires approval` — called 6×, the approval prompt never reached the user |
| `mcp__github__create_repository` | `403 Resource not accessible by integration` — the App cannot create repos |
| `mcp__…__list_repos` | `MCP tool call requires approval` — same gate |
| Direct `git push` to the new remote | 403 from the git proxy (message above) |

**If the new session is sourced from `story-studio`, this problem is already solved** —
just retrieve the code (§2) and push. Do not re-litigate the old session's tooling.

---

## 2. How to retrieve the code

Three copies exist. Any one is complete.

1. **The holding branch** (most reliable):
   ```bash
   git clone https://github.com/tysitv/uk-sponsored-jobs.git
   cd uk-sponsored-jobs
   git checkout claude/automated-movie-production-dv279o
   # everything is in studio/
   ```
2. **A git bundle** already sent to the user in chat: `story-studio.bundle`, 172K,
   verified complete history, **already in the correct root layout**.
   ```bash
   git clone story-studio.bundle story-studio
   ```
3. The old session's scratchpad (ephemeral, probably gone — ignore).

### Layout change on migration

In `uk-sponsored-jobs` everything is under `studio/`. In `story-studio` it must sit at
**repository root** — `studio.py`, `doctrine/`, `agents/`, `pipeline/`, `productions/`,
`routines/`, `tests/`, `RESEARCH.md`, `README.md`, `.github/workflows/ci.yml`.

The bundle is already laid out that way. If you migrate from the holding branch instead,
move `studio/*` up one level. Imports already handle both layouts (`studio.py` and
`tests/test_retention.py` each try root-relative first, then `studio.`-prefixed).

### Final cleanup once story-studio has the code

```bash
# in uk-sponsored-jobs
git checkout claude/automated-movie-production-dv279o
git revert --no-commit 81c89e5 14fb309 ed96701   # or just delete the branch
```
The branch never touched `main`. Deleting it outright is fine and cleanest.

---

## 3. What the user asked for

> Build a fully automated movie production and publishing system. Research what makes a
> great film and incorporate it. Build agents for each step with a CEO directing
> everything. Find out what captures and retains attention. Survival/suspense, viewers
> hooked and wanting more. Plot twists on many levels. Every episode must leave viewers
> wanting to finish. Start production today.

Then, later: move it out of the jobs repo, and **make it fully automated with Claude
Routines**.

Two decisions the user made explicitly:
- **Dedicated repo**, not a subdirectory of an existing one.
- **"Daily everything"** cadence — write, render and release one episode per day.

---

## 4. What exists (all working, 68 tests passing)

### The research → rules → enforcement spine

`RESEARCH.md` — the answer to "what captures and retains attention", with sources.
One-sentence version: **attention is captured by what you withhold and retained by the
viewer's own unfinished mental work.** Findings: Zeigarnik open loops (and the corollary
that unpaid loops are a debt that damages the *next* production), Hitchcock's bomb
(suspense is a state, surprise is an event — 15 minutes vs 15 seconds), Hasson's ISC
neural-coupling work, micro-drama retention telemetry (hook every 45–60s, end on a
question), fair-play twist construction, ticking-clock craft.

`doctrine/*.yaml` — those findings as numeric thresholds:
- `attention_physics.yaml` — six weighted forces (open_loop_pressure 24,
  dramatic_irony_gap 22, hook_cadence 20, empathy_lock 14, clock_and_shrinking_world 12,
  twist_ladder 8), three gates (script 78 / render 84 / publish 84), seven hard-fail rules
- `episode_spec.yaml` — timing to the second, 7-min serial + 60s vertical + feature cut
- `twist_ladder.yaml` — the five levels and the fair-play contract
- `genre_survival.yaml` — house genre doctrine, the six-question premise test

`pipeline/retention.py` — grades a beat sheet against all six forces and returns
**timestamped, rule-named violations**, so rework orders are mechanical
(`hook_interval_max_sec: 82s with no hook between 03:12 and 04:34`) not editorial.

### The twist ladder (the user's "twists on many levels")

| | Scope | Cadence | Reframes | Clues |
|---|---|---|---|---:|
| L1 | scene | every scene | the beat | 1 |
| L2 | episode | every episode | the episode's goal was wrong | 3 |
| L3 | arc | every 3 eps | an alliance / identity / loyalty | 5 |
| L4 | season | once | **the premise — it was engineered** | 9 |
| L5 | series | once | **the protagonist — they caused it** | 12 |

**L4 and L5 are frozen.** They were committed before E01 was written and the clue trail
is already planted in shipped material. Changing them violates `forbid_retcon`. If a
future session thinks it has a better L5, it writes to `IDEAS.md` and leaves the ledger
alone.

Fair play is bookkeeping: every clue carries a `surface_read` and a `true_read`, and the
Continuity Auditor verifies each against the **shot list, not the script** — a clue that
was never framed does not exist.

### Agents and orchestration

`agents/` — 18 role cards (00-ceo through 17-audience-analyst). The craft half of each
job. `pipeline/agents.py`, `render.py`, `publish.py` are the executable half.

`pipeline/ceo.py` — stage-gate state machine. Gates tighten downstream because the cost
curve is concept 1× / script 4× / render 120× / publish ∞ (a weak release teaches the
algorithm we are skippable). Three failed reworks at one gate = kill. QC and the
Continuity Auditor can block alone; **QC's veto cannot be overridden by anyone.**

Render and publish are provider-agnostic with per-shot fallback lanes and run dry with no
credentials, emitting full manifests. No secret is ever written to the repo.

### The autonomy layer

`pipeline/slate.py` — **this is what makes Routines possible.** A Routine fires a fresh
session with no memory, so state cannot live in a conversation; the Slate derives every
episode's rung (`planned → written → rework → greenlit → rendered → released`) from files
on disk and emits one directive.

Two non-obvious behaviours, both deliberate — do not "fix" them:
- **It skips rungs it cannot climb.** No render credentials → it returns writing work
  instead of spinning. A studio with no API keys quietly writes all 12 episodes, spends
  nothing, and is ready the moment keys appear.
- **Priority is not lowest-rung-first.** Rendered-but-unreleased outranks unwritten,
  because that is spent money earning nothing. Writing is *lowest* priority — it is the
  only move that creates new liabilities.

`studio.py` — the single CLI the Routines drive:
`doctor | status | next | score | run [--live] | test`.
Exit codes are the contract: **0** done · **1** rework · **2** needs a human · **3** bad call.

`routines/` — the standing orders as versioned markdown, ready to paste into
`create_trigger` **verbatim**:

| File | Cron (UTC) | Owner |
|---|---|---|
| `01-writers-room.md` | `0 6 * * *` | episode-writer |
| `02-production.md` | `0 12 * * *` | cinematographer |
| `03-release.md` | `0 17 * * *` | distributor |
| `04-retention-review.md` | `0 8 * * 1` | audience-analyst |
| `05-season-greenlight.md` | on demand | story-architect |

Plus `routines/budget.yaml` (per-episode $250 / day $400 / month $4000, `stop_and_report`
on breach — never truncate; a half-rendered episode is worth nothing).

**Guardrails — do not weaken these:**
1. Never publish past a QC failure.
2. **Never amend the doctrine unattended.** The analyst opens a PR and waits. A system
   that rewrites its own standards while nobody watches has no standards.
3. Never retcon a committed twist.
4. Never exceed the budget; stop and report.
5. Never take a fourth swing after three failed reworks.
6. Never publish an episode whose successor is not ready.
7. Never put a new show into production — humans greenlight shows.

Kill switch: `touch PAUSE`, commit, push. Enforced inside `studio.py` itself so it holds
even if a Routine prompt is edited.

`.github/workflows/ci.yml` — runs doctor + tests, then **re-scores every written episode**
so a doctrine amendment cannot silently invalidate shipped material.

---

## 5. The production: ASH RIVER

Survival thriller. 12 × 7 min, assembling into an ~84-minute feature.

> One road out of a burning valley, eleven passengers, and a driver who counts them at
> every stop. On the last count of the day she gets twelve.

- **L4 (E08):** the fire was set. Ignition points form a line, not a spread; the gate was
  installed three weeks early; the evacuation was routed by the office that lit it.
- **L5 (E12):** the calm voice on the radio is the son of one of three people who died
  under Maren's command eleven years ago. Every turn he gave her took her *toward* the
  same canyon, so she would make the identical choice with witnesses. She does.
- **The wound:** she counts people aloud and always starts at nine. Nobody notices for
  eleven episodes because the audience assumes she is picking up mid-count. She is
  finishing the count she abandoned. Planted E01 beat b02, never explained until E12.

**State:** E01 "Headcount" and E02 "The Clinic" both **greenlit at 100.0/100, zero hard
fails**, full pipeline. E03–E12 arced, with every L3/L4/L5 clue slot already allocated in
`twist-ledger.yaml` (18 twists, 47 clues).

**Slate says next action: write E03.** E03 carries **L3-A** — there is no Dispatch 9;
county comms went down 40 minutes before the bus left. Its allocated clues are already in
the ledger and are commitments, not suggestions.

---

## 6. Immediate next steps, in order

1. Get the code into `tysitv/story-studio` at root layout (§2).
2. Verify: `python3 studio.py doctor && python3 studio.py test` → expect **68 passed**.
3. Delete or revert the holding branch on `uk-sponsored-jobs`.
4. **Create the four Routines** with `create_trigger`, fresh-session-per-fire, prompts
   verbatim from `routines/*.md`. Critical: the environment must be sourced from
   `story-studio`, or every firing wakes in the wrong repo and finds no studio.
5. Optional but this is what actually starts the flywheel: add render credentials
   (`VEO_API_KEY` / `RUNWAY_API_KEY` / `KLING_API_KEY`) and publish credentials. Until
   then the studio writes ahead and spends nothing, which is correct behaviour.

Note on TikTok: the Content Posting API needs a **passed app audit** before posts can be
public — budget weeks — and has **no scheduled-publish parameter**, so scheduling is our
scheduler's problem. This is documented in `pipeline/publish.py` and `03-release.md`.

---

## 7. Honest notes for whoever picks this up

- **The 100/100 scores prove less than they look.** The beat sheets were written against
  rules by the same author. The real proof is `tests/test_retention.py`, which breaks the
  shipping episode one doctrine rule at a time and asserts the engine catches each.
- **The engine measures structure, not execution.** It cannot see a flat performance or a
  shot that does not cut. Passing the gate is necessary, not sufficient.
- **Nothing has been rendered or published.** Every render/publish artefact so far is a
  dry-run manifest. Estimated cost is ~$155–160 per episode across ~30 shots.
- **The division of labour is deliberate:** the pipeline is deterministic Python, the
  *writing* is Claude working to the doctrine. No scorer can write a good scene and no
  model should grade its own. The machine holds the standard; the standard is the thing
  that never gets tired at 3am on episode nine.
- **One real bug was found and fixed** by writing E02: the cross-episode options check
  compared a new episode's opening against the previous episode's *closing*, which drives
  the count to zero by mid-season. It is now opening-to-opening, with the season shrink
  tracked physically as boundary mileage in `arc.md`. Two slate tests that pinned specific
  episode numbers were made shape-based at the same time.
