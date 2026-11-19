# RiseFirst

Fresher jobs and internships in India, collected daily from employers' own job boards.

RiseFirst reads the public job-board APIs that companies publish through their hiring
systems (Greenhouse, Lever, Ashby). It keeps only jobs located in India and decides which
ones suit freshers (0–1 years of experience). It can use Gemini to tag jobs, then serves
them through a FastAPI backend and a Next.js website with search and filters.

```
config/sources.yaml ──► connectors ──► India filter ──► eligibility rules ──► (Gemini) ──► PostgreSQL
  74 employer boards    Greenhouse      city gazetteer    experience parser    only for         │
                        Lever, Ashby                      title rules          unclear jobs     ▼
                                                                                        FastAPI /api/*
                                                                                              │
                                                                                        Next.js site
```

---

## Quick start (Docker)

You need Docker Desktop.

```bash
cp .env.example .env          # optional: set GEMINI_API_KEY to turn on AI tagging
docker compose up --build
```

| What | Where |
|---|---|
| Website | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Postgres | `localhost:5433`, user, password and database all `risefirst` |

On start, the `worker` container runs one full ingestion (about 1–2 minutes without AI), then
repeats it every day at 06:00 IST. The site shows jobs as soon as the first run finishes.
Refresh the page after a minute or two.

## Local development (without Docker)

You need Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20+ and a local PostgreSQL.

```bash
# Backend
cd backend
createdb risefirst
uv sync
uv run risefirst migrate                 # create tables
uv run risefirst ingest                  # fetch all 74 boards once (add --no-ai for rules only)
uv run risefirst stats
uv run uvicorn risefirst.entrypoints.api.main:app --reload --port 8000

# Website (second terminal)
cd web
npm install
npm run dev                              # http://localhost:3000, expects the API on :8000
```

Configuration comes from environment variables or `backend/.env`. See `.env.example`.

### CLI

| Command | Does |
|---|---|
| `risefirst migrate` | Apply database migrations (Alembic) |
| `risefirst ingest [--source stripe] [--no-ai]` | One refresh run over all (or one) sources. Prints the run report |
| `risefirst schedule` | Runs ingest now and then daily at `REFRESH_HOUR_IST` (the worker container) |
| `risefirst stats` | What the site currently publishes |

---

## Architecture

Clean architecture, kept light. Dependencies point inward only:
`entrypoints → application → domain`, and `infrastructure` implements the application's ports.

```
backend/src/risefirst/
├── domain/              Pure Python rules. No framework imports.
│   ├── experience.py      "0-2 years", "2+ yrs", "minimum 3 years", "freshers welcome" parser
│   ├── eligibility.py     ELIGIBLE / REVIEW_REQUIRED / REJECTED rules and how AI may adjust them
│   ├── location.py        India detection, city aliases (Bangalore→Bengaluru, Gurgaon→Delhi NCR), work mode
│   ├── classification.py  category and employment type from the title
│   ├── identity.py        duplicate fingerprints, content hashes, slugs
│   └── job_builder.py     RawPosting (+ AI output) → Job
├── application/         Use cases and ports (typing.Protocol)
│   ├── ports.py           SourceConnector, Enricher, JobRepository
│   ├── ingest.py          IngestJobs: fetch → filter → classify → enrich → save → close missing
│   └── catalog.py         JobCatalog: search, detail, facets, stats for the public API
├── infrastructure/      Adapters
│   ├── http.py            host allowlist, per-host rate limits, retries with backoff
│   ├── connectors/        Greenhouse, Lever, Ashby parsers and the source registry
│   ├── llm/gemini.py      Gemini enricher (structured JSON output), the only file importing the Google SDK
│   └── persistence/       SQLAlchemy tables and the PostgreSQL repository
├── entrypoints/         FastAPI app (api/) and Typer CLI (cli.py)
└── composition.py       wires the concrete adapters together (the only place that does)
```

Why this shape: the domain rules decide what users see, so they are pure functions with
fast unit tests. Every port has a real second implementation in the tests (in-memory
repository, fake connectors, fake enricher), so the whole ingestion flow is tested without
network or database. Swapping Gemini for another model means writing one new adapter file.

### Data flow of one ingestion run

1. Load `config/sources.yaml` (the reviewed list of 74 employer boards) and build one connector per board.
2. Fetch each board. **A failing board is logged and skipped.** It never stops the run, and
   its jobs are not closed.
3. Keep postings located in India (city gazetteer plus the word "India". The bare code "IN" is not used, because it also means Indiana).
4. **Rules first:** parse experience from the description and apply the title rules.
5. **AI only where it helps:** jobs the rules rejected never reach Gemini. Jobs whose text
   hasn't changed reuse the stored AI result. A per-run call budget caps cost. Calls are
   spaced to `AI_REQUESTS_PER_MINUTE`. "Busy" (503) and per-minute (429) errors are retried,
   following Google's retry hint. When the daily quota is used up, AI pauses for the rest of
   the run (the job is still saved on rules alone) and the job is retried on the next run.
6. Upsert by `source_key` (`ats:board:job_id`). `first_seen_at` is preserved.
7. Jobs missing from a board for **2 consecutive successful runs** are closed. A job that
   reappears is reopened.
8. Duplicates (same company + normalised title + cities) collapse to one listing.
9. Save the run report (counts per stage, AI calls, failures) to `ingestion_runs`.

### Fresher eligibility

| Situation | Result |
|---|---|
| Senior / lead / staff / principal / director / "II"+ title | Rejected |
| Asks for 3+ years | Rejected |
| Intern, trainee, apprentice, graduate, new grad, campus title | Eligible |
| Asks for 0–1 years minimum (and at most 3 maximum) | Eligible |
| Says "freshers" or "recent graduates", no years stated | Eligible |
| Asks for 2 years, or experience not stated | Needs review (hidden by default) |

**What Gemini can change:** it can move a *needs review* job to eligible (or rejected), and
only when its confidence is at least 0.7. It can flag an eligible job for review when it
confidently disagrees. **It can never un-reject a job.** Every job shows why it is listed
and whether rules or AI made the call.

**Prompt-injection safety:** job descriptions are untrusted. They go inside `<posting>`
delimiters under a fixed system instruction. The model has no tools and must return a fixed
JSON schema, which is validated again on our side. The worst a malicious posting can do is
produce wrong field values, and the rules above limit what those can change.

### Database (PostgreSQL)

- `jobs`: one row per source posting. Fields: identity (`source_key` unique, `fingerprint`
  for duplicates), display fields, classification (`eligibility`, `eligibility_reason`,
  `classified_by`), lifecycle (`status`, `first_seen_at`, `last_seen_at`, `missed_runs`),
  the stored AI output (`enrichment` JSONB) and `duplicate_of`.
  - Full-text search: a generated `tsvector` column, weighted title/company > skills >
    summary > description, with a GIN index. Partial words fall back to `ILIKE` on title
    and company.
  - GIN index on `cities` (text array) for city filters. A composite index on
    `(status, eligibility, posted_at)` for the listing.
- `ingestion_runs`: one row per run, with the run report as JSONB.

Migrations live in `backend/migrations` (Alembic).

### API

| Endpoint | Returns |
|---|---|
| `GET /api/jobs?q=&category=&city=&employment_type=&work_mode=&include_review=&page=&page_size=` | Paginated jobs. Verified fresher jobs come first, then the newest |
| `GET /api/jobs/{id}` | Full job, including description, apply link and why it is listed. 404 if closed or rejected |
| `GET /api/facets` | Counts per category, city, type and work mode (for the filters) |
| `GET /api/stats` | Published job count, companies, last refresh time |
| `GET /api/health` | Liveness |

Inputs are validated (enums, length limits, `page_size ≤ 50`). The API is read-only (`GET` only, CORS restricted).

### Website

Next.js 15 (App Router, TypeScript, Tailwind), rendered on the server so pages are indexable.

- **Home:** search box, filters (category, city, type, work mode), an "include unclear
  experience" toggle and pagination. Filters live in the URL, so searches can be shared.
  The form works without JavaScript.
- **Job page:** facts, skills, full description, an "Apply on the company's site" button,
  why it's listed and when it was last checked. Includes schema.org `JobPosting` JSON-LD for Google.
- **How it works:** sources, eligibility rules and removal requests.
- Descriptions are rendered as plain text, never as HTML, so injected markup can't run.

---

## Sources and compliance

- **Included:** only official public job-board APIs that employers publish through their
  ATS. They need no login or key. Each host's robots.txt was checked (2026-11-17): Greenhouse
  disallows only `/embed/`, Lever allows `/` with `Crawl-delay: 1` (we wait 1 s between
  requests), and Ashby documents a public posting API.
- **Excluded:** LinkedIn, Naukri, Indeed, Internshala, Glassdoor and Foundit, whose terms
  forbid scraping. SmartRecruiters is also excluded (robots.txt `Disallow: /`).
- The HTTP client refuses any host not on its allowlist. This prevents SSRF from a bad
  config value and records exactly where data comes from.
- Every listing links to and credits the employer's page, and the site explains how to
  request removal.

## Current numbers (measured 2026-11-19, rules only, no AI)

| Stage | Count |
|---|---|
| Boards fetched | 74 / 74 |
| Postings fetched | 11,848 |
| Located in India | 1,527 |
| **Published as fresher roles** | **40** from 16 companies |
| Needs review (experience unclear) | 246 |
| Rejected (senior, or 3+ years) | 1,229 |

**Honest limitation:** the original goal was 200+ fresher listings. Employer job boards
alone don't reach it. The companies with public ATS APIs are mostly global tech firms and
funded startups whose India offices hire experienced people, while large fresher employers
(IT services, banks) use closed portals. The full measurement is in
[spikes/sourcing/REPORT.md](spikes/sourcing/REPORT.md).

Ways to raise the count, in order of impact:
1. **Turn on Gemini** (`GEMINI_API_KEY`). It reads the 246 "needs review" jobs and publishes
   those it judges fresher-friendly with confidence.
2. **Add an aggregator API** (Adzuna India, free key). A connector is one new file
   implementing `SourceConnector`.
3. **Grow `config/sources.yaml`.** Each new India board adds roughly 0.5–2 fresher jobs.

## Evaluation: accuracy and cost (2026-11-19)

50 posts were hand-checked from a frozen snapshot. The sample is stratified so AI decisions aren't
drowned out by easy rejections. Everything is in [eval/](eval/) and the sheet `eval/RiseFirst_eval.xlsx`.

| Metric | Result |
|---|---|
| Fresher decision (shown vs hidden), sample | **46/50 (92%)**, 95% CI 81–97% |
| Same, weighted to the real job mix | **98.5%** |
| Published list: genuine fresher roles | 18/20 in sample (≈95% weighted) |
| When AI made the final call | 14/17 |
| Category / work mode / city / experience | 88% / 88% / 98% / 94% |
| Cost per 1,000 posts the AI reads (Gemini 3.5 Flash-Lite, measured 1,079 in / 146 out tokens) | **$0.69** ($0.34 batch) |
| Cost per 1,000 India posts ingested (rules filter first, 19% reach AI) | **$0.13** |

Errors found: AI publishes some posts that state no years (2 of 8). The rules' city→onsite default
overrides "hybrid" (5 of 6 work-mode errors). Title-regex categories mislabel some posts ("Finance Content Creator").

Reproduce: `python eval/sample.py` → `eval/judgments.py` (verdicts) → `python eval/score.py` →
`eval/measure_tokens.py` (inside the worker container) → `uv run --project backend --with openpyxl python eval/build_sheet.py` (run from `eval/`).

## Tests

```bash
cd backend
uv run pytest            # 66 tests: domain, connectors (recorded payloads), ingestion, API, Gemini adapter, Postgres
uv run ruff check src tests migrations
cd ../web && npm run build   # type-checks and lints the site
```

The Postgres integration tests use `TEST_DATABASE_URL` (default
`postgresql+psycopg://localhost:5432/risefirst_test`) and are skipped if it can't be reached.
No test calls the network or Gemini.

## Decisions and trade-offs

| Decision | Why | Revisit when |
|---|---|---|
| FastAPI + server-rendered Next.js | Matches the requested stack, gives live search over Postgres, and runs with one command | — |
| Postgres full-text search, no Elasticsearch | Thousands of rows, not millions. One less system to run | More than about 100k jobs, or search relevance needs tuning |
| Rules first, AI second | Rules are free, explainable and testable. AI calls drop by about 80% (rejected jobs skip AI) | Rule precision drops on new sources |
| Gemini behind an `Enricher` port | Provider is swappable. Tests use a fake | — |
| In-container daily scheduler | No extra infrastructure for a local deployment | When deployed: use a platform cron (GitHub Actions, Cloud Scheduler) running `risefirst ingest` |
| Close after 2 missed runs | One miss can be a board glitch | — |

## Not built yet (next steps)

- Adzuna connector, to reach the 200+ listing target.
- Admin review screen for "needs review" jobs (the data and status already exist).
- Hosting: deploy the API and worker on a container platform, the site on Vercel, and the database on a managed Postgres such as Neon.
- Alerts when a run fails or the published count drops sharply (the run reports are already stored).
- Browser end-to-end tests (Playwright) and accessibility checks.
- Company logos (only where licensing is clear) and email job alerts.

## Repository layout

```
backend/            Python package, tests, Alembic migrations, Dockerfile
web/                Next.js site, Dockerfile
config/sources.yaml Reviewed list of employer boards
docs/               Architecture proposal (pre-build design notes)
spikes/sourcing/    The measurement that decided the source strategy
docker-compose.yml  db + api + worker + web
```
