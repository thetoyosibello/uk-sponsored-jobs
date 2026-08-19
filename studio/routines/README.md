# The CEO's Calendar — running the studio on Claude Routines

The studio is designed to run without anyone in the room. Claude Routines are the clock;
this directory is the set of standing orders each one carries.

---

## How a Routine actually works here

A Routine fires a **fresh session with no memory of any previous run**. That constraint
shapes the whole design:

1. **State lives on disk, not in a conversation.** `pipeline/slate.py` derives every
   episode's position on the production ladder from files in `productions/`. A cold
   session runs `python3 studio.py next` and knows exactly what to do.
2. **Each prompt is standalone.** No Routine may say "continue where you left off",
   because there is no left off.
3. **Every run ends in a commit.** If the work is not pushed, it did not happen — the
   container is reclaimed and the next Routine starts from the repository.
4. **Exit codes are the contract.** `0` done · `1` rework (actionable) · `2` needs a
   human · `3` bad invocation.

The pipeline is deterministic Python; the *writing* is Claude working to the doctrine.
That division is deliberate and worth being plain about: **no scorer can write a good
scene, and no model should be trusted to grade its own.** The machine holds the
standard, the model does the work, and the standard is the thing that never gets tired
at 3am on episode nine.

---

## The daily calendar

Three production Routines, staggered so each one's output is the next one's input, plus
a weekly review. All times UTC.

| Time | Routine | Does | Ends run when |
|---|---|---|---|
| **06:00 daily** | [Writers' Room](01-writers-room.md) | Writes or reworks the next episode until it passes the script gate | Greenlit and pushed, or 3 failed reworks |
| **12:00 daily** | [Production](02-production.md) | Renders and assembles the next greenlit episode | Master built and pushed, or blocked on credentials |
| **17:00 daily** | [Release](03-release.md) | Publishes the next rendered episode, vertical cut first | Published and logged, or held by QC |
| **08:00 Mondays** | [Retention Review](04-retention-review.md) | Maps drop-off cliffs to beats, proposes doctrine amendments | Report pushed. Amendments need a human |
| **on season end** | [Season Greenlight](05-season-greenlight.md) | Closes the loop ledger, opens the next season's arc | Arc pushed, or escalated |

**Why staggered rather than one Routine doing everything:** a focused prompt does better
work than "do whatever is next", and a failure in rendering should not cost that day's
writing. The Slate already handles ordering; the calendar handles isolation.

**Why every stage runs daily:** twelve days to a finished season, and every stage has
slack — if the Writers' Room fails on Tuesday, Wednesday's run picks up the same
directive rather than skipping the episode.

---

## What happens when a stage is blocked

The Slate refuses to spin. If a rung cannot be climbed — no render credentials, no
publish credentials — `studio.py next` **skips it and returns work that can actually be
done**, which in practice means writing further ahead. A studio with no API keys will
quietly write all twelve episodes and stop, having spent nothing, with a full slate ready
the moment keys appear.

```
$ python3 studio.py status
  BLOCKED STAGES
    greenlit  no render credentials in the environment; set one of VEO_API_KEY, ...
    rendered  no publish credentials in the environment; set one of YOUTUBE_REFRESH_TOKEN, ...

NEXT: write the beat sheet, script, shot list and packaging
  target: ash-river S01E02  (stage: planned, owner: episode-writer)
```

---

## Guardrails

These are the rules that make unattended operation defensible. They are not suggestions
and no Routine may reason its way past one.

### Never, unattended

1. **Never publish anything QC failed.** QC holds an absolute veto that the CEO cannot
   override, and neither can a Routine. A failed check ends the run.
2. **Never amend the doctrine.** The Retention Review *proposes*; a human merges. A
   system that rewrites its own standards while nobody is watching has no standards.
   Amendments arrive as a PR, never as a push to the main branch.
3. **Never retcon a committed twist.** L4 and L5 and their clue trails are frozen once
   Episode 1 ships. If a Routine believes it has found a better series twist, it writes
   the idea into `productions/<show>/IDEAS.md` and leaves the ledger alone.
4. **Never exceed the spend cap.** See below. A run that would breach it stops and
   reports instead.
5. **Never take a fourth swing.** Three failed reworks at one gate is a kill and a
   human decision. The brief is wrong, not the writing, and a fourth attempt just buys
   a more expensive version of the same mistake.
6. **Never publish an episode whose successor is not written.** The loop-debt rule
   applies to the release schedule, not only to the script. Opening a question the
   studio cannot answer next week is the one failure that damages the *next* production.
7. **Never invent a production.** New shows are greenlit by a human. The Concept
   Architect may generate and score candidates; it may not put one into production.

### Spend cap

`routines/budget.yaml` holds the ceiling. The Production Routine reads it, compares
against the render manifest's estimate, and refuses rather than truncates — a half-
rendered episode is worth nothing, so a run that cannot afford the whole thing does not
start it.

### Kill switch

Three, in increasing order of severity:

```bash
touch PAUSE            # committed and pushed: every Routine no-ops on its next run
```
Disable the trigger in Claude's Routines settings — stops the schedule but keeps state.
Delete the trigger — stops it permanently.

Every Routine checks for `PAUSE` before doing anything and exits cleanly if it finds one.

---

## Wiring them up

Each Routine is registered with `create_trigger` in fresh-session mode, using the prompt
body from its file verbatim. Fresh-session mode matters: these must not accumulate
context across weeks of runs.

To change what a Routine does, edit the file **and** update the trigger — the file is the
source of truth for review, the trigger is what actually executes. `update_trigger`
changes the prompt in place and keeps the run history.

---

## Reading the logs

Every run appends to the episode's `build/decisions.jsonl` and pushes it, so the decision
history of the entire studio is in git and attributable to a commit. To see what the CEO
did and why:

```bash
git log --oneline -- productions/            # what shipped, when
cat productions/*/season-*/ep*/build/decisions.jsonl | python3 -m json.tool
python3 studio.py status                     # where everything stands right now
```
