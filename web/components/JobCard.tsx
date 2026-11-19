import Link from "next/link";
import type { JobSummary } from "@/lib/api";
import { EMPLOYMENT_LABELS, WORK_MODE_LABELS, experienceLabel, locationLabel, timeAgo } from "@/lib/format";

// Each company gets a stable colour so the list is easy to scan.
const MONOGRAM_COLOURS = [
  "bg-orange text-white",
  "bg-yellow text-ink",
  "bg-blue text-white",
  "bg-green text-white",
  "bg-ink text-white",
  "bg-[#b62ad9] text-white",
];

function colourFor(name: string): string {
  let hash = 0;
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return MONOGRAM_COLOURS[hash % MONOGRAM_COLOURS.length];
}

export function Monogram({ name, size = "md" }: { name: string; size?: "md" | "lg" }) {
  const letters = name.replace(/[^A-Za-z0-9 ]/g, "").split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("");
  const box = size === "lg" ? "h-14 w-14 text-xl" : "h-11 w-11 text-base";
  return (
    <div aria-hidden className={`${box} ${colourFor(name)} flex shrink-0 items-center justify-center rounded-md border-[1.5px] border-ink font-bold shadow-[0_2px_0_var(--color-ink)]`}>
      {letters.toUpperCase() || "?"}
    </div>
  );
}

type Tone = "slate" | "green" | "amber" | "indigo" | "violet";

const TONES: Record<Tone, string> = {
  slate: "border-line bg-chrome text-muted",
  green: "border-[#b5dcc0] bg-[#e3f3e7] text-[#1f6b3a]",
  amber: "border-[#f0d48f] bg-[#fdf1d3] text-[#7a5200]",
  indigo: "border-[#c3cdfb] bg-[#e6ebff] text-[#1d3bd1]",
  violet: "border-[#e3b5ef] bg-[#f6e3fb] text-[#86199f]",
};

export function Tag({ children, tone = "slate" }: { children: React.ReactNode; tone?: Tone }) {
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-semibold ${TONES[tone]}`}>{children}</span>
  );
}

export function AiBadge({ decided }: { decided: boolean }) {
  return (
    <span title={decided ? "The AI read the description and made the fresher decision" : "The AI read the description and extracted skills and a summary"}>
      <Tag tone="violet">✨ {decided ? "AI decision" : "AI-assessed"}</Tag>
    </span>
  );
}

export function JobCard({ job }: { job: JobSummary }) {
  return (
    <li>
      <Link
        href={`/jobs/${job.id}`}
        className="card group flex gap-4 p-4 transition hover:-translate-y-0.5 hover:border-ink hover:shadow-[0_3px_0_var(--color-ink)]"
      >
        <Monogram name={job.company} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
            <div className="min-w-0">
              <h3 className="text-[16px] font-bold leading-snug text-ink group-hover:text-orange">{job.title}</h3>
              <p className="text-sm text-muted">
                <span className="font-semibold text-ink">{job.company}</span> · {locationLabel(job)}
              </p>
            </div>
            {job.posted_at && <span className="font-mono text-xs text-subtle">{timeAgo(job.posted_at)}</span>}
          </div>
          {job.summary && <p className="mt-2 line-clamp-2 text-sm text-muted">{job.summary}</p>}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {job.verified_fresher ? <Tag tone="green">✓ Fresher-friendly</Tag> : <Tag tone="amber">Check experience</Tag>}
            {job.ai_assessed && <AiBadge decided={job.decided_by_ai} />}
            {job.employment_type !== "unknown" && <Tag tone="indigo">{EMPLOYMENT_LABELS[job.employment_type]}</Tag>}
            {job.work_mode !== "unknown" && <Tag>{WORK_MODE_LABELS[job.work_mode]}</Tag>}
            <Tag>{experienceLabel(job)}</Tag>
            <Tag>{job.category}</Tag>
          </div>
        </div>
      </Link>
    </li>
  );
}
