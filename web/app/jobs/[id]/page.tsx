import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AiBadge, Monogram, Tag } from "@/components/JobCard";
import { ApiError, api, type JobDetail } from "@/lib/api";
import { EMPLOYMENT_LABELS, WORK_MODE_LABELS, experienceLabel, formatDate, locationLabel } from "@/lib/format";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ id: string }> };

async function load(id: string): Promise<JobDetail> {
  if (!/^\d{1,12}$/.test(id)) notFound();
  try {
    return await api.job(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const job = await load((await params).id);
  return {
    title: `${job.title} at ${job.company}`,
    description: job.summary ?? `${job.title} at ${job.company} — ${locationLabel(job)}. Apply on the company's site.`,
  };
}

// Google JobPosting structured data. Only fields we actually have; nothing invented.
function jsonLd(job: JobDetail) {
  return {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: job.title,
    description: job.description,
    datePosted: job.posted_at ?? job.last_verified_at,
    hiringOrganization: { "@type": "Organization", name: job.company },
    employmentType: { internship: "INTERN", full_time: "FULL_TIME", contract: "CONTRACTOR" }[job.employment_type as string],
    ...(job.work_mode === "remote"
      ? { jobLocationType: "TELECOMMUTE", applicantLocationRequirements: { "@type": "Country", name: "India" } }
      : {
          jobLocation: (job.cities.length ? job.cities : ["India"]).map((city) => ({
            "@type": "Place",
            address: { "@type": "PostalAddress", addressLocality: city, addressCountry: "IN" },
          })),
        }),
    directApply: false,
  };
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2.5">
      <dt className="eyebrow">{label}</dt>
      <dd className="text-right text-sm font-semibold text-ink">{value}</dd>
    </div>
  );
}

export default async function JobPage({ params }: Props) {
  const job = await load((await params).id);

  return (
    <article className="space-y-5">
      <script
        type="application/ld+json"
        // JSON.stringify output with "<" escaped cannot break out of the script tag.
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd(job)).replace(/</g, "\\u003c") }}
      />
      <Link href="/" className="inline-flex items-center gap-1 font-mono text-xs font-medium text-muted hover:text-orange">
        ← back to all jobs
      </Link>

      <div className="grid items-start gap-5 lg:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          <header className="card p-6">
            <div className="flex gap-4">
              <Monogram name={job.company} size="lg" />
              <div className="min-w-0">
                <p className="eyebrow">{job.company}</p>
                <h1 className="mt-1 text-2xl font-bold leading-tight tracking-tight text-ink md:text-[32px]">{job.title}</h1>
                <p className="mt-1 text-muted">{locationLabel(job)}</p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-1.5">
              {job.verified_fresher ? <Tag tone="green">✓ Fresher-friendly</Tag> : <Tag tone="amber">Check experience required</Tag>}
              {job.ai_assessed && <AiBadge decided={job.decided_by_ai} />}
              <Tag>{job.category}</Tag>
            </div>
            {job.summary && <p className="mt-4 border-l-4 border-yellow pl-3 text-[15px] text-ink">{job.summary}</p>}
          </header>

          <section className="window">
            <div className="window-bar">
              <div className="window-dots" aria-hidden>
                <span className="bg-[#f1452f]" />
                <span className="bg-yellow" />
                <span className="bg-[#3fb950]" />
              </div>
              <span>job-description.txt</span>
            </div>
            {/* Plain text from the backend, rendered as text: no HTML injection possible. */}
            <div className="whitespace-pre-line p-6 text-[15px] leading-relaxed text-muted">{job.description}</div>
          </section>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-20">
          <div className="card space-y-4 p-5">
            <a href={job.apply_url} target="_blank" rel="noopener noreferrer nofollow" className="btn btn-primary w-full !py-3 !text-[15px]">
              Apply on {job.company}&apos;s site ↗
            </a>
            <dl className="divide-y divide-dashed divide-line">
              <Fact label="Experience" value={experienceLabel(job)} />
              <Fact label="Job type" value={EMPLOYMENT_LABELS[job.employment_type]} />
              <Fact label="Work mode" value={WORK_MODE_LABELS[job.work_mode]} />
              <Fact label="Posted" value={formatDate(job.posted_at)} />
              <Fact label="Last checked" value={formatDate(job.last_verified_at)} />
            </dl>
          </div>

          {job.skills.length > 0 && (
            <div className="card p-5">
              <p className="eyebrow mb-2">Skills mentioned</p>
              <div className="flex flex-wrap gap-1.5">{job.skills.map((s) => <Tag key={s} tone="indigo">{s}</Tag>)}</div>
            </div>
          )}

          <div className="rounded-md border border-dashed border-line-strong p-4 text-xs leading-relaxed text-muted">
            <p className="eyebrow mb-1.5">Why it&apos;s listed</p>
            <p>
              {job.eligibility_reason}
              {job.classified_by === "ai" && " (assessed by AI from the job description)"}.
            </p>
            {job.ai_assessed && (
              <p className="mt-2 text-[#86199f]">
                ✨ AI: {job.decided_by_ai
                  ? "the rules couldn't tell how much experience this needs, so the AI read the description and made the call."
                  : "the rules made the fresher decision; the AI added the summary, skills and category."}
              </p>
            )}
            <p className="mt-2">
              Source: {job.company}&apos;s job board on {job.source}. Always confirm details on the employer&apos;s page
              before applying.
            </p>
          </div>
        </aside>
      </div>
    </article>
  );
}
