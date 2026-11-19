"""Identity helpers: duplicate fingerprints, content hashes and URL slugs."""

from __future__ import annotations

import hashlib
import re
import unicodedata

_COMPANY_SUFFIXES = re.compile(
    r"\b(private|pvt|limited|ltd|inc|llc|llp|corp|corporation|technologies|technology|software|"
    r"solutions|india|co)\b\.?",
    re.IGNORECASE,
)
_NON_WORD = re.compile(r"[^a-z0-9]+")


def _ascii_lower(text: str) -> str:
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()


def normalize_company(company: str) -> str:
    return _NON_WORD.sub(" ", _COMPANY_SUFFIXES.sub(" ", _ascii_lower(company))).strip()


def normalize_title(title: str) -> str:
    text = _ascii_lower(title)
    text = re.sub(r"\(.*?\)|\[.*?\]", " ", text)  # "(Remote)", "[2026 batch]"
    text = re.sub(r"\bsr\b\.?", "senior", text)
    text = re.sub(r"\bjr\b\.?", "junior", text)
    return _NON_WORD.sub(" ", text).strip()


def fingerprint(company: str, title: str, cities: list[str]) -> str:
    """Same company + same normalised title + same city set = the same job posted twice."""
    key = "|".join([normalize_company(company), normalize_title(title), ",".join(sorted(cities))])
    return hashlib.sha1(key.encode()).hexdigest()


def content_hash(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def slugify(*parts: str, max_length: int = 80) -> str:
    slug = _NON_WORD.sub("-", _ascii_lower(" ".join(parts))).strip("-")
    return slug[:max_length].rstrip("-") or "job"
