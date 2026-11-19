"""Deterministic parser for the years of experience a job description asks for.

Handles phrasings common in Indian postings: "0-2 years", "0 to 2 yrs", "up to 2 years",
"2+ years", "minimum 2 years", "at least 3 years of experience", "freshers welcome".
Only sentences that talk about experience are read, so "founded 10 years ago" is ignored.
"""

from __future__ import annotations

import re

from risefirst.domain.models import ExperienceRange

_YEARS = r"(?:years?|yrs?)"
_RANGE = re.compile(
    rf"(\d{{1,2}}(?:\.\d)?)\s*\+?\s*(?:-|–|—|to)\s*(\d{{1,2}}(?:\.\d)?)\s*\+?\s*{_YEARS}", re.IGNORECASE
)
_MINIMUM = re.compile(
    rf"(?:minimum|min\.?|at least|atleast|over|more than)\s*(?:of\s*)?(\d{{1,2}})\s*\+?\s*{_YEARS}"
    rf"|(\d{{1,2}})\s*\+\s*{_YEARS}"
    rf"|(\d{{1,2}})\s*(?:or more|plus)\s*{_YEARS}"
    rf"|(\d{{1,2}})\s*{_YEARS}(?:\s*of)?(?:\s+[\w-]+){{0,3}}\s+experienc",
    re.IGNORECASE,
)
_UP_TO = re.compile(rf"(?:up to|upto)\s*(\d{{1,2}})\s*{_YEARS}", re.IGNORECASE)
_FRESHERS = re.compile(
    r"\bfreshers?\b|recent graduates?|new grads?|no (?:prior )?experience (?:is )?required", re.IGNORECASE
)
_SENTENCE_SPLIT = re.compile(r"[.\n;•●▪]")
_MAX_PLAUSIBLE_YEARS = 30


def parse_experience(description: str) -> ExperienceRange:
    lower_bounds: list[float] = []
    upper_bounds: list[float] = []
    for sentence in _SENTENCE_SPLIT.split(description or ""):
        lowered = sentence.lower()
        if "experienc" not in lowered and "exp " not in lowered:
            continue
        for low, high in _RANGE.findall(sentence):
            low_value, high_value = float(low), float(high)
            if low_value <= high_value <= _MAX_PLAUSIBLE_YEARS:
                lower_bounds.append(low_value)
                upper_bounds.append(high_value)
        for value in _UP_TO.findall(sentence):
            lower_bounds.append(0.0)
            upper_bounds.append(float(value))
        # Drop spans already read so "0-2 years of experience" is not re-read as "2 years".
        remainder = _UP_TO.sub(" ", _RANGE.sub(" ", sentence))
        for groups in _MINIMUM.findall(remainder):
            value = next((group for group in groups if group), None)
            if value is not None and float(value) <= _MAX_PLAUSIBLE_YEARS:
                lower_bounds.append(float(value))

    # The strictest requirement wins: "0-2 years in Python, 3+ years overall" means 3.
    return ExperienceRange(
        min_years=max(lower_bounds) if lower_bounds else None,
        max_years=max(upper_bounds) if upper_bounds else None,
        freshers_mentioned=bool(_FRESHERS.search(description or "")),
    )
