import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const plexSans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-plex-sans" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex-mono" });

export const metadata: Metadata = {
  title: { default: "RiseFirst — Fresher jobs & internships in India", template: "%s · RiseFirst" },
  description:
    "Internships, trainee programmes and 0–1 year jobs in India, collected daily from employers' own career pages.",
};

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 text-[17px] font-bold tracking-tight text-ink">
      <span aria-hidden className="flex h-7 w-7 items-center justify-center rounded-[5px] border-[1.5px] border-ink bg-orange text-sm font-bold text-white shadow-[0_2px_0_var(--color-ink)]">
        ↑
      </span>
      RiseFirst
    </Link>
  );
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en-IN" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body className="flex min-h-screen flex-col antialiased">
        <header className="sticky top-0 z-20 border-b border-line bg-paper/90 backdrop-blur">
          <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-2.5">
            <Logo />
            <div className="flex items-center gap-1 text-sm font-semibold text-muted">
              <Link href="/" className="rounded-md px-3 py-1.5 hover:bg-chrome hover:text-ink">Jobs</Link>
              <Link href="/?employment_type=internship" className="hidden rounded-md px-3 py-1.5 hover:bg-chrome hover:text-ink sm:block">Internships</Link>
              <Link href="/about" className="rounded-md px-3 py-1.5 hover:bg-chrome hover:text-ink">How it works</Link>
              <Link href="/" className="btn btn-primary btn-sm ml-2 hidden sm:inline-flex">Find jobs</Link>
            </div>
          </nav>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>

        <footer className="border-t border-line bg-paper">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 text-sm text-muted md:grid-cols-[2fr_1fr_1fr]">
            <div className="space-y-3">
              <Logo />
              <p className="max-w-sm">
                Fresher jobs and internships in India, collected every day from employers&apos; own job boards. Every
                listing links to the company&apos;s page, where you apply.
              </p>
            </div>
            <div className="space-y-2">
              <p className="eyebrow">Browse</p>
              <ul className="space-y-1.5">
                <li><Link href="/" className="hover:text-ink">All fresher jobs</Link></li>
                <li><Link href="/?employment_type=internship" className="hover:text-ink">Internships</Link></li>
                <li><Link href="/?work_mode=remote" className="hover:text-ink">Remote</Link></li>
              </ul>
            </div>
            <div className="space-y-2">
              <p className="eyebrow">About</p>
              <ul className="space-y-1.5">
                <li><Link href="/about" className="hover:text-ink">How it works</Link></li>
                <li><Link href="/about#removal" className="hover:text-ink">Removal requests</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-line">
            <p className="mx-auto max-w-6xl px-4 py-4 font-mono text-xs text-subtle">
              Sources: Greenhouse, Lever and Ashby public job boards. Not affiliated with the listed employers.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
