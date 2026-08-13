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
cd ~/Downloads/sponsored-jobs
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
git remote add origin https://github.com/tysitv/uk-sponsored-jobs.git
```

```bash
git push -u origin main
```

That last one may ask for a username and password. Username is `tysitv`. The
password is **not** your GitHub password — it is your Personal Access Token, the
same one saved in your Keychain from last time. If it goes through without
asking, the Keychain already handled it.

Check it worked: <https://github.com/tysitv/uk-sponsored-jobs> should now show
`hr.csv`, `other.csv`, `PLAYBOOK.md` and this file.

---

## Step 3 — Build the live sheet

1. Go to <https://sheets.new> and name it **UK Sponsored Jobs — Live**.
2. Rename the first tab to **HR (D)**. Click cell **A1** and paste:

```
=IMPORTDATA("https://raw.githubusercontent.com/tysitv/uk-sponsored-jobs/main/hr.csv")
```

3. Add a second tab, name it **Other (T)**. Click cell **A1** and paste:

```
=IMPORTDATA("https://raw.githubusercontent.com/tysitv/uk-sponsored-jobs/main/other.csv")
```

You will see just the column headers at first. That is correct — the rows appear
after the routine's first run.

Google refreshes an `IMPORTDATA` formula roughly every hour on its own. To pull
new rows immediately, reload the browser tab.

---

## How you use the sheet day to day

Columns **A to M** are filled by the routine. Do not type in them — anything you
write there gets wiped on the next refresh.

Columns **N onwards are yours.** Put your own headers in `N1` and `O1`, something
like **Status** and **Notes**, and track your applications there. New rows are
always added at the *bottom* of the file and existing rows are never reordered,
so your notes stay lined up with their job forever.

To see the newest jobs first, use **Data → Create a filter view** and sort by
column A descending. Use a filter view rather than sorting the sheet directly,
because sorting directly fights with the formula.

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
cd ~/Downloads/sponsored-jobs && git add -A && git commit -m "Tune search" && git push
```

The routine re-reads the playbook on every run, so the next run picks up your
change. You never need to touch the routine itself.

The first thing worth editing is **section 3, D's profile** — it is currently
generic HR. Fill in D's real seniority, years of experience, CIPD level, sector
and preferred location and the fit scores get far more accurate.

---

## The local sweep on your Mac

Already installed and scheduled — nothing for you to do. It runs at **08:17 and
17:17**, half an hour behind the cloud routine so the two never fight over the
push.

- It only runs when the Mac is **awake**. Asleep at 08:17 means that sweep is
  skipped; the cloud one still ran, so you never get a totally empty day.
- Its log is `sweep.log` in this folder. Open it if a day looks thin.
- To pause it: `launchctl unload ~/Library/LaunchAgents/com.tysitv.sponsored-jobs.plist`
- To start it again: `launchctl load ~/Library/LaunchAgents/com.tysitv.sponsored-jobs.plist`
- To run one right now, on demand:

```bash
bash ~/Downloads/sponsored-jobs/local-sweep.sh
```

Rules it follows with your browser, in `LOCAL.md`: read only, never apply, never
submit a form, never log in, never type a credential. If a site is logged out it
stops and says so rather than trying to sign in.

---

## Checking on it

- Runs and logs: <https://claude.ai/code/routines>
- Every run leaves a commit in the repo, so
  <https://github.com/tysitv/uk-sponsored-jobs/commits/main> tells you at a
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
