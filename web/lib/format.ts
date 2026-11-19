import type { JobSummary } from "./api";

export const EMPLOYMENT_LABELS: Record<string, string> = {
  internship: "Internship",
  apprenticeship: "Apprenticeship",
  full_time: "Full-time",
  contract: "Contract",
  unknown: "Not specified",
};

export const WORK_MODE_LABELS: Record<string, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
  unknown: "Not specified",
};

export function experienceLabel(job: Pick<JobSummary, "experience_min" | "experience_max">): string {
  const { experience_min: min, experience_max: max } = job;
  if (min === null) return "Experience not specified";
  if (max !== null && max !== min) return `${min}–${max} years`;
  if (min === 0) return "No experience needed";
  return `${min}+ year${min === 1 ? "" : "s"}`;
}

export function locationLabel(job: Pick<JobSummary, "cities" | "work_mode" | "location">): string {
  if (job.cities.length) return job.cities.slice(0, 3).join(", ") + (job.cities.length > 3 ? " +more" : "");
  if (job.work_mode === "remote") return "Remote (India)";
  return job.location || "India";
}

const IST = "Asia/Kolkata";

export function formatDate(iso: string | null): string {
  if (!iso) return "Not specified";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: IST });
}

export function timeAgo(iso: string | null, now: Date = new Date()): string {
  if (!iso) return "";
  const days = Math.floor((now.getTime() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return months === 1 ? "1 month ago" : `${months} months ago`;
}
