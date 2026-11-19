"""Closed vocabularies used across the system."""

from enum import StrEnum


class Eligibility(StrEnum):
    ELIGIBLE = "eligible"  # published
    REVIEW_REQUIRED = "review_required"  # not enough evidence either way; hidden by default
    REJECTED = "rejected"  # clearly not a fresher role


class EmploymentType(StrEnum):
    INTERNSHIP = "internship"
    APPRENTICESHIP = "apprenticeship"
    FULL_TIME = "full_time"
    CONTRACT = "contract"
    UNKNOWN = "unknown"


class WorkMode(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class JobStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class ClassifiedBy(StrEnum):
    RULES = "rules"
    AI = "ai"


class Category(StrEnum):
    SOFTWARE = "Software Engineering"
    DATA_AI = "Data & AI"
    PRODUCT = "Product"
    DESIGN = "Design"
    SALES_MARKETING = "Sales & Marketing"
    FINANCE = "Finance"
    OPERATIONS = "Operations"
    CUSTOMER_SUPPORT = "Customer Support"
    HR = "HR & Recruiting"
    OTHER = "Other"
