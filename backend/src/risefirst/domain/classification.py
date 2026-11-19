"""Rule-based category and employment type. The AI may refine these when enabled."""

from __future__ import annotations

import re

from risefirst.domain.enums import Category, EmploymentType

# Order matters: the first match wins ("Data Engineer" is Data & AI, not Software).
_CATEGORY_RULES: list[tuple[Category, re.Pattern[str]]] = [
    (Category.DATA_AI, re.compile(
        r"\bdata\b|machine learning|\bml\b|\bai\b|analytics|scientist|\bnlp\b|deep learning", re.I)),
    (Category.DESIGN, re.compile(r"design|\bux\b|\bui\b|creative|illustrat", re.I)),
    (Category.PRODUCT, re.compile(r"product manager|product owner|\bapm\b|product analyst", re.I)),
    (Category.HR, re.compile(r"\bhr\b|human resources|recruit|talent|people (?:ops|partner)", re.I)),
    (Category.FINANCE, re.compile(r"financ|accountant|accounting|audit|\btax\b|payroll|treasury|credit", re.I)),
    (Category.SOFTWARE, re.compile(
        r"engineer|developer|\bsde\b|software|devops|\bsre\b|cloud|\bqa\b|test|security|programmer|"
        r"full[- ]?stack|backend|frontend|android|\bios\b", re.I)),
    (Category.SALES_MARKETING, re.compile(
        r"sales|marketing|growth|business development|\bbd[er]?\b|account (?:executive|manager)|brand|"
        r"content|\bseo\b|social media|partnership", re.I)),
    (Category.CUSTOMER_SUPPORT, re.compile(r"support|customer|success|service desk|helpdesk", re.I)),
    (Category.OPERATIONS, re.compile(r"operations|\bops\b|supply|logistics|program|project|analyst", re.I)),
]

_INTERNSHIP = re.compile(r"\bintern(ship)?\b", re.I)
_APPRENTICE = re.compile(r"\bapprentice(ship)?\b", re.I)
_CONTRACT = re.compile(r"\bcontract(or|ual)?\b|\btemporary\b|\bfixed[- ]term\b", re.I)
_FULL_TIME = re.compile(r"full[- ]?time|permanent|regular", re.I)


def category_of(title: str) -> Category:
    return next((category for category, pattern in _CATEGORY_RULES if pattern.search(title or "")),
                Category.OTHER)


def employment_type_of(title: str, hint: str | None = None) -> EmploymentType:
    """The title is checked first: boards often label internships as 'Full-time'."""
    for text in (title or "", hint or ""):
        if _INTERNSHIP.search(text):
            return EmploymentType.INTERNSHIP
        if _APPRENTICE.search(text):
            return EmploymentType.APPRENTICESHIP
    if _CONTRACT.search(hint or "") or _CONTRACT.search(title or ""):
        return EmploymentType.CONTRACT
    if _FULL_TIME.search(hint or ""):
        return EmploymentType.FULL_TIME
    return EmploymentType.UNKNOWN
