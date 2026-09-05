# Setup — three steps, about ten minutes

You only do this once. After that the routine runs on its own and the sheet fills
itself.

Here is what you are building:

```
  Cloud routine  07:47 + 16:47      Local sweep  08:17 + 17:17
  runs always, even if the Mac      runs on your Mac, opens and
  is off. Search results plus       verifies every advert, can use
  the sponsor-register check.       your logged-in browser.
        \                                    /
         \                                  /
          v                                v
       GitHub repo: hr.csv + other.csv
                     |
                     v
       Google Sheet, 2 tabs   <- reads the files, refreshes itself
```

Two sweeps write to the same two files. The cloud one is the baseline that never
misses a day; the local one runs half an hour later and does the deeper work the
cloud sandbox is not allowed to do (it blocks every website except search).
Both pull before they push, so they don't overwrite each other.

Nothing in this system can apply for a job, send a message, log in anywhere, or
spend money. It only reads job pages and writes two files.

---

## Step 1 — Make an empty GitHub repo

Go to <https://github.com/new> and fill in exactly this:

- **Repository name:** `uk-sponsored-jobs`
- **Public** (it has to be public, or Google Sheets cannot read the files —
  see the privacy note at the bottom)
- Leave "Add a README", ".gitignore" and "licence" **unticked**. The repo must
  start completely empty.

Click **Create repository**, then come back here.

---

## Step 2 — Push these files up

Open Terminal and run these one at a time. Check each one worked before running
the next.

```bash
cd ~/projects/sponsored-jobs
```

```bash
git add -A
```

```bash
git commit -m "Set up sponsored job sweep"
```

```bash
git branch -M main
```

```bash
git remote add origin https://github.com/thetoyosibello/uk-sponsored-jobs.git
```

```bash
git push -u origin main
```

That last one may ask for a username and password. Username is `thetoyosibello`. The
password is **not** your GitHub password — it is your Personal Access Token, the
same one saved in your Keychain from last time. If it goes through without
asking, the Keychain already handled it.

Check it worked: <https://github.com/thetoyosibello/uk-sponsored-jobs> should now show
`hr.csv`, `other.csv`, `PLAYBOOK.md` and this file.

---

## Step 2b — Let the cloud routine write to the repo

Creating the repo is not enough. The Claude GitHub App is installed on *selected
repositories*, and a brand-new repo is not on that list, so the routine can read
the files but not push to them. A live run on 14 Aug 2026 found 14 good jobs and
then lost them all to this:

```
403 Resource not accessible by integration
```

Reads worked the whole time, which is what makes this one sneaky — the repo is
public, so anyone can read it. Only writing is blocked.

To fix it, go to <https://github.com/settings/installations>, click **Configure**
next to Claude, and under **Repository access** add `uk-sponsored-jobs` to the
selected repositories. If it is already set to "All repositories", check instead
that the app has **Contents: Read and write** permission.

Until this is done the cloud routine will do all its work and then throw it away
at the last step, twice a day.

---

## Step 3 — Build the live sheet

1. Go to <https://sheets.new> and name it **UK Sponsored Jobs — Live**.
2. Rename the first tab to **HR (D)**. Click cell **A1** and paste:

```
=IMPORTDATA("https://raw.githubusercontent.com/thetoyosibello/uk-sponsored-jobs/main/hr.csv?v=3")
```

3. Add a second tab, name it **Other (T)**. Click cell **A1** and paste:

```
=IMPORTDATA("https://raw.githubusercontent.com/thetoyosibello/uk-sponsored-jobs/main/other.csv?v=3")
```

You will see just the column headers at first. That is correct — the rows appear
after the first sweep runs.

> **The `?v=` number on the end is load-bearing. Leave it there.**
> `IMPORTDATA` caches hard, keyed on the exact URL. Set up on a plain URL while
> the CSV still held only its header, the sheet **kept serving that empty result
> even after six rows had landed in the repo** — verified 14 Aug 2026. Reloading
> the browser did not shift it, because a reload does not make Google refetch.
> Changing the number makes it a URL Google has never seen, which forces a fresh
> fetch. GitHub ignores the parameter and serves the same file.
>
> **If the sheet ever looks frozen: bump the number.** Raise `?v=3` to `?v=4` in
> both tabs and the rows reappear. Bump it whenever the columns change too, since
> that is a different shape of data arriving at the same address.
>
> Do not try to automate that stamp with `NOW()` — Sheets rejects it outright
> with *"This function is not allowed to reference a cell with NOW(), RAND(),
> RANDARRAY(), or RANDBETWEEN()"*, and it blocks the indirect version through a
> helper cell too.
>
> Diagnosing a frozen sheet: check
> <https://github.com/thetoyosibello/uk-sponsored-jobs/commits/main> first. New commits
> there but nothing new in the sheet means it is this cache, not the sweeps.

---

## How you use the sheet day to day

Columns **A to N** are filled by the sweeps. Do not type in them — anything you
write there gets wiped on the next refresh.

**Column A is `Status`**, and it is the first thing to read:

- **`Live`** — a sweep opened the advert this run and it is accepting applications
- **`Closed 2026-08-14`** — it opened the advert and the job has closed, with the
  date it found out. The row is kept deliberately so you keep the history
- **`Unverified`** — nobody could open the page, so its state is genuinely unknown

**Newest jobs arrive at the top**, directly under the header, so closed rows sink
down the list as new ones push in above them.

To see only what you can still apply for, use **Data → Create a filter view** and
filter column A to `Live`. Use a filter view rather than sorting or filtering the
sheet directly, which fights with the formula.

**Your own notes need their own tab.** Rows now move — new ones push in at the
top and any row's `Status` can change — so anything typed beside a job will not
stay with it. Keep notes on a separate tab and paste the job's **link** next to
each one, so you can always tell which job a note belongs to.

Worth knowing about the columns:

- **Skill level** — `Higher` means the occupation qualifies for sponsorship
  normally. `Medium — TSL/transitional only` means the role is below degree level
  and only works in narrow cases. Read those with your eyes open.
- **Sponsor licence** — `Yes — Skilled Worker` means the employer is on the
  gov.uk register for the right route. `Not found` usually means their trading
  name differs from their registered name, so check by hand before writing it
  off. A licence means an employer *can* sponsor, never that they *will*.
- **Fit** — 5 is apply today, 3 has a real caveat, 2 is a long shot.

---

## Changing what it looks for

Edit **`PLAYBOOK.md`** in this folder, then push it:

```bash
cd ~/projects/sponsored-jobs && git add -A && git commit -m "Tune search" && git push
```

The routine re-reads the playbook on every run, so the next run picks up your
change. You never need to touch the routine itself.

Section 3 holds both profiles and is the highest-leverage thing to tune: add a
sector D or T wants, or rule one out, and the next run reflects it.

**Do not edit it while a sweep is running.** On 14 Aug 2026 a mid-run edit was
caught by the sweep itself, which stopped and asked rather than working from
rules that were changing underneath it. Correct behaviour, but it cost the run —
commit your edits between runs instead.

---

## Why this repo lives in `~/projects` and must stay there

**Never move it into `~/Downloads`, `~/Desktop` or `~/Documents.`** macOS
protects those three folders with TCC, and a launchd agent cannot execute a
script inside them. It does not warn you: the job fires on schedule and dies
instantly with

```
/bin/bash: .../local-sweep.sh: Operation not permitted
```

That is exactly what happened. The sweep ran from `~/Downloads` and every
scheduled run from 14 Aug to 5 Sep 2026 failed this way — twice a day, silently,
for three weeks. The sheet froze on 14 August as a result. Granting Full Disk
Access would also fix it, but keeping the repo in `~/projects` is simpler and
needs no system settings.

---

## The local sweep on your Mac

Installed and scheduled at **08:17 and 17:17**, half an hour behind the cloud
routine so the two never fight over the push.

### One thing you must do first: give it a long-lived login

The first test run failed in eleven seconds with
`OAuth session expired and could not be refreshed`. A scheduled job cannot open a
browser to log you in, so it needs a token that does not expire. Run this once,
in Terminal, and follow the prompts:

```bash
claude setup-token
```

That prints a token valid for a year. The sweep reads it from
`~/.sponsored-jobs.env`. Create that file with the command below — it prompts for
the token without echoing it, so the token never lands in your shell history.

**This is zsh syntax**, which is the shell on this Mac. The bash equivalent
(`read -rs -p "..."`) fails here with `read: -p: no coprocess`, because zsh uses
`-p` to mean "read from a coprocess" and takes its prompt as `"var?prompt"`:

```bash
read -rs "T?Paste token: " && printf 'export CLAUDE_CODE_OAUTH_TOKEN=%s\n' "$T" > ~/.sponsored-jobs.env && chmod 600 ~/.sponsored-jobs.env && unset T && echo " saved"
```

The terminal will print `Paste token:` and then appear to hang. That is the
silent prompt working as intended — paste, press enter, and you get ` saved`.

The file lives in your home folder, deliberately not in this repo, so it can never
be committed and pushed to a public GitHub repo by accident. Treat that token like
a password: anything holding it can run Claude as you. If you ever paste it
somewhere it shouldn't be — a chat, a screenshot, a shared doc — run
`claude setup-token` again to mint a fresh one, which retires the old.

Then prove it worked:

```bash
bash ~/projects/sponsored-jobs/local-sweep.sh
```

That runs a full sweep in the foreground and takes a few minutes. If `sweep.log`
ends with `exit=0` and rows appeared in the CSVs, the scheduled runs will work
from then on. **Until you do this, only the cloud routine is actually running** —
the local job will keep firing twice a day and failing instantly, at no cost, but
also to no effect.

- It only runs when the Mac is **awake**. Asleep at 08:17 means that sweep is
  skipped; the cloud one still ran, so you never get a totally empty day.
- Its log is `sweep.log` in this folder. Open it if a day looks thin.
- To pause it: `launchctl unload ~/Library/LaunchAgents/com.tysitv.sponsored-jobs.plist`
- To start it again: `launchctl load ~/Library/LaunchAgents/com.tysitv.sponsored-jobs.plist`
- To run one right now, on demand:

```bash
bash ~/projects/sponsored-jobs/local-sweep.sh
```

Rules it follows with your browser, in `LOCAL.md`: read only, never apply, never
submit a form, never log in, never type a credential. If a site is logged out it
stops and says so rather than trying to sign in.

---

## Checking on it

- Runs and logs: <https://claude.ai/code/routines>
- Every run leaves a commit in the repo, so
  <https://github.com/thetoyosibello/uk-sponsored-jobs/commits/main> tells you at a
  glance whether it ran and what it found.
- If the sheet stops updating, that commit list is the first place to look: no
  new commits means the routine failed, not the sheet.

---

## Privacy note

The repo has to be public for Google Sheets to read it. What is public: job
listings that are already public, and `PLAYBOOK.md`, which describes the two
people by initial only — no names, no contact details, no CVs. If you would
rather nothing at all was public, tell Claude and it can rebuild the write path
as a Google Apps Script web app instead, which keeps everything inside your
Google account at the cost of a more fiddly setup.
