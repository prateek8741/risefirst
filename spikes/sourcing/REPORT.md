# Sourcing spike — Step 1 results (employer job boards, no API keys)

Date: 2026-11-17 · Code: `probe.py` (discovery), `classify.py` (rules) · Raw data: not committed

## Question

How many **fresher / entry-level jobs in India** can we collect from public, permitted
applicant-tracking-system (ATS) job-board APIs, the employers' own boards?

## Method

1. 418 candidate company slugs (Indian startups, analytics/services firms, global
   companies with India offices; `candidates.py`), each probed on 5 ATSs: Greenhouse,
   Lever, Ashby, Workable, Recruitee. Rate limits per host followed robots.txt (Lever 1 req/s).
2. India filter on location text (country + about 40 Indian cities).
3. Deterministic eligibility rules, a simplified version of proposal §8.5, with no LLM:
   - **ELIGIBLE:** intern / trainee / graduate / apprentice / "pass-out 2026" titles; stated
     experience with minimum ≤ 1 and maximum ≤ 3 years; "freshers" mentioned.
   - **REJECTED:** senior / lead / staff / principal / II+ titles, or ≥ 3 years required.
   - **REVIEW:** 2+ years (borderline), junior title with no stated experience, or a
     "Manager" title with ≤ 2 years stated.
   - **UNKNOWN:** neutral title and no experience stated. These would be REVIEW_REQUIRED
     in the real system.

## Results

| ATS | Boards found | All postings | India postings | Eligible | Review | Unknown | Rejected |
|---|---|---|---|---|---|---|---|
| Greenhouse | 79 | 11,935 | 1,042 | 15 | 69 | 68 | 890 |
| Lever | 14 | 549 | 352 | 22 | 37 | 42 | 251 |
| Ashby | 20 | 2,917 | 130 | 1 | 9 | 32 | 88 |
| Recruitee | 2 | 6 | 0 | 0 | 0 | 0 | 0 |
| Workable | 0 | — | — | — | — | — | — |
| **Total** | **115** (74 with India jobs) | 15,407 | **1,524** | **38** | **115** | **142** | **1,229** |

- **Auto-eligible rate: 2.5% of India postings.** If roughly a third of the REVIEW items pass
  review, the realistic publishable count from these 74 boards is **about 60–90 jobs**.
- **Precision check:** about 35 of the 38 eligible are clearly fresher roles when checked by
  hand (internships, trainee programmes, "0–2 years", associate roles). The rest are
  borderline 1–3-year roles.
- **Domains of eligible jobs:** HR 8, Software/IT 8, Sales/Marketing 4, Operations 4,
  Finance 2, Data/AI 1, Product 1, other 10. Not only tech, but thin everywhere.
- **Concentration:** Paytm alone gives 13 of 38. 15 boards have any eligible job at all.
- **Ten of the boards found** (e.g. Rubrik, Stripe, Paytm, Mindtickle, Hevo, CRED, FamPay,
  Sigmoid, Celonis, Meesho) cover most of the fresher roles. See `results/boards_with_india_jobs.csv`.

## Correction to my earlier estimate

I had estimated **300–500 fresher jobs from about 300 companies**. The measurement says that
was too optimistic:

- Only **18% of guessed companies** (74/418) have a public board with India jobs. Most large
  Indian employers (IT services, banks, BPO, retail, consumer apps such as Swiggy and Zomato)
  use Workday, SuccessFactors, Taleo, Darwinbox or their own portals, not public APIs.
- Each India board yields about **0.5 auto-eligible jobs** (about 1–2 including review), not 1–2 eligible.
- Companies with public ATS APIs are mostly **global tech firms and funded startups whose India
  offices hire experienced people**. The big fresher hirers aren't on these systems.

**Conclusion: employer ATS boards realistically give about 60–150 publishable fresher jobs**
(150 assumes the company list grows to about 150 India boards). That is valuable as
high-quality listings, with full descriptions, direct apply links and reliable closure
detection, but **it cannot reach 200 alone**. The aggregator APIs (Adzuna, Jooble, Careerjet) are
required, so getting those keys is the next blocker.

## Compliance notes found during the spike

- **Lever** (`jobs.lever.co`) content signals: `search=yes, ai-train=no, use=reference`.
  AI input isn't stated. → For Lever-sourced jobs, show **an excerpt plus a link to the
  original** rather than the full description. LLM tagging of the text should be confirmed
  as acceptable, or we could tag from title and metadata only.
- **Workable** (`apply.workable.com`): `search=yes, ai-input=yes, ai-train=no`, nothing disallowed.
- **Ashby:** the documented posting API is on `api.ashbyhq.com` (no robots.txt). The separate
  `jobs.ashbyhq.com` host disallows `/api/`, which we don't use.
- **SmartRecruiters:** excluded (robots `Disallow: /` for all agents but LinkedInBot).
- No ATS model is used for AI training. All signals allow our use for search and tagging,
  except the Lever AI-input point above.

## Open items

- **Workable is inconclusive.** 131 slugs resolve to accounts, but neither the widget endpoint
  nor the careers endpoint returned jobs, even for companies that are hiring. 222 requests got
  HTTP 429 at 2 req/s. This needs a slower re-probe against a known-active account
  before we include or drop it.
- 4 Lever requests timed out (Myntra, Pine Labs, LatentView, Sigmoid on Lever); not retried.
- **Slug collisions:** a resolving slug isn't proof of identity. Each board must be
  checked by hand before it goes into `config/sources.yaml`.

## Next step

Measure the aggregator APIs with the same rules once keys are available:
**Adzuna** (free self-serve), **Jooble** (key on request), **Careerjet** (affiliate ID).
