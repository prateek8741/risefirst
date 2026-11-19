# Loom script (max 5 min, face + screen)

Times are targets. Talk to the points below; don't read them out. Have these open in tabs before you start:
http://localhost:3000, http://localhost:8000/docs, README.md (architecture diagram), the sheet, VS Code.

---

## 0:00 – 0:30 · What it is

**Screen:** http://localhost:3000

- "RiseFirst lists fresher jobs and internships in India, refreshed daily, straight from employers' own job boards."
- "Every listing says *why* it's listed and whether rules or AI made the call." Hover one **AI decision** badge.
- Open one job page and show the "Why it's listed" line and the Apply button, which goes to the employer's own page.

## 0:30 – 1:45 · Architecture

**Screen:** README diagram, then VS Code `backend/src/risefirst/`

- Pipeline: **74 employer boards (Greenhouse, Lever, Ashby) → India filter → rules → Gemini only for unclear jobs → Postgres → FastAPI → Next.js.**
- Sources: only official public ATS APIs. LinkedIn and Naukri are excluded because their terms forbid scraping. The HTTP client refuses any host not on an allowlist.
- **Rules first, AI second.** The rules decide 80% of jobs for free (senior title or 3+ years → reject; intern, trainee or 0–1 years → publish). Only the uncertain middle goes to Gemini.
- **AI has bounded power.** Gemini returns a fixed JSON schema that we validate again. It can settle a "needs review" job only at confidence ≥ 0.7, and it can never un-reject a job. Job text sits inside `<posting>` tags as untrusted data, so a prompt injection can only produce wrong field values, never actions.
- Clean architecture: `domain` holds pure rules, `application` holds use cases and ports, and `infrastructure` holds the Gemini, ATS and Postgres adapters. Swapping the model means writing one file, `llm/gemini.py`.
- Daily: the worker runs at 06:00 IST. Jobs whose text hasn't changed reuse the stored AI result, so a daily refresh costs almost nothing. Jobs missing for 2 runs are closed.

## 1:45 – 3:15 · What broke and how I fixed it

**Screen:** `docker compose logs worker`, then the `ingestion_runs` reports in the sheet ("Pipeline runs" tab)

1. **The free-tier quota killed the first AI run.** Run 2 made 297 Gemini calls and **287 failed**: `gemini-3.5-flash` allows 5 requests a minute and 20 a day. The run hammered the API with 4 threads and logged hundreds of errors.
   **Fix:** calls are paced to the per-minute limit. 429 and 503 errors retry after the wait Google suggests. When the daily quota runs out, AI pauses for the rest of the run, and the job is still saved on rules and retried tomorrow. Results are cached by content hash. Run 3 shows it working: 10 cache hits, one clean pause, 283 jobs deferred instead of failed. Then I moved to `gemini-3.5-flash-lite`, which has its own quota.
2. **"Busy" 503s from Gemini.** These are retried with backoff. The logs show them happening and recovering.
3. **"IN" means Indiana too.** The raw board data from the sourcing spike has US jobs at "Indianapolis, IN" (Samsara, Block and others), so matching the country code would publish American jobs. The filter uses a city gazetteer plus the word "India" instead, and a unit test keeps it that way.
4. **The site disagreed with itself.** While the worker ran, the header count and the list didn't match, because each part of the page cached API answers at a different moment. I turned off caching and added a test that the filter count equals the header count.
5. **The honest limitation:** public ATS boards give only about 2.5% fresher jobs, so 40 published, not 200+. I measured this before building (spikes/sourcing/REPORT.md) instead of padding with scraped data.

## 3:15 – 4:30 · Putting a number on it

**Screen:** the sheet, "Summary" then "Hand-check (50)"

- 50 posts, stratified so AI decisions aren't drowned out by easy rejections: published by rules, published by AI, rejected by AI, AI-reviewed, rejected by rules.
- **Shown/hidden decision: 46/50 correct (92%).** Weighted to the real mix of jobs it's **~98.5%**. **18 of the 20 published jobs in the sample are genuine fresher roles** (about 95% once weighted). Rules alone were right 32 of 33 times. When the AI made the call, it was right 14 of 17 times.
- **Where it fails:** the AI is weakest on posts with *no years stated*. 2 of the 8 AI-published jobs were false positives, for example "CleverTap expertise mandatory" with no years given. Field tags are weaker than the decision. **Work mode is 88%**, because a city in the location defaults to "onsite" and overrides the AI's "hybrid". **Category is 88%**, because the title regex picks "Finance" for "Finance Content Creator".
- **Cost:** about 1,100 input and 150 output tokens per post, measured on real calls. On Flash-Lite at $0.30 / $2.50 per million tokens, that's **≈ $0.69 per 1,000 posts the AI reads** ($0.34 with the Batch API). Because rules screen out most posts first, it's **≈ $0.13 per 1,000 India posts ingested**, and close to $0 on daily refreshes because unchanged jobs are cached. On the free tier I actually paid $0.

## 4:30 – 5:00 · Next

- Fix the work-mode priority bug the eval found, and require a stated experience signal before AI can publish.
- Add the Adzuna API to reach 200+ listings. It's one new connector file.
- Deploy: API and worker on a container host, Postgres on Neon, the site on Vercel.
- "Repo, sheet and prompts are linked in the submission. Thanks."
