"""Connectors for public employer job-board APIs (no keys, documented, robots.txt-permitted).

Each connector covers one employer board. `parse_*` functions are pure so they can be
tested against recorded payloads without network access.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from risefirst.domain.models import RawPosting
from risefirst.infrastructure.connectors.text import from_epoch_ms, html_to_text, parse_iso
from risefirst.infrastructure.http import PoliteHttpClient


def parse_greenhouse(board: str, company: str, payload: dict[str, Any]) -> list[RawPosting]:
    postings = []
    for job in payload.get("jobs", []):
        offices = ", ".join(o.get("name", "") for o in job.get("offices") or [] if o.get("name"))
        location = " | ".join(filter(None, [(job.get("location") or {}).get("name", ""), offices]))
        postings.append(RawPosting(
            source="greenhouse",
            board=board,
            external_id=str(job["id"]),
            company=company,
            title=job.get("title", ""),
            location_text=location,
            description=html_to_text(job.get("content")),
            apply_url=job.get("absolute_url", ""),
            posted_at=parse_iso(job.get("first_published") or job.get("updated_at")),
        ))
    return postings


def parse_lever(board: str, company: str, payload: list[dict[str, Any]]) -> list[RawPosting]:
    postings = []
    for job in payload:
        categories = job.get("categories") or {}
        locations = [categories.get("location") or ""] + list(categories.get("allLocations") or [])
        sections = "\n\n".join(
            f"{item.get('text', '')}\n{html_to_text(item.get('content'))}" for item in job.get("lists") or []
        )
        description = "\n\n".join(filter(None, [
            job.get("descriptionPlain") or html_to_text(job.get("description")),
            sections,
            job.get("additionalPlain") or "",
        ]))
        postings.append(RawPosting(
            source="lever",
            board=board,
            external_id=str(job["id"]),
            company=company,
            title=job.get("text", ""),
            location_text=" | ".join(dict.fromkeys(filter(None, locations))),
            description=description.strip(),
            apply_url=job.get("hostedUrl", ""),
            posted_at=from_epoch_ms(job.get("createdAt")),
            employment_type_hint=categories.get("commitment"),
            work_mode_hint=job.get("workplaceType"),
        ))
    return postings


def parse_ashby(board: str, company: str, payload: dict[str, Any]) -> list[RawPosting]:
    postings = []
    for job in payload.get("jobs", []):
        if job.get("isListed") is False:
            continue
        secondary = [s.get("location") or "" for s in job.get("secondaryLocations") or []]
        work_mode = job.get("workplaceType") or ("Remote" if job.get("isRemote") else None)
        postings.append(RawPosting(
            source="ashby",
            board=board,
            external_id=str(job.get("id") or job.get("jobUrl")),
            company=company,
            title=job.get("title", ""),
            location_text=" | ".join(filter(None, [job.get("location") or "", *secondary])),
            description=job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml")),
            apply_url=job.get("jobUrl") or job.get("applyUrl") or "",
            posted_at=parse_iso(job.get("publishedAt")),
            employment_type_hint=job.get("employmentType"),
            work_mode_hint=work_mode,
        ))
    return postings


@dataclass
class AtsBoardConnector:
    ats: str
    board: str
    company: str
    http: PoliteHttpClient

    @property
    def name(self) -> str:
        return f"{self.ats}:{self.board}"

    def fetch(self) -> list[RawPosting]:
        if self.ats == "greenhouse":
            payload = self.http.get_json(
                f"https://boards-api.greenhouse.io/v1/boards/{self.board}/jobs", {"content": "true"})
            return parse_greenhouse(self.board, self.company, payload)
        if self.ats == "lever":
            payload = self.http.get_json(f"https://api.lever.co/v0/postings/{self.board}", {"mode": "json"})
            return parse_lever(self.board, self.company, payload)
        if self.ats == "ashby":
            payload = self.http.get_json(f"https://api.ashbyhq.com/posting-api/job-board/{self.board}")
            return parse_ashby(self.board, self.company, payload)
        raise ValueError(f"unsupported ATS: {self.ats}")
