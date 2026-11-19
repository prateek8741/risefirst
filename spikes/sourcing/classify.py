"""Sourcing spike, phase 2: classify discovered India postings by fresher eligibility.

Applies a simplified version of the proposed deterministic eligibility rules
(docs/ARCHITECTURE_PROPOSAL.md section 8.5), with no LLM. It answers "roughly how many
fresher jobs can these sources yield?". It is not the production classifier.

Usage: python3 -I classify.py <raw_dir> <results_dir>
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

INDIA_PATTERN = re.compile(
    r"\bindia\b|bengaluru|bangalore|mumbai|\bpune\b|hyderabad|chennai|\bdelhi\b|gurgaon|gurugram|noida|"
    r"ghaziabad|faridabad|kolkata|ahmedabad|jaipur|\bkochi\b|cochin|thiruvananthapuram|trivandrum|coimbatore|"
    r"indore|bhopal|chandigarh|mohali|lucknow|nagpur|vadodara|\bsurat\b|visakhapatnam|bhubaneswar|mysuru|"
    r"mysore|mangalore|mangaluru|\bgoa\b|\bncr\b",
    re.IGNORECASE,
)
STRONG_FRESHER_TITLE = re.compile(
    r"\b(intern|internship|trainee|apprentice|apprenticeship|graduate|fresher|freshers|campus|entry[- ]level|"
    r"new grad|early career|university grad|pass[- ]?outs?|batch)\b|\b20(?:2[5-7])\s*(?:grad|batch|pass)",
    re.IGNORECASE,
)
SENIOR_TITLE = re.compile(
    r"\b(senior|sr\.?|lead|principal|staff|director|head|vp|vice president|architect|chief|avp|"
    r"ii|iii|iv|expert)\b",
    re.IGNORECASE,
)
# A bare "Manager" title is not decisive in India (e.g. "Relationship Manager", "Assistant Manager"
# can be entry-level), so it is judged by the stated experience instead of rejected on title.
MANAGER_TITLE = re.compile(r"\bmanager\b", re.IGNORECASE)
JUNIOR_FRIENDLY_EXCEPTIONS = re.compile(r"associate product manager|\bapm\b", re.IGNORECASE)
JUNIOR_TITLE = re.compile(
    r"\b(junior|jr\.?|associate|analyst|executive|coordinator|representative|assistant|"
    r"engineer i|engineer 1|sde[- ]?i|sde[- ]?1|level 1|l1)\b",
    re.IGNORECASE,
)
YEARS = r"(?:years?|yrs?)"
RANGE_PATTERN = re.compile(rf"(\d{{1,2}}(?:\.\d)?)\s*\+?\s*(?:-|–|—|to)\s*(\d{{1,2}}(?:\.\d)?)\s*\+?\s*{YEARS}", re.I)
MIN_PATTERN = re.compile(
    rf"(?:minimum|min\.?|at least|atleast|over|more than)\s*(?:of\s*)?(\d{{1,2}})\s*\+?\s*{YEARS}"
    rf"|(\d{{1,2}})\s*\+\s*{YEARS}|(\d{{1,2}})\s*(?:or more|plus)\s*{YEARS}"
    rf"|(\d{{1,2}})\s*{YEARS}(?:\s*of)?(?:\s+\w+){{0,3}}\s+experienc",
    re.I,
)
UPTO_PATTERN = re.compile(rf"(?:up to|upto)\s*(\d{{1,2}})\s*{YEARS}", re.I)
FRESHER_TEXT = re.compile(r"\bfreshers?\b|recent graduates?|new grads?|no (?:prior )?experience (?:is )?required", re.I)
SENTENCE_SPLIT = re.compile(r"[.\n;•●▪]|<br\s*/?>|</li>|</p>")

DOMAIN_KEYWORDS: list[tuple[str, re.Pattern[str]]] = [
    ("Data/AI", re.compile(r"data|machine learning|\bml\b|\bai\b|analytics|scientist", re.I)),
    ("Software/IT", re.compile(r"engineer|developer|sde|software|devops|cloud|qa|test|security|it ", re.I)),
    ("Sales/Marketing", re.compile(r"sales|marketing|growth|business development|account|brand|content|seo", re.I)),
    ("Finance", re.compile(r"financ|account|audit|tax|payroll|credit|risk|treasury", re.I)),
    ("Operations", re.compile(r"operations|ops|supply|logistics|program|project", re.I)),
    ("Customer Support", re.compile(r"support|customer|success|service", re.I)),
    ("HR", re.compile(r"\bhr\b|human resources|recruit|talent|people", re.I)),
    ("Design", re.compile(r"design|ux|ui|creative", re.I)),
    ("Product", re.compile(r"product", re.I)),
]


@dataclass(frozen=True)
class Posting:
    ats: str
    board: str
    title: str
    location: str
    description: str
    url: str


def strip_html(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(text or "")))


def extract_postings(ats: str, board: str, payload: object) -> list[Posting]:
    postings: list[Posting] = []
    if ats == "greenhouse":
        for job in payload.get("jobs", []):
            postings.append(Posting(ats, board, job.get("title", ""), (job.get("location") or {}).get("name", ""),
                                    strip_html(job.get("content", "")), job.get("absolute_url", "")))
    elif ats == "lever":
        for job in payload:
            categories = job.get("categories") or {}
            location = " | ".join([categories.get("location") or ""] + (categories.get("allLocations") or []))
            lists_text = " ".join(f"{item.get('text', '')}: {strip_html(item.get('content', ''))}" for item in job.get("lists") or [])
            description = " ".join([job.get("descriptionPlain") or "", lists_text, job.get("additionalPlain") or ""])
            postings.append(Posting(ats, board, job.get("text", ""), location, description, job.get("hostedUrl", "")))
    elif ats == "ashby":
        for job in payload.get("jobs", []):
            if job.get("isListed") is False:
                continue
            secondary = [s.get("location") or "" for s in job.get("secondaryLocations") or []]
            location = " | ".join([job.get("location") or ""] + secondary)
            postings.append(Posting(ats, board, job.get("title", ""), location, job.get("descriptionPlain") or "",
                                    job.get("jobUrl", "")))
    elif ats == "workable":
        for job in payload.get("jobs", []):
            places = [" ".join(filter(None, [l.get("city"), l.get("region"), l.get("country")])) for l in job.get("locations") or []]
            location = " | ".join(places + [" ".join(filter(None, [job.get("city"), job.get("state"), job.get("country")]))])
            postings.append(Posting(ats, board, job.get("title", ""), location, strip_html(job.get("description", "")),
                                    job.get("url") or job.get("shortlink", "")))
    elif ats == "recruitee":
        for offer in payload.get("offers", []):
            location = " ".join(filter(None, [offer.get("location"), offer.get("city"), offer.get("country"),
                                              "India" if offer.get("country_code") == "IN" else ""]))
            description = strip_html((offer.get("description") or "") + " " + (offer.get("requirements") or ""))
            postings.append(Posting(ats, board, offer.get("title", ""), location, description, offer.get("careers_url", "")))
    return postings


def experience_lower_bounds(description: str) -> tuple[list[float], list[float]]:
    """Return (lower bounds, upper bounds) from sentences that talk about experience."""
    lower: list[float] = []
    upper: list[float] = []
    for sentence in SENTENCE_SPLIT.split(description):
        if "experienc" not in sentence.lower() and "exp " not in sentence.lower():
            continue
        for low, high in RANGE_PATTERN.findall(sentence):
            if float(high) >= float(low) and float(high) <= 30:
                lower.append(float(low))
                upper.append(float(high))
        for value in UPTO_PATTERN.findall(sentence):
            lower.append(0.0)
            upper.append(float(value))
        # Remove spans already consumed so "0-2 years of experience" isn't re-read as "2 years".
        remainder = UPTO_PATTERN.sub(" ", RANGE_PATTERN.sub(" ", sentence))
        for groups in MIN_PATTERN.findall(remainder):
            value = next((g for g in groups if g), None)
            if value is not None and float(value) <= 30:
                lower.append(float(value))
    return lower, upper


def classify(posting: Posting) -> tuple[str, str]:
    title = posting.title
    senior_title = SENIOR_TITLE.search(title) and not JUNIOR_FRIENDLY_EXCEPTIONS.search(title)
    if senior_title and not STRONG_FRESHER_TITLE.search(title):
        return "REJECTED", "senior title"
    lower, upper = experience_lower_bounds(posting.description)
    highest_lower = max(lower) if lower else None
    if highest_lower is not None and highest_lower >= 3:
        return "REJECTED", f"requires {highest_lower:g}+ years"
    if STRONG_FRESHER_TITLE.search(title):
        return "ELIGIBLE", "intern/trainee/graduate title"
    if highest_lower is not None and highest_lower <= 1 and (not upper or max(upper) <= 3):
        return "ELIGIBLE", f"experience {highest_lower:g}-{max(upper) if upper else '?'} years"
    if highest_lower is None and FRESHER_TEXT.search(posting.description):
        return "ELIGIBLE", "freshers mentioned"
    if highest_lower == 2:
        return "REVIEW", "borderline: 2+ years"
    if MANAGER_TITLE.search(title) and not JUNIOR_FRIENDLY_EXCEPTIONS.search(title):
        return ("REVIEW", "manager title, experience <=2 or not stated") if highest_lower is not None else ("UNKNOWN", "manager title, experience not stated")
    if JUNIOR_TITLE.search(title) or JUNIOR_FRIENDLY_EXCEPTIONS.search(title):
        return "REVIEW", "junior title, experience not stated" if highest_lower is None else "junior title"
    return "UNKNOWN", "experience not stated, neutral title"


def domain_of(title: str) -> str:
    return next((name for name, pattern in DOMAIN_KEYWORDS if pattern.search(title)), "Other")


def main() -> None:
    raw_dir, results_dir = Path(sys.argv[1]), Path(sys.argv[2])
    results_dir.mkdir(parents=True, exist_ok=True)
    discovery = json.loads((raw_dir / "discovery.json").read_text())

    per_board: dict[tuple[str, str], Counter] = defaultdict(Counter)
    eligible_rows: list[dict[str, str]] = []
    seen_unique: set[tuple[str, str, str]] = set()
    unique_eligible = 0
    ats_summary: dict[str, Counter] = defaultdict(Counter)
    domains: Counter = Counter()

    for ats, boards in discovery.items():
        ats_summary[ats]["boards_with_jobs"] = sum(1 for b in boards.values() if b["jobs"])
        for board, meta in boards.items():
            if not meta["jobs"]:
                continue
            payload = json.loads((raw_dir / ats / f"{board}.json").read_text())
            postings = extract_postings(ats, board, payload)
            ats_summary[ats]["all_postings"] += len(postings)
            for posting in postings:
                if not INDIA_PATTERN.search(posting.location):
                    continue
                label, reason = classify(posting)
                per_board[(ats, board)]["india"] += 1
                per_board[(ats, board)][label] += 1
                ats_summary[ats]["india_postings"] += 1
                ats_summary[ats][label] += 1
                if label == "ELIGIBLE":
                    key = (board, posting.title.strip().lower(), posting.location.strip().lower())
                    if key not in seen_unique:
                        seen_unique.add(key)
                        unique_eligible += 1
                    domains[domain_of(posting.title)] += 1
                    eligible_rows.append({"ats": ats, "board": board, "title": posting.title,
                                          "location": posting.location, "reason": reason, "url": posting.url})

    india_boards = sorted(((k, v) for k, v in per_board.items()), key=lambda kv: -kv[1]["ELIGIBLE"])
    with (results_dir / "boards_with_india_jobs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ats", "board", "india_postings", "eligible", "review", "rejected", "unknown"])
        for (ats, board), counts in india_boards:
            writer.writerow([ats, board, counts["india"], counts["ELIGIBLE"], counts["REVIEW"], counts["REJECTED"], counts["UNKNOWN"]])
    with (results_dir / "eligible_postings.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ats", "board", "title", "location", "reason", "url"])
        writer.writeheader()
        writer.writerows(eligible_rows)

    summary = {
        "per_ats": {ats: dict(counts) for ats, counts in ats_summary.items()},
        "boards_with_india_jobs": len(per_board),
        "boards_with_eligible_jobs": sum(1 for c in per_board.values() if c["ELIGIBLE"]),
        "eligible_postings": len(eligible_rows),
        "eligible_unique_title_location": unique_eligible,
        "eligible_by_domain": dict(domains.most_common()),
    }
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nTop boards by eligible postings:")
    for (ats, board), counts in india_boards[:25]:
        print(f"  {ats:10} {board:28} india={counts['india']:4} eligible={counts['ELIGIBLE']:3} review={counts['REVIEW']:3}")


if __name__ == "__main__":
    main()
