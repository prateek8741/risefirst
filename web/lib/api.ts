// Typed client for the RiseFirst FastAPI backend. Runs on the server (React Server Components).

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export type JobSummary = {
  id: number;
  slug: string;
  title: string;
  company: string;
  location: string;
  cities: string[];
  work_mode: "remote" | "hybrid" | "onsite" | "unknown";
  employment_type: "internship" | "apprenticeship" | "full_time" | "contract" | "unknown";
  category: string;
  skills: string[];
  experience_min: number | null;
  experience_max: number | null;
  verified_fresher: boolean;
  ai_assessed: boolean;
  decided_by_ai: boolean;
  summary: string | null;
  posted_at: string | null;
  last_verified_at: string;
  source: string;
};

export type JobDetail = JobSummary & {
  description: string;
  apply_url: string;
  eligibility_reason: string;
  classified_by: "rules" | "ai";
};

export type JobList = { items: JobSummary[]; total: number; page: number; page_size: number; pages: number };

export type Facets = {
  categories: Record<string, number>;
  cities: Record<string, number>;
  employment_types: Record<string, number>;
  work_modes: Record<string, number>;
};

export type Stats = {
  eligible_jobs: number;
  review_jobs: number;
  ai_assessed_jobs: number;
  companies: number;
  last_refreshed_at: string | null;
};

export type JobFilters = {
  q?: string;
  category?: string;
  city?: string;
  employment_type?: string;
  work_mode?: string;
  include_review?: string;
  ai_assessed?: string;
  page?: string;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function get<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(path, API_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value) url.searchParams.set(key, value);
  }
  // No caching: the header, the dropdown counts and the results must come from the same moment,
  // or they disagree while a refresh is running. The API answers in milliseconds.
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new ApiError(response.status, `${response.status} from ${url.pathname}`);
  return response.json() as Promise<T>;
}

function toParams(filters: JobFilters): Record<string, string | undefined> {
  return {
    ...filters,
    include_review: filters.include_review ? "true" : undefined,
    ai_assessed: filters.ai_assessed ? "true" : undefined,
  };
}

export const api = {
  jobs: (filters: JobFilters) => get<JobList>("/api/jobs", toParams(filters)),
  job: (id: string) => get<JobDetail>(`/api/jobs/${encodeURIComponent(id)}`),
  // Same filters as the job list, so each dropdown's counts match what picking that option returns.
  facets: (filters: JobFilters) => get<Facets>("/api/facets", { ...toParams(filters), page: undefined }),
  stats: () => get<Stats>("/api/stats"),
};
