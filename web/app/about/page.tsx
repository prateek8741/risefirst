import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "How it works" };

const STEPS = [
  {
    title: "We read employers' own job boards",
    body: (
      <>
        <p>
          Every day RiseFirst reads the public job boards that companies publish through their hiring systems (Greenhouse,
          Lever and Ashby). These are official, open feeds meant to be read. We follow each site&apos;s robots.txt and
          rate limits.
        </p>
        <p>
          We don&apos;t copy listings from job portals such as LinkedIn, Naukri, Indeed or Internshala. Every job links to
          the employer&apos;s own page, where you apply.
        </p>
      </>
    ),
  },
  {
    title: "Rules decide who counts as a fresher",
    body: (
      <ul className="list-disc space-y-1 pl-5">
        <li>Internships, apprenticeships, trainee and graduate programmes are included.</li>
        <li>Jobs asking for 0–1 years (up to 3 at most), or saying freshers are welcome, are included.</li>
        <li>Senior, lead, staff or manager-level titles, and jobs asking for 3+ years, are left out.</li>
      </ul>
    ),
  },
  {
    title: "AI settles the unclear ones ✨",
    body: (
      <p>
        When a description doesn&apos;t say how much experience is needed, an AI model reads it. It can include a job
        only when it is confident, and it can never override the rules above. Jobs it assessed carry an{" "}
        <strong>AI-assessed</strong> or <strong>AI decision</strong> badge. Jobs we still can&apos;t judge are hidden
        unless you tick “Also show roles where the experience needed isn&apos;t clear”.
      </p>
    ),
  },
  {
    title: "Listings stay fresh",
    body: (
      <p>
        Each job shows when we last checked it. A job that disappears from the employer&apos;s board for two daily
        checks in a row is removed.
      </p>
    ),
  },
];

export default function About() {
  return (
    <article className="mx-auto max-w-3xl space-y-8">
      <header className="space-y-3">
        <p className="eyebrow">How it works</p>
        <h1 className="text-4xl font-bold leading-tight tracking-tight md:text-5xl">
          Fewer jobs, <span className="marker">all of them real.</span>
        </h1>
        <p className="text-lg text-muted">
          RiseFirst lists only roles a fresher can actually get, taken straight from the company that is hiring.
        </p>
      </header>

      <ol className="space-y-4">
        {STEPS.map((step, index) => (
          <li key={step.title} className="card flex gap-4 p-5">
            <span aria-hidden className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border-[1.5px] border-ink bg-yellow font-mono text-sm font-bold shadow-[0_2px_0_var(--color-ink)]">
              {index + 1}
            </span>
            <div className="space-y-2 text-[15px] leading-relaxed text-muted">
              <h2 className="text-lg font-bold text-ink">{step.title}</h2>
              {step.body}
            </div>
          </li>
        ))}
      </ol>

      <section id="removal" className="scroll-mt-24 rounded-md border border-dashed border-line-strong p-5 text-[15px] text-muted">
        <h2 className="mb-1 text-lg font-bold text-ink">Removal requests</h2>
        <p>
          If you are an employer and want a listing removed or corrected, contact the site operator and we will remove it
          from the next daily update.
        </p>
      </section>

      <Link href="/" className="btn btn-primary">Browse fresher jobs →</Link>
    </article>
  );
}
