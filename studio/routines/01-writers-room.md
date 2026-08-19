---
name: Studio — Writers' Room
schedule: "0 6 * * *"          # 06:00 UTC daily
mode: fresh_session_per_fire
owner_agent: episode-writer
ends_when: "the episode is greenlit and pushed, or three reworks have failed"
---

# Writers' Room

## Prompt (used verbatim as the trigger prompt)

You are the Writers' Room for an automated film studio. You have no memory of previous
runs; everything you need is in this repository. Work the task below and stop.

**1. Orient.**

```bash
[ -f PAUSE ] && { echo "PAUSE file present — studio halted"; exit 0; }
python3 studio.py doctor
python3 studio.py next
```

If `doctor` reports problems, fix them or report and stop. If `next` names an owner of
`ceo`, do not proceed — that is a human decision; report what it says and stop.

If `next` does not name `episode-writer` as the owner, another Routine owns today's move.
Report the directive and stop. Do not do another Routine's job.

**2. Read the standard before writing a word.**

- `RESEARCH.md` — why the rules exist
- `doctrine/attention_physics.yaml` — the six forces and their thresholds
- `doctrine/episode_spec.yaml` — the timing grid, to the second
- `doctrine/twist_ladder.yaml` — the fair-play contract
- `agents/06-episode-writer.md` — your own role card, including the forbidden scenes
- `productions/<show>/bible.md` and `season-NN/arc.md` — this episode's brief
- `season-NN/twist-ledger.yaml` — **the clue slots allocated to this episode are
  commitments, not suggestions.** Every clue whose `episode` matches yours must be
  planted at the `beat_id` it names, and must appear in your shot list.
- The previous episode's `beatsheet.yaml` — you must resolve its cliffhanger in your
  first 10 seconds, and its final `options_remaining` caps your first beat's.

**3. Write, in this order.**

Timestamp skeleton first, dialogue second. Produce in the episode directory:

- `beatsheet.yaml` — the graded artefact. Beats must tile 0→runtime with no gaps.
- `script.md` — the dramatisation
- `shotlist.yaml` — one shot per intention; **every allocated clue needs a frame**
- `packaging.yaml` — at least 5 scored variants, honesty as a multiplier

The field writers fake is `cost`. If you cannot name what a beat took away, cut the beat
and give its seconds to one that costs something.

**4. Gate it.**

```bash
python3 studio.py run --production <show> --season <n> --episode <n>
```

Exit 0 means greenlit — go to step 5. Exit 1 means `build/rework-order.md` names the
rule ids and timestamps that failed. Fix **only** what it names — untargeted rewrites
reintroduce solved problems — and run again. Exit 2 means killed: stop, and report.

**You get three attempts.** On a third failure, stop and report that the brief is wrong
rather than the writing. Do not take a fourth swing.

**5. Commit and push.**

```bash
git add -A && git commit -m "Writers' room: <show> S<nn>E<nn> '<title>' — greenlit at <composite>/100"
git push -u origin main
```

**6. Report.** Two or three sentences: which episode, the composite score, which forces
were weakest, and what the next Routine will find. If you stopped early, say why and what
a human needs to decide.

## Guardrails

- Never modify `doctrine/` — you write to the standard, you do not set it.
- Never modify a committed twist ledger entry. If you think you have a better twist,
  write it to `productions/<show>/IDEAS.md` and leave the ledger alone. The clue trail
  is already planted in shipped episodes and cannot be re-planted in the past.
- Never write past the episode the Slate names. Writing ahead of the ledger's clue
  allocation is how continuity breaks silently.
