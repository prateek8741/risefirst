import Link from "next/link";
import { Filters } from "@/components/Filters";
import { JobCard } from "@/components/JobCard";
import { Pagination } from "@/components/Pagination";
import { api, type Facets, type JobFilters, type JobList, type Stats } from "@/lib/api";
import { timeAgo } from "@/lib/format";

export const dynamic = "force-dynamic";

const FILTER_KEYS = ["q", "category", "city", "employment_type", "work_mode", "include_review", "ai_assessed", "page"] as const;

function readFilters(params: Record<string, string | string[] | undefined>): JobFilters {
  const filters: JobFilters = {};
  for (const key of FILTER_KEYS) {
    const value = params[key];
    const first = Array.isArray(value) ? value[0] : value;
    if (first) filters[key] = first.slice(0, 200);
  }
  return filters;
}

export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const filters = readFilters(await searchParams);

  let jobs: JobList | null = null;
  let facets: Facets | null = null;
  let stats: Stats | null = null;
  try {
    [jobs, facets, stats] = await Promise.all([api.jobs(filters), api.facets(filters), api.stats()]);
  } catch {
    // Rendered below as a friendly error; the API may be starting up.
  }

  const filtered = Object.keys(filters).some((k) => k !== "page");

  return (
    <div className="space-y-8">
      <section className="grid items-center gap-8 md:grid-cols-[1.4fr_1fr]">
        <div className="space-y-5">
          <p className="inline-flex items-center gap-2 rounded-full border border-line bg-paper px-3 py-1 font-mono text-xs text-muted">
            <span className="h-2 w-2 rounded-full bg-green" aria-hidden />
            {stats?.last_refreshed_at ? `Refreshed ${timeAgo(stats.last_refreshed_at)}` : "Refreshed daily"} · straight from company job boards
          </p>
          <h1 className="text-4xl font-bold leading-[1.05] tracking-tight text-ink md:text-[56px]">
            Fresher jobs &amp; internships in India, <span className="marker">without the noise.</span>
          </h1>
          <p className="max-w-xl text-lg text-muted">
            Internships, trainee programmes and 0–1 year roles, checked every day on employers&apos; own career pages.
            No senior roles in disguise, no reposted spam.
          </p>
          <div className="flex flex-wrap gap-3">
            <a href="#results" className="btn btn-primary">Browse jobs ↓</a>
            <Link href="/?employment_type=internship#results" className="btn btn-secondary">Internships only</Link>
          </div>
        </div>

        <div className="window" aria-label="Today's numbers">
          <div className="window-bar">
            <div className="window-dots" aria-hidden>
              <span className="bg-[#f1452f]" />
              <span className="bg-yellow" />
              <span className="bg-[#3fb950]" />
            </div>
            <span>today.stats</span>
          </div>
          <dl className="grid grid-cols-2 divide-x divide-y divide-line">
            <Stat label="Fresher roles" value={stats?.eligible_jobs} accent="text-orange" />
            <Stat label="Companies" value={stats?.companies} />
            <Stat label="Assessed by AI ✨" value={stats?.ai_assessed_jobs} accent="text-[#86199f]" />
            <Stat label="Experience unclear" value={stats?.review_jobs} />
          </dl>
        </div>
      </section>

      <Filters filters={filters} facets={facets} />

      {jobs === null ? (
        <div role="alert" className="card border-[#f0d48f] bg-[#fdf1d3] p-6 text-[#7a5200]">
          We couldn&apos;t load jobs right now. Please try again in a minute.
        </div>
      ) : jobs.total === 0 ? (
        <div className="card border-dashed p-10 text-center text-muted">
          <p className="text-lg font-bold text-ink">No jobs match these filters.</p>
          <p className="mt-1 text-sm">Try fewer filters, or tick “Also show roles where the experience needed isn&apos;t clear”.</p>
        </div>
      ) : (
        <section id="results" aria-label="Job results" className="scroll-mt-20">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-xl font-bold tracking-tight">
              {jobs.total} {jobs.total === 1 ? "job" : "jobs"}{filtered ? " match your search" : ""}
            </h2>
            <span className="eyebrow hidden sm:block">Verified fresher roles first · newest next</span>
          </div>
          <ul className="space-y-3">
            {jobs.items.map((job) => <JobCard key={job.id} job={job} />)}
          </ul>
          <Pagination filters={filters} page={jobs.page} pages={jobs.pages} />
        </section>
      )}
    </div>
  );
}

function Stat({ label, value, accent = "text-ink" }: { label: string; value: number | undefined; accent?: string }) {
  return (
    <div className="space-y-1 p-5">
      <dt className="eyebrow">{label}</dt>
      <dd className={`text-4xl font-bold tracking-tight ${accent}`}>{value ?? "—"}</dd>
    </div>
  );
}
