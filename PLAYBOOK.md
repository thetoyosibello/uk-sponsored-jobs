# Playbook: UK visa-sponsored job sweep

This file is the single source of truth for the daily routine. Edit this file to
change what the routine looks for. The routine prompt itself does nothing except
tell the agent to read and follow this playbook.

---

## 1. Mission

Twice a day, find **genuinely sponsorable** UK job vacancies for two people, verify
them, score them, and append them to `hr.csv` and `other.csv` in this repo. Those
two files feed a live Google Sheet through `IMPORTDATA`.

- `hr.csv` — HR / People roles, for **D**
- `other.csv` — everything else, for **T**

Two files, two tabs. Never create a third.

---

## 2. The rules that decide everything (UK, verified 13 Aug 2026)

Most "visa sponsorship" job listings on the internet are no longer sponsorable.
Since **22 July 2025** the Skilled Worker route changed, and the filter below is
the whole reason this routine exists. Apply it before anything else.

1. **Skill level.** For a new Skilled Worker application the job must normally sit
   at **RQF level 6** (degree level) — gov.uk labels these occupation codes
   **"Higher Skilled"**. Codes labelled **"Medium Skilled"** (RQF 3–5) only
   qualify if the occupation is on the **Temporary Shortage List** (in force
   until 31 December 2026) or the applicant has transitional protection.
2. **Salary.** The general threshold is **£41,700** *or* the occupation's **going
   rate**, whichever is higher. Lower "new entrant" rates can apply — typically
   for applicants switching from a Student or Graduate visa, or under 26. Where a
   listing's salary clears the new-entrant rate but not the standard rate, keep it
   and say so in the `Why it fits` column.
3. **The employer must actually hold a licence.** Check the gov.uk register (§5).
   A licence means the employer *can* sponsor, never that they *will*.

Occupation codes that matter here (standard rate / new-entrant rate):

| Code | Occupation | Level | Going rate |
|---|---|---|---|
| 1136 | Human resource managers and directors | Higher | £52,900 / £41,200 |
| 3571 | Human resources and industrial relations officers | **Medium** | £33,400 / £27,100 |
| 1132 | Marketing, sales and advertising directors | Higher | £87,300 / £60,000 |
| 2432 | Marketing and commercial managers | Higher | check page |
| 1133 | Public relations and communications directors | Higher | check page |
| 2493 | Public relations professionals | Higher | check page |
| 2431 | Management consultants and business analysts | Higher | £50,200 / £36,000 |
| 2440 | Business and financial project management professionals | Higher | £56,500 / £43,300 |
| 2434 | Business and related research professionals | Higher | £38,800 / £31,500 |
| 2412 | Solicitors and lawyers | Higher | £51,600 / £39,000 |
| 2419 | Legal professionals n.e.c. | Higher | check page |
| 3554 | Advertising and marketing associate professionals | **Medium** | £33,400 / £26,300 |
| 3520 | Legal associate professionals | **Medium** | £33,400 / £26,400 |

Authoritative pages, re-check if a rate looks wrong:
- Going rates: <https://www.gov.uk/government/publications/skilled-worker-visa-going-rates-for-eligible-occupations/skilled-worker-visa-going-rates-for-eligible-occupation-codes>
- Eligible occupations and skill level: <https://www.gov.uk/government/publications/skilled-worker-visa-eligible-occupations/skilled-worker-visa-eligible-occupations-and-codes>

**Medium-skilled roles are not banned from the sheet** — HR Officer and Marketing
Executive are exactly the jobs these two are qualified for today. Include them,
but set `Skill level` to `Medium — TSL/transitional only` so the risk is visible
rather than hidden. Never present a medium-skilled role as straightforwardly
sponsorable.

---

## 3. Who the jobs are for

### D — the `hr.csv` tab

**Adebola (D)**, UK, needs Skilled Worker sponsorship. **MSc International Human
Resources Management (Merit, 2024)**, on top of an **LLB (2:1)** and
**Barrister-at-Law**. Currently **Policy Advisor (shadowing) at Companies House,
Cardiff** (Mar 2025 to present): auditing people and recruitment policy against
UK employment legislation, maintaining right-to-work records, equality impact
assessments. Before that **HR Advisor at Augustsons LLP** (Nov 2022 to Jan 2024)
and **HR Generalist at Charles Anthony LLP** (Sep 2020 to Nov 2022), both
professional-services firms: employment contracts, onboarding, right-to-work and
ID verification, internal compliance audits, HRIS clean-up (100% audit
compliance, 30% efficiency gain, 18% turnover reduction).

Certified in **CIPD HR-Inform Right to Work Checks**, **UK Compliance (GDPR, AML,
KYC)** and **Business Analysis**.

**The differentiator is HR plus compliance plus law.** D is not a generalist
people person — they are a governance, audit and right-to-work specialist who
happens to sit in HR, with a barrister's training behind it. Rank accordingly:
a People Operations Manager role at a regulated employer, or an HR compliance,
recruitment-governance or workforce-audit role, beats a generic HR Manager
opening every time. Regulated public sector, NHS, financial services and law
firms are the natural homes. There is an irony worth using in `Why it fits`:
right-to-work compliance is literally D's specialism.

- **Primary targets (Higher Skilled, code 1136):** HR Manager, People Operations
  Manager, HR Compliance Manager, Recruitment Operations Manager, Talent
  Acquisition Manager, HR Governance / Workforce Compliance Manager, HR Business
  Partner, Head of People Operations.
- **Adjacent Higher-Skilled, genuinely strong for D:** people analytics and
  workforce reporting (2434); HRIS / HR transformation project and programme
  roles (2440); employment-compliance and policy roles where the law degree
  counts (2419); org-design and HR consulting (2431).
- **Secondary (Medium, code 3571, always flag the risk):** HR Advisor, HR
  Officer, People Advisor, HR Compliance Officer, Recruitment Coordinator, HR
  Generalist.
- **The honest gap.** D's current level is Advisor/Officer, which is exactly the
  Medium-skilled band that stopped being sponsorable in July 2025. Manager-level
  titles are a step up from where D sits today, and they are also the only band
  that reliably qualifies. So keep stretching upward — but when a manager role
  clearly wants five years of managing a team, say so plainly in `Why it fits`
  rather than scoring it 5.
- Location: anywhere in the UK. **Cardiff, Wales and remote deserve a specific
  look** since D is at Companies House in Cardiff, but do not restrict to it —
  London and the big regional centres carry far more sponsored HR roles.

**NHS: yes, sweep it every run — it is one of the best HR targets available.**
Confirmed 13 Aug 2026. NHS trusts are licensed sponsors in large numbers, and
**Band 7 and above** non-clinical roles are generally sponsorable. Two things to
get right: HR is **non-clinical**, so it goes through the *standard* Skilled
Worker route, not the Health and Care Worker sub-route — no reduced visa fee, no
Immigration Health Surcharge exemption, and the full £41,700-or-going-rate test
applies. And band maps to salary: Band 7 (roughly £47k–£54k) clears the general
threshold and the 1136 new-entrant rate, Band 8a and above clears the £52,900
standard rate comfortably. Band 6 and below usually fails on both skill and
salary. Search `jobs.nhs.uk` and `apps.trac.jobs`, and individual trust careers
sites, for `HR Business Partner`, `People Partner`, `Workforce Manager`,
`Employee Relations Manager`, `Head of People`. Put the band in `Why it fits`.

**Civil Service: include only when the advert explicitly says so.** Confirmed
13 Aug 2026, and it is the mirror image of the NHS. Civil Service nationality
rules bar many posts outright, anything needing security clearance or British
citizenship cannot be sponsored at all, and entry-level and administrative posts
are very unlikely to sponsor given the domestic applicant pool. Some departments
do sponsor specialist roles, so it is not a blanket no — but **never infer it**.
Unless the listing on `civilservicejobs.service.gov.uk` states that applicants
requiring sponsorship may apply, do not add the row. When one does qualify, say
in `Why it fits` that the advert states sponsorship explicitly.

**Manager-first is the standing instruction** (confirmed by the user,
13 Aug 2026). Sweep both bands, but lead every run with the manager-level titles
and spend your search budget there. Officer and Advisor roles go in the sheet
too, always with `Skill level` set to `Medium — TSL/transitional only`, and they
can never outrank a manager-level role of comparable quality. If a run is going
to be short, cut the Officer-level searching, not the manager-level searching.

> **Tuning note:** this profile is still generic HR — D's CV was not available
> when the routine was built, and nothing HR-related exists on the user's disk or
> in their Drive. Replace this section with D's actual seniority, years of
> experience, CIPD level, sector and location and the fit scores get much
> sharper.

### T — the `other.csv` tab

Toyosi (T), London. LLB (2020) plus **LLM International Commercial Law,
Distinction** (Northumbria, 2024). Currently holds three overlapping roles:
Legal Assistant at a property group (commercial contracts, corporate compliance,
statutory registers, Companies Act filings), Marketing Associate at a studio
(campaign execution, lead generation, social), and a resident-services role.
Earlier: content strategist and producer at a university, social media and
marketing assistant. Also worked as an **AI trainer** and builds AI content and
marketing automation (n8n, Vapi, Airtable, HubSpot, Google Analytics, Meta Ads,
Google Ads); built and led an AI voice-agent capstone project.

The differentiator is the **intersection**: commercial-law literacy + marketing
execution + practical AI automation. Roles that need two of those three rank
highest.

- **Primary targets (Higher Skilled):** Marketing Manager, Digital Marketing
  Manager, Marketing and Commercial Manager (2432); Communications Manager, PR
  Professional (2493, 1133); Business Analyst, Management Consultant (2431);
  Project / Programme Manager, Delivery Manager (2440); Compliance Officer,
  Contracts Manager, Legal Counsel, Company Secretarial, Legal Operations,
  Legal-tech / contract-automation roles (2419, 2412); Research and insight
  roles (2434); Marketing Operations, Revenue Operations, CRM Manager,
  Content Strategy Manager, AI content / automation specialist roles.
- **Secondary (Medium, flag the risk):** Marketing Executive, Digital Marketing
  Executive, Content Marketing Executive (3554); Paralegal, Legal Assistant,
  Contracts Administrator (3520).
- **Do not include:** care assistant, support worker, hospitality, front of
  house, concierge, retail, warehouse, driving, kitchen. T has CVs for these but
  they are RQF 2–3, sit outside the eligible occupation list entirely, and are
  not sponsorable for a new application. Adding them wastes the sheet.
- Location: London and remote/hybrid UK first. Include strong roles elsewhere in
  the UK but say so in `Why it fits`.

---

## 4. Daily procedure

Work through this in order.

> ### Write early, write often — this is the most important rule here
>
> A run that searches beautifully for fifteen minutes and commits nothing is a
> **failed run**. It happened on 13 Aug 2026: the sweep ran twelve minutes of
> excellent searching, verified employers against the register, and produced an
> empty sheet, because it was saving all the writing for the end.
>
> So:
>
> - **Hard budget: about 20 searches.** When you hit that, stop searching. Not
>   "one more angle" — stop, and write up what you already have.
> - **Append and commit in batches as you go**, roughly every 3–5 rows you
>   score. Do not hold rows in your head until the end. Each commit is safe on
>   its own, and a run cut short still leaves the user better off than before.
> - **The first commit should happen within the first third of the run.** If you
>   have gone a long way with nothing committed, that is the signal to stop
>   searching and start writing.
> - Rows that are good enough beat rows that are perfect and unwritten. If a
>   salary or closing date is unknown, write `Not stated` and move on rather
>   than running three more searches to pin it down.

1. **Read the current state.** Read `hr.csv` and `other.csv`. Collect every value
   already in the `Link` column into a set — that is your dedupe key.
2. **Search — and run both strategies, not just the obvious one.**

   **Strategy A, keyword-led (the obvious one, and the weaker one).** Search the
   role titles in §3 together with explicit *visa* wording: `"visa sponsorship"`,
   `"skilled worker visa"`, `"Certificate of Sponsorship"`, `"we sponsor visas"`,
   `"sponsorship available"`. This is what everyone does, and it mostly surfaces
   care, trades and hospitality spam that fails §2 anyway.

   **Strategy B, register-led (do this every run, it finds the better roles).**
   Most UK employers who sponsor never say so in the advert, so keyword search
   cannot see them. Instead work backwards: pull employers from the sponsor
   register that hold a **Skilled Worker** licence in the right sectors, then
   search those named employers for the degree-level roles in §3 —
   `"<employer>" careers HR business partner`, or go straight to their ATS.
   A licensed employer advertising a Higher-Skilled role is a far stronger lead
   than an unlicensed one that merely used the word "sponsorship".

   Rotate the role titles and the employers you lead with between runs so the
   sweep does not keep re-finding the same corner of the market.
3. **Filter hard.** Drop anything that is: a duplicate link, already in the CSV,
   a role clearly outside §3, closed or expired, a training course rather than a
   job, based outside the UK, or a "sponsorship considered for exceptional
   candidates" tease with no substance.

   **Contract type is a hard filter, not a detail.** A sponsor licence is no use
   if the engagement itself cannot carry a visa. Reject outright:

   - **day-rate, hourly-paid, temp, interim and "bank" roles** — an advert
     quoting `£25–£30 per hour` or `£180 per day` is a temp booking, and the NHS
     "bank" is casual shift work. None of these sponsor.
   - **agency-supplied temp assignments**, where the agency is the payer.
   - **anything under 12 months.** A fixed-term contract *can* be sponsored, but
     the Certificate of Sponsorship only runs to the end of the contract, so a
     6-month FTC buys 6 months of visa. Not worth an application.

   Keep **permanent** roles, and **fixed-term of 12 months or more** — for the
   latter, put the length in `Why it fits` so the reader can judge it.

   The advert usually states this plainly once you can actually read the page.
   NHS Jobs prints `Position Type: Permanent`; most ATS pages carry an
   employment-type field. This is another reason `fetch-page.sh` matters: a
   search snippet almost never tells you whether a role is permanent, and salary
   quoted per hour or per day is the giveaway that it is not.

   **Recruitment-agency listings** (Reed, Hays, Michael Page, Morgan Law,
   Huntress, Lloyd Recruitment and the rest) need their own rule, because on a
   keyword search they are most of what comes back. The end employer is hidden,
   so the register cannot be checked and the sponsor is unknown. Do not drop
   them outright — that threw away every HR result in testing on 13 Aug 2026 —
   but only keep one when the role is **Higher Skilled** *and* the advertised
   salary clears the standard going rate. Record `Agency listing — employer
   unknown` in `Sponsor licence` and cap `Fit` at 3.
4. **Verify the employer** against the sponsor register (§5).
5. **Classify** each survivor: occupation code, skill level, salary versus
   threshold.
6. **Score fit** 1–5 (§6).
7. **Append** rows to the right CSV and commit (§7).
8. **Report** in your final message: how many candidates seen, how many kept,
   how many rejected and the main reasons, and anything that broke.

**Volume:** aim for **5–15 genuinely good new rows per run across both files**. If
a run finds only two that pass, append two. Never invent rows, never pad, never
lower the bar to hit a number. An empty run with an honest explanation is a
correct outcome.

---

## 5. Sources

Verified reachable on 13 Aug 2026. If one blocks you, move on rather than
retrying — note it in your final report.

> ### Read this before you touch the network
>
> **In the cloud sandbox, `WebSearch` is the only way out.** Verified by a live
> run on 13 Aug 2026: the egress proxy returned `EGRESS_BLOCKED` for *every*
> `WebFetch` attempted — `www.gov.uk`, `www.reed.co.uk`, `boards.greenhouse.io`,
> even `en.wikipedia.org` — and `curl` gets `403 CONNECT tunnel failed`. Only
> GitHub, npm and PyPI are reachable directly. This is a network policy, not a
> transient outage, so **do not burn a run rediscovering it**: try `WebFetch`
> once at most, and if it comes back `EGRESS_BLOCKED`, switch to the
> search-only mode below and say so in your report.
>
> **Search-only mode.** `WebSearch` still works and returns titles, URLs and
> snippets. That is enough to run this job properly, just with less detail:
>
> - Mine the **title and snippet** for role, employer, location and salary.
>   Search engines surface a lot of it — `"HR Business Partner - Acme - London -
>   £48,000"` is a complete row.
> - Run **several narrow searches** rather than one broad one, since you cannot
>   open a results page and page through it. Vary role title, city, and phrasing.
> - **Verify the employer against the register** — `register-skilled-worker.txt`
>   is in this repo and needs no network at all. In search-only mode this is your
>   strongest signal, so lean on it harder than usual.
> - Set `Source` to `WebSearch snippet (page not fetched)` so the user knows the
>   detail is unverified, and put anything you could not confirm — usually salary
>   and closing date — as `Not stated` rather than guessing.
> - Because you cannot read the advert, **you cannot confirm the employer says
>   they sponsor.** Do not claim they do. The register tells you they *can*.
>
> **Search-only mode does not write to `hr.csv` or `other.csv`. Ever.** Those two
> files feed the live sheet and, per §7, may only contain vacancies proven open
> — which needs a page fetch you cannot make. Write your finds to
> **`candidates.csv`** instead, same 13 columns, same append-and-dedupe rules.
> That file is not in the sheet; it is a queue.
>
> This is the division of labour, and each half plays to its strength: the cloud
> sweep can search but not read, so it **discovers**; the local sweep can read,
> so it **verifies and promotes**. A search-only run that adds ten solid
> candidates has done its job properly, even though the sheet does not move until
> the local sweep confirms them.
>
> If a future run finds `WebFetch` working, use it — richer and more reliable —
> and mention in the report that egress opened up, because it means the rest of
> this section is live again. To make that happen deliberately, the user can
> widen the allowed domains on the routine's environment at
> <https://claude.ai/code/routines>; gov.uk, reed.co.uk and the ATS hosts in §5
> are the ones worth allowing.

**Sponsor register (the gate).** The register ships **inside this repo**, already
filtered, so no network call is needed:

- `register-skilled-worker.txt` — 121,891 organisations licensed for the
  **Skilled Worker** route. This is the one that matters.
- `register-other-routes.txt` — 5,330 organisations licensed only for other
  routes (Global Business Mobility, Temporary Worker). Being in *this* file
  instead is a red flag, not a pass.

> **Why it is a file and not a download.** The cloud sandbox routes egress
> through a proxy that blocks `curl` to gov.uk — verified 13 Aug 2026, it returns
> HTTP 000. `WebFetch` and `WebSearch` work fine, but the register CSV is 10 MB,
> far too large to pull through them. Do not waste a run rediscovering this.

Check an employer case-insensitively:

```bash
grep -i "acme" register-skilled-worker.txt
grep -i "acme" register-other-routes.txt   # only if the first found nothing
```

Match on a distinctive fragment of the legal name, not the full string — register
names carry suffixes ("Acme Group Ltd" vs "Acme"). Trading names often differ from
the registered entity, so a miss is weak evidence, not proof. Record
`Yes — Skilled Worker`, `Licensed, other route only`, `Agency listing — employer
unknown`, or `Not found` in the `Sponsor licence` column. **Never drop a strong
role purely because the name did not match** — record `Not found` and let a human
judge.

**Keeping the register fresh.** It was extracted from the gov.uk publication dated
**2026-08-13**. gov.uk republishes it roughly weekly. Once a month, check the
publication date with
`WebFetch("https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers")`
and if the file here is more than about six weeks behind, say so in your run
report so a human can refresh it. Do not try to refresh it yourself — the
download is blocked from the sandbox.

**Job sources, in order of usefulness:**

1. **Company ATS pages, found through WebSearch** — the highest-quality source by
   a distance: named employer, real salary, current, and a stable link. Rotate
   ATS hosts (Greenhouse, Lever, Workable, Ashby, Teamtailor, Pinpoint):
   `site:boards.greenhouse.io UK "visa sponsorship" HR manager`,
   `site:apply.workable.com UK "skilled worker visa"`,
   `site:jobs.lever.co London "HR business partner"` then check the register.

   > **Never search the bare word "sponsorship" on job boards.** Verified
   > 13 Aug 2026: it returns *event and brand* sponsorship roles. A search for
   > London marketing roles with "sponsorship" returned Aera Technology
   > ("owns global sponsorship strategy") and Match Group ("leads brand
   > partnerships and sponsorships") — nothing to do with visas. Always say
   > **visa** sponsorship, or skilled worker visa.

   > And the mirror-image mistake: most UK ATS adverts say **nothing** about
   > visas even when the employer sponsors routinely. Silence is not a no. That
   > is precisely why Strategy B in §4 exists — check the employer against the
   > register rather than waiting for the advert to volunteer it.
2. **Reed** — real listings, but **read this carefully, the obvious URL is a
   trap**. Adding `?keywords=` to a role slug URL silently *replaces* the role:
   `/jobs/hr-manager-jobs-in-london?keywords=visa%20sponsorship` returns
   phlebotomists and care assistants, not HR. Verified 13 Aug 2026.
   Use the search endpoint and put everything in `keywords`:
   `https://www.reed.co.uk/jobs/search?keywords=hr+manager+visa+sponsorship&location=london`
   That form does return genuine HR roles (HR Business Partner, People Partner,
   Employee Relations Manager). Two known quirks: Reed intermittently serves a
   "your session has expired" shell that truncates results — retry once, then
   move on — and it sometimes misreads `location`, so always sanity-check that
   the locations coming back are real and in the UK.
   The plain slug URL with **no** query string also works when you want a whole
   role family: `https://www.reed.co.uk/jobs/hr-manager-jobs-in-london`.
3. **Glassdoor** has dedicated sponsorship listing pages that are worth trying,
   e.g. `https://www.glassdoor.co.uk/Job/london-visa-sponsorship-hr-manager-jobs-SRCH_IL.0,6_IC2671300_KO7,34.htm`.
   It often blocks automated fetches — one attempt, then move on.
   **ATS mechanics, all verified 13 Aug 2026 — these save whole runs:**

   - **A job ID from a search result is usually dead.** Search indexes lag badly.
     Both ATS links tested went nowhere: a Capco job ID redirected to the board
     index, and a Figma one bounced to `?error=true` and then to their careers
     homepage. **A redirect to a board index, a careers homepage, or an `error`
     parameter means the vacancy is gone.** Never write that row — you would be
     sending someone to a job that no longer exists.
   - **Greenhouse changed host.** `boards.greenhouse.io/...` now 301s to
     `job-boards.greenhouse.io/...`. Go straight to the new host.
   - **Fetch the board index, not the job ID.** `job-boards.greenhouse.io/<company>`
     lists what is genuinely open right now, so it cannot be stale. Use search to
     find *which licensed employers to look at*, then read their board directly.
   - **Lever blocks automated fetches** — both job pages and board indexes return
     403. You can still see Lever roles in WebSearch snippets; you just cannot
     open them. Treat a Lever hit as a lead to verify elsewhere, not a row.

4. **Company careers pages** of employers you can see on the register in the
   right sector — go direct when a search surfaces a promising employer. This is
   the natural partner to Strategy B in §4 and, given how stale ATS search hits
   are, often the fastest route to a row you can actually trust.
5. **CV-Library, Totaljobs, Jobserve, Otta** — try them; they sometimes block
   automated fetches. Do not spend more than one attempt each.

**Known dead ends, do not waste calls (all verified 13 Aug 2026):**
`findajob.dwp.gov.uk` returns 503 to automated fetches. `tarve.co.uk` shows
*fabricated* sample listings on its landing page (Revolut, DeepMind, Monzo roles
that do not exist) and hides any real board behind a login — never take rows from
it. `myvisajobs.co.uk` has useful occupation-code reference pages but **no live
vacancies**. LinkedIn and Indeed block automated access.

**What the generic "visa sponsorship" keyword pool actually contains.** Verified
on Reed, 13 Aug 2026: of the first 25 results, the overwhelming majority were
care assistants, support workers, phlebotomists, trades operatives and two
Australia-based roles. Almost none were degree-level, and almost none were
sponsorable under the 2025 rules. **Expect to reject most of what you find.** A
run that looks at 60 listings and keeps 6 is working correctly, not failing.

---

## 6. Fit scoring

| Score | Meaning |
|---|---|
| 5 | Higher Skilled code, salary clears the standard going rate, employer licensed for Skilled Worker, and the role matches the person's actual experience. Apply today. |
| 4 | Higher Skilled and licensed, but one soft gap — salary only clears the new-entrant rate, or the role stretches their experience by a level. |
| 3 | Worth a look with a real caveat — employer not found on the register, or a Medium-skilled role they are well qualified for. |
| 2 | Long shot. Sponsorship wording is vague, or the fit is thin. |
| 1 | Do not use. If you scored it 1, do not append it. |

`Why it fits` must be one specific sentence naming the actual overlap and the
actual risk. "Good match for their background" is useless. Write like:
`Contract review + Companies Act filings map to her legal-assistant work; salary
£44k clears the standard rate; employer licensed for Skilled Worker.`

---

## 7. Writing the results

> ### Newest at the top, and nothing is ever deleted
>
> **Insert new rows directly beneath the header**, so the freshest jobs are the
> first thing the reader sees. Do not append to the bottom.
>
> **Never delete a row.** When a vacancy closes, its row stays and its `Status`
> changes. The user wants the history kept — a closed job they already applied
> to, or decided against, is still worth having a record of.

> ### `Status` is the first column, and you keep it honest
>
> A closed job presented as open is the worst failure this system has: it wastes
> the reader's time and makes them distrust every other row. Verified 14 Aug
> 2026 — the sheet's highest-scoring row, a Band 8a NHS Employee Relations
> Manager, had already closed.
>
> `Status` takes exactly one of:
>
> - `Live` — you fetched the advert this run and it is open and accepting
>   applications.
> - `Closed YYYY-MM-DD` — you fetched it and it is closed, expired, gone, or it
>   redirects to a board index or careers homepage. The date is the day you found
>   it closed.
> - `Unverified` — you could not fetch the page, so you genuinely do not know.
>   Honest, and far better than guessing `Live`.
>
> **1. Prove a job is open before you write it.** A search snippet is evidence a
> job once existed, never that it is open today. If you cannot fetch the page,
> the row is `Unverified` — and in search-only mode it does not belong in these
> files at all, it goes to `candidates.csv`.
>
> **2. Re-check existing rows every run.** Before searching, walk the rows that
> are currently `Live`, fetch each `Link`, and flip any that have closed to
> `Closed <today>`. Rows already marked `Closed` are settled — do not re-fetch
> them, that is wasted budget. If the run is tight, re-check oldest `Found` first
> and say which ones you did not reach.
>
> Changing a row's `Status` is the **only** edit you may make to an existing row.
> Everything else about it stays exactly as written.

Columns, in order — **14 of them, `Status` first**:

`Status,Found,Role,Employer,Location,Salary,SOC,Skill level,Sponsor licence,Fit,Why it fits,Closes,Link,Source`

- `Status` — `Live`, `Closed YYYY-MM-DD`, or `Unverified`. See the box above.
- `Found` — the date you first added it, `YYYY-MM-DD`. This never changes, even
  when `Status` does.
- `Salary` — as advertised. If absent, write `Not stated`, and be aware that an
  unstated salary is itself a risk on a sponsored role.
- `Skill level` — `Higher` or `Medium — TSL/transitional only`.
- `Fit` — the number only.
- `Closes` — closing date if shown, else `Not stated`.
- `Link` — the direct job URL. This is the dedupe key, so keep it clean: strip
  tracking parameters (`utm_*`, `?src=`, `&ref=`).

CSV hygiene: quote any field containing a comma, and never put a newline inside a
field. Verify the file still parses before committing:

```bash
python3 -c "import csv;rows=list(csv.reader(open('hr.csv')));print(len(rows),{len(r) for r in rows})  # expect {14}"
```

Every row must have 14 fields. Then commit and push — **always pull first**:

```bash
git add hr.csv other.csv
git commit -m "Job sweep $(date -u +%Y-%m-%d\ %H:%M) UTC"
git pull --rebase origin main
git push
```

> **Why the pull matters.** Two different sweeps write to these files: the cloud
> routine and the local one on the user's Mac (see `LOCAL.md`). Whichever pushes
> second will be rejected without a rebase first, and a rejected push means the
> sheet silently stops updating. If the rebase hits a conflict, it will be in the
> appended rows — keep **both** sides, since they are different jobs, then
> re-run the 14-field check before pushing.

If the push fails, say so loudly in your final message with the exact error —
a silent push failure means the sheet quietly stops updating, which is the worst
possible failure mode for this system.

---

## 8. Standing rules

- Report honestly. If a source blocked you, if the register download failed, if a
  run found nothing — say it plainly. Do not paper over a bad run.
- Never fabricate a vacancy, an employer, a salary or a link. Every row must
  come from a page you actually fetched.
- Never apply to anything, never send a message, never fill in a form. This
  routine only ever reads, and writes to these two CSV files.
- A licence on the register means the employer *can* sponsor. It never means
  they will sponsor this role, for this person, at this salary.
