import Link from "next/link";
import type { JobFilters } from "@/lib/api";

function href(filters: JobFilters, page: number): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value && key !== "page") params.set(key, value);
  }
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  return query ? `/?${query}` : "/";
}

export function Pagination({ filters, page, pages }: { filters: JobFilters; page: number; pages: number }) {
  if (pages <= 1) return null;
  return (
    <nav aria-label="Pagination" className="mt-8 flex items-center justify-center gap-4">
      {page > 1 ? <Link className="btn btn-secondary btn-sm" href={href(filters, page - 1)}>← Previous</Link> : <span className="w-24" />}
      <span className="font-mono text-xs text-muted">Page {page} / {pages}</span>
      {page < pages ? <Link className="btn btn-secondary btn-sm" href={href(filters, page + 1)}>Next →</Link> : <span className="w-24" />}
    </nav>
  );
}
