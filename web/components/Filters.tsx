"use client";

import Link from "next/link";
import type { Facets, JobFilters } from "@/lib/api";
import { EMPLOYMENT_LABELS, WORK_MODE_LABELS } from "@/lib/format";

// A plain GET form: works without JavaScript; with JS, dropdowns apply as soon as they change.
export function Filters({ filters, facets }: { filters: JobFilters; facets: Facets | null }) {
  const submit = (event: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) => event.currentTarget.form?.requestSubmit();
  const active = Object.entries(filters).some(([key, value]) => value && key !== "page");

  // The selected option is always listed (with its count, or 0), so the dropdown never hides an active filter.
  const options = (counts: Record<string, number> | undefined, selected: string | undefined, labels?: Record<string, string>) =>
    Object.entries({ ...(selected ? { [selected]: 0 } : {}), ...(counts ?? {}) }).map(([value, count]) => (
      <option key={value} value={value}>
        {(labels?.[value] ?? value) + ` (${count})`}
      </option>
    ));

  const dropdowns: { name: keyof JobFilters; label: string; all: string; counts?: Record<string, number>; labels?: Record<string, string> }[] = [
    { name: "category", label: "Category", all: "All categories", counts: facets?.categories },
    { name: "city", label: "City", all: "All cities", counts: facets?.cities },
    { name: "employment_type", label: "Job type", all: "Any type", counts: facets?.employment_types, labels: EMPLOYMENT_LABELS },
    { name: "work_mode", label: "Work mode", all: "Any mode", counts: facets?.work_modes, labels: WORK_MODE_LABELS },
  ];

  return (
    <form action="/" method="get" role="search" className="window">
      <div className="window-bar">
        <div className="window-dots" aria-hidden>
          <span className="bg-[#f1452f]" />
          <span className="bg-yellow" />
          <span className="bg-[#3fb950]" />
        </div>
        <span>search.jobs</span>
        {active && (
          <Link href="/" className="ml-auto font-sans text-xs font-semibold text-orange hover:text-orange-dark">
            Clear all filters ×
          </Link>
        )}
      </div>

      <div className="space-y-4 p-4">
        <div className="flex flex-col gap-2 sm:flex-row">
          <label htmlFor="q" className="sr-only">Search jobs</label>
          <input
            id="q"
            name="q"
            type="search"
            defaultValue={filters.q}
            maxLength={200}
            placeholder="Role, company or skill — e.g. “data analyst”, “Python”"
            className="field flex-1 !py-2.5 !text-[15px]"
          />
          <button type="submit" className="btn btn-primary">Search</button>
        </div>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {dropdowns.map((d) => (
            <label key={d.name} className="space-y-1">
              <span className="eyebrow block">{d.label}</span>
              <select name={d.name} defaultValue={filters[d.name] ?? ""} onChange={submit} className="field">
                <option value="">{d.all}</option>
                {options(d.counts, filters[d.name], d.labels)}
              </select>
            </label>
          ))}
        </div>

        <div className="flex flex-col gap-2 border-t border-dashed border-line pt-3 text-sm text-muted sm:flex-row sm:gap-6">
          <label className="flex cursor-pointer items-center gap-2">
            <input type="checkbox" name="include_review" value="true" defaultChecked={!!filters.include_review} onChange={submit} className="h-4 w-4 accent-orange" />
            Also show roles where the experience needed isn&apos;t clear
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <input type="checkbox" name="ai_assessed" value="true" defaultChecked={!!filters.ai_assessed} onChange={submit} className="h-4 w-4 accent-orange" />
            Only jobs assessed by AI ✨
          </label>
        </div>
      </div>
    </form>
  );
}
