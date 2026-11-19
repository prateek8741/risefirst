"""India location handling: is a posting in India, which cities, and is it remote."""

from __future__ import annotations

import re

from risefirst.domain.enums import WorkMode

# canonical city -> aliases (lower case, matched on word boundaries)
_CITY_ALIASES: dict[str, tuple[str, ...]] = {
    "Bengaluru": ("bengaluru", "bangalore", "bengalore"),
    "Mumbai": ("mumbai", "bombay", "navi mumbai", "thane"),
    "Delhi NCR": ("delhi", "new delhi", "ncr", "gurgaon", "gurugram", "noida", "greater noida", "ghaziabad",
                  "faridabad"),
    "Hyderabad": ("hyderabad", "secunderabad"),
    "Pune": ("pune",),
    "Chennai": ("chennai", "madras"),
    "Kolkata": ("kolkata", "calcutta"),
    "Ahmedabad": ("ahmedabad", "gandhinagar"),
    "Jaipur": ("jaipur",),
    "Kochi": ("kochi", "cochin"),
    "Thiruvananthapuram": ("thiruvananthapuram", "trivandrum"),
    "Coimbatore": ("coimbatore",),
    "Indore": ("indore",),
    "Chandigarh": ("chandigarh", "mohali", "panchkula"),
    "Lucknow": ("lucknow",),
    "Nagpur": ("nagpur",),
    "Vadodara": ("vadodara", "baroda"),
    "Surat": ("surat",),
    "Visakhapatnam": ("visakhapatnam", "vizag"),
    "Bhubaneswar": ("bhubaneswar",),
    "Mysuru": ("mysuru", "mysore"),
    "Mangaluru": ("mangaluru", "mangalore"),
    "Goa": ("goa",),
    "Bhopal": ("bhopal",),
}

_CITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (city, re.compile(r"\b(?:" + "|".join(re.escape(a) for a in aliases) + r")\b", re.IGNORECASE))
    for city, aliases in _CITY_ALIASES.items()
]
# Not the bare code "IN": that is also Indiana ("Indianapolis, IN").
_INDIA = re.compile(r"\bindia\b", re.IGNORECASE)
_REMOTE = re.compile(r"\bremote\b|work from home|\bwfh\b", re.IGNORECASE)
_HYBRID = re.compile(r"\bhybrid\b", re.IGNORECASE)


def cities_in(location_text: str) -> list[str]:
    return [city for city, pattern in _CITY_PATTERNS if pattern.search(location_text or "")]


def is_in_india(location_text: str) -> bool:
    text = location_text or ""
    return bool(_INDIA.search(text) or cities_in(text))


def work_mode_of(location_text: str, hint: str | None = None) -> WorkMode:
    if hint:
        normalized = hint.strip().lower().replace("-", "").replace(" ", "")
        if normalized in {"remote", "remoteonly", "fullyremote"}:
            return WorkMode.REMOTE
        if normalized == "hybrid":
            return WorkMode.HYBRID
        if normalized in {"onsite", "inoffice", "office"}:
            return WorkMode.ONSITE
    if _HYBRID.search(location_text or ""):
        return WorkMode.HYBRID
    if _REMOTE.search(location_text or ""):
        return WorkMode.REMOTE
    if cities_in(location_text):
        return WorkMode.ONSITE
    return WorkMode.UNKNOWN
